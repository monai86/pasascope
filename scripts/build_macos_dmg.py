"""Build PasaScope.app and a disk image that installs on any Apple Silicon Mac.

Unlike scripts/build_macos_app.py (launchers for this checkout), the bundle
carries everything it runs:

* a standalone CPython 3.12 (python-build-standalone, pinned by SHA-256);
* the desktop app's packages, at the exact versions of this project's tested
  environment (``scripts/desktop_bundle/constraints.txt``, from ``.venv312``);
* the app's code: ``packages/``, ``src/``, ``apps/api/app`` and ``pyproject.toml``
  (the version the update check compares).

Speech models are not in the image: the app downloads and checks them on
first use (Settings, Download speech models). The bundle is signed ad hoc;
without an Apple Developer ID it is not notarised, so the first launch on
another Mac needs right-click, Open.

Steps: fetch Python, install packages, copy code, write Info.plist and the
icon, run the headless smoke test with the bundled Python, sign last and
verify the signature, then make ``PasaScope-<version>.dmg``, check the
signature again inside the mounted image, and write its ``.sha256`` (the files a GitHub release
carries for the in-app updater).

The disk image opens as a fixed install window: the app and Applications side
by side over a drawn background with an arrow and the first-launch hint.
Finder itself lays the window out (AppleScript on a writable copy), because
the Finder of macOS 26 ignores a background written into ``.DS_Store`` by
other tools. The build therefore needs a logged-in session and permission for
the terminal to control Finder (asked once).

Applications is a Finder alias carrying the folder's icon, not a symlink: in a
disk image macOS 26 Finder shows a symlink to /Applications as a blank tile.
The alias records /Applications on the startup disk, which every Mac has.

Usage:
    .venv312/bin/python scripts/build_macos_dmg.py              # dist/PasaScope-<version>.dmg
    .venv312/bin/python scripts/build_macos_dmg.py --no-dmg     # the .app only
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import tomllib
import urllib.request

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

PYTHON_URL = (
    "https://github.com/astral-sh/python-build-standalone/releases/download/20261003/"
    "cpython-3.12.15%2B20261003-aarch64-apple-darwin-install_only.tar.gz"
)
PYTHON_SHA256 = "316a463172740e71d8dca1f2730784e325f3f720941137b5d674d5801a632213"
CACHE = PROJECT_ROOT / ".local" / "cache" / "dmg-build"
REQUIREMENTS = PROJECT_ROOT / "scripts" / "desktop_bundle" / "requirements.txt"
BUNDLE_ID = "org.pasascope.desktop"
FONTS = PROJECT_ROOT / "packages" / "desktop" / "ui" / "assets" / "fonts"

# The install window, in points: Finder centres each icon on its location.
WINDOW = (640, 400)
APP_AT = (170, 200)
APPLICATIONS_AT = (470, 200)
ICON_SIZE = 128
TITLE_BAR = 32  # Finder's window bounds include the title bar

LAYOUT_SCRIPT = """
on run argv
    set volumeName to item 1 of argv
    tell application "Finder"
        set theDisk to disk volumeName
        open theDisk
        set theWindow to container window of theDisk
        set current view of theWindow to icon view
        set toolbar visible of theWindow to false
        set statusbar visible of theWindow to false
        set bounds of theWindow to {%(left)d, %(top)d, %(right)d, %(bottom)d}
        set theOptions to icon view options of theWindow
        set arrangement of theOptions to not arranged
        set icon size of theOptions to %(icon)d
        set text size of theOptions to 13
        set label position of theOptions to bottom
        set shows item info of theOptions to false
        set shows icon preview of theOptions to false
        set background picture of theOptions to file ".background:background.tiff" of theDisk
        set theLink to make new alias file at theDisk to (POSIX file "/Applications" as alias)
        set name of theLink to "Applications"
        set position of item "PasaScope.app" of theDisk to {%(app_x)d, %(app_y)d}
        set position of item "Applications" of theDisk to {%(apps_x)d, %(apps_y)d}
        update theDisk without registering applications
        delay 1
        close theWindow
    end tell
end run
"""

# Gives a file (or a volume, via .VolumeIcon.icns) its own Finder icon.
SET_ICON_SCRIPT = """
ObjC.import("AppKit");
function run(argv) {
    var workspace = $.NSWorkspace.sharedWorkspace;
    var icon = argv[0].startsWith("/") && argv[0].endsWith(".icns")
        ? $.NSImage.alloc.initWithContentsOfFile(argv[0]) : workspace.iconForFile(argv[0]);
    return workspace.setIconForFileOptions(icon, argv[1], 0);
}
"""

# What the app runs from; everything else in the repository stays out.
CODE = ["packages", "src", "apps/api/app", "pyproject.toml", "scripts/desktop_bundle"]
SKIP_DIRS = {"__pycache__", "tests", ".pytest_cache", "node_modules"}
# Not part of the desktop app.
SKIP_CODE: set[str] = set()

LAUNCHER = """#!/bin/bash
# PasaScope: runs the bundled Python on the bundled code.
CONTENTS="$(cd "$(dirname "$0")/.." && pwd)"
APP="$CONTENTS/Resources/app"
export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
# Caches go outside the app: a file written inside it breaks its signature.
export NUMBA_CACHE_DIR="$HOME/Library/Caches/PasaScope/numba"
LOGS="$HOME/Library/Logs/PasaScope"
mkdir -p "$LOGS"
cd "$APP"
exec "$CONTENTS/Resources/python/bin/python3" -s -m packages.desktop.app "$@" 2>>"$LOGS/desktop.log"
"""


def version() -> str:
    return tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def run(*command: str, **kwargs) -> None:
    print("$", " ".join(command), flush=True)
    subprocess.run(command, check=True, **kwargs)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_python() -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    archive = CACHE / "cpython-3.12.15-aarch64-apple-darwin.tar.gz"
    if not archive.is_file() or sha256(archive) != PYTHON_SHA256:
        print("Downloading standalone Python…", flush=True)
        with urllib.request.urlopen(PYTHON_URL, timeout=120) as response, archive.open("wb") as sink:
            shutil.copyfileobj(response, sink)
    if sha256(archive) != PYTHON_SHA256:
        archive.unlink()
        raise SystemExit("The standalone Python archive does not match its pinned SHA-256.")
    return archive


CONSTRAINTS = PROJECT_ROOT / "scripts" / "desktop_bundle" / "constraints.txt"
CONSTRAINTS_HEADER = """# Exact versions for the desktop app bundles (macOS and Windows): the tested
# environment (.venv312), used as pip constraints by scripts/build_macos_dmg.py
# and scripts/build_windows.py. Refresh after changing .venv312:
#   .venv312/bin/python scripts/build_macos_dmg.py --write-constraints
"""


def write_constraints() -> Path:
    """Record the tested environment's exact versions, so every bundle runs what the tests ran."""
    frozen = subprocess.run([str(PROJECT_ROOT / ".venv312" / "bin" / "python"), "-m", "pip", "freeze"],
                            check=True, capture_output=True, text=True).stdout
    lines = [line for line in frozen.splitlines() if line and not line.startswith(("-e", "#")) and " @ " not in line]
    CONSTRAINTS.write_text(CONSTRAINTS_HEADER + "\n".join(lines) + "\n", encoding="utf-8")
    return CONSTRAINTS


def copy_code(app_dir: Path) -> None:
    def ignore(directory: str, names: list[str]) -> set[str]:
        relative = Path(directory).resolve().relative_to(PROJECT_ROOT).as_posix()
        skipped = {name for name in names if name in SKIP_DIRS or name.endswith((".pyc", ".pyo"))}
        skipped |= {name for name in names if f"{relative}/{name}".lstrip("./") in SKIP_CODE}
        return skipped

    for item in CODE:
        source = PROJECT_ROOT / item
        target = app_dir / item
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, ignore=ignore)
        else:
            shutil.copy2(source, target)


def write_info_plist(contents: Path, app_version: str) -> None:
    info = {
        "CFBundleName": "PasaScope",
        "CFBundleDisplayName": "PasaScope",
        "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleExecutable": "PasaScope",
        "CFBundleIconFile": "PasaScope",
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": app_version,
        "CFBundleVersion": app_version,
        "LSMinimumSystemVersion": "12.0",
        "LSArchitecturePriority": ["arm64"],
        "NSHighResolutionCapable": True,
        "NSMicrophoneUsageDescription": "PasaScope records therapy sessions on this computer to draft transcripts.",
    }
    with (contents / "Info.plist").open("wb") as sink:
        plistlib.dump(info, sink)


def build_app(out: Path) -> Path:
    from scripts.build_macos_app import build_icns

    app_version = version()
    bundle = out / "PasaScope.app"
    if bundle.exists():
        shutil.rmtree(bundle)
    contents = bundle / "Contents"
    resources = contents / "Resources"
    (contents / "MacOS").mkdir(parents=True)
    resources.mkdir(parents=True)

    with tarfile.open(fetch_python()) as archive:
        archive.extractall(resources, filter="data")  # unpacks to resources/python
    python = resources / "python" / "bin" / "python3"

    run(str(python), "-m", "pip", "install", "--no-cache-dir", "--disable-pip-version-check",
        "-r", str(REQUIREMENTS), "-c", str(CONSTRAINTS))
    copy_code(resources / "app")

    launcher = contents / "MacOS" / "PasaScope"
    launcher.write_text(LAUNCHER, encoding="utf-8")
    launcher.chmod(0o755)
    write_info_plist(contents, app_version)
    build_icns(resources / "PasaScope.icns")
    return bundle


def sign(bundle: Path) -> None:
    """Sign ad hoc, last: any file written into the bundle afterwards breaks the seal."""
    for cache in bundle.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)
    run("codesign", "--force", "--deep", "--sign", "-", str(bundle))
    run("codesign", "--verify", "--deep", "--strict", str(bundle))


def smoke_test(bundle: Path) -> None:
    resources = bundle / "Contents" / "Resources"
    env = {key: value for key, value in os.environ.items() if not key.startswith(("PYTHON", "VIRTUAL_ENV"))}
    env.update({"PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1", "QT_QPA_PLATFORM": "offscreen",
                "NUMBA_CACHE_DIR": str(Path(tempfile.gettempdir()) / "pasascope-numba")})
    run(str(resources / "python" / "bin" / "python3"), "-s", "scripts/desktop_bundle/smoke_test.py",
        cwd=resources / "app", env=env)


def draw_background(folder: Path) -> Path:
    """The install window's background, one TIFF holding 1x and 2x: title, arrow, and how to open the app the first time."""
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QImage, QPainter, QPainterPath, QPen

    app = QGuiApplication.instance() or QGuiApplication(["dmg"])  # noqa: F841 - fonts need an application
    for name in ("Sarabun-Regular.ttf", "Sarabun-SemiBold.ttf"):
        QFontDatabase.addApplicationFont(str(FONTS / name))
    width, height = WINDOW
    ink, muted, primary = QColor("#1f2328"), QColor("#6b7280"), QColor("#2383e2")

    def font(pixels: float, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
        result = QFont("Sarabun")
        result.setPixelSize(round(pixels))
        result.setWeight(weight)
        return result

    path = folder / "background.png"
    for scale, target in ((1, path), (2, folder / "background@2x.png")):
        image = QImage(width * scale, height * scale, QImage.Format.Format_ARGB32)
        image.fill(QColor("#f7f8fa"))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.scale(scale, scale)

        painter.setPen(ink)
        painter.setFont(font(22, QFont.Weight.DemiBold))
        painter.drawText(QRectF(0, 34, width, 32), Qt.AlignmentFlag.AlignHCenter, "Install PasaScope")
        painter.setPen(muted)
        painter.setFont(font(14))
        painter.drawText(QRectF(0, 66, width, 22), Qt.AlignmentFlag.AlignHCenter,
                         "Drag PasaScope onto Applications  ·  ลาก PasaScope ไปวางที่ Applications")

        # A soft arrow from the app to Applications.
        y = APP_AT[1]
        start, end = APP_AT[0] + ICON_SIZE / 2 + 26, APPLICATIONS_AT[0] - ICON_SIZE / 2 - 26
        pen = QPen(primary, 3.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(QPointF(start, y), QPointF(end - 4, y))
        head = QPainterPath()
        head.moveTo(end - 14, y - 11)
        head.lineTo(end, y)
        head.lineTo(end - 14, y + 11)
        painter.drawPath(head)

        # macOS blocks the first launch of an app that is not notarised; since
        # macOS 15 it is allowed in Privacy & Security (labels as macOS shows them).
        card = QRectF(40, 318, width - 80, 56)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#e9eef5"))
        painter.drawRoundedRect(card, 10, 10)
        painter.setPen(ink)
        painter.setFont(font(14, QFont.Weight.DemiBold))
        painter.drawText(card.adjusted(0, 8, 0, 0), Qt.AlignmentFlag.AlignHCenter,
                         "Blocked at first launch? System Settings → Privacy & Security → Open Anyway")
        painter.setPen(muted)
        painter.setFont(font(12.5))
        painter.drawText(card.adjusted(0, 30, 0, 0), Qt.AlignmentFlag.AlignHCenter,
                         "เปิดครั้งแรกไม่ได้: การตั้งค่าระบบ → ความเป็นส่วนตัวและความปลอดภัย → ยืนยันจะเปิด")
        painter.end()
        image.setDotsPerMeterX(round(72 * scale / 0.0254))
        image.setDotsPerMeterY(round(72 * scale / 0.0254))
        image.save(str(target))
    tiff = folder / "background.tiff"
    run("tiffutil", "-cathidpicheck", str(path), str(folder / "background@2x.png"), "-out", str(tiff))
    return tiff


def build_dmg(bundle: Path, out: Path) -> Path:
    app_version = version()
    volume_name = f"PasaScope {app_version}"
    volume = Path("/Volumes") / volume_name
    if volume.exists():
        raise SystemExit(f"Eject {volume} first: Finder lays out the new image by its volume name.")
    image = out / f"PasaScope-{app_version}.dmg"
    image.unlink(missing_ok=True)
    stale = image.with_name(image.name + ".sha256")
    stale.unlink(missing_ok=True)
    width, height = WINDOW
    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp) / "PasaScope"
        (staging / ".background").mkdir(parents=True)
        run("ditto", str(bundle), str(staging / "PasaScope.app"))
        shutil.copy2(draw_background(Path(tmp)), staging / ".background" / "background.tiff")
        size_mb = int(sum(f.stat().st_size for f in staging.rglob("*") if f.is_file()) / 1e6 * 1.1) + 40
        writable = Path(tmp) / "writable.dmg"
        run("hdiutil", "create", "-volname", volume_name, "-srcfolder", str(staging), "-fs", "HFS+",
            "-format", "UDRW", "-size", f"{size_mb}m", str(writable))
        run("hdiutil", "attach", "-readwrite", "-noverify", "-noautoopen", "-mountpoint", str(volume), str(writable))
        try:
            run("osascript", "-l", "JavaScript", "-e", SET_ICON_SCRIPT,
                str(bundle / "Contents" / "Resources" / "PasaScope.icns"), str(volume))
            script = LAYOUT_SCRIPT % {
                "left": 200, "top": 160, "right": 200 + width, "bottom": 160 + height + TITLE_BAR,
                "icon": ICON_SIZE, "app_x": APP_AT[0], "app_y": APP_AT[1],
                "apps_x": APPLICATIONS_AT[0], "apps_y": APPLICATIONS_AT[1],
            }
            try:
                run("osascript", "-e", script, volume_name)
            except subprocess.CalledProcessError:
                raise SystemExit("Finder could not lay out the disk image. Allow this terminal to control "
                                 "Finder (System Settings, Privacy & Security, Automation) and build again.") from None
            run("osascript", "-l", "JavaScript", "-e", SET_ICON_SCRIPT, "/Applications", str(volume / "Applications"))
            # Finder writes the window's .DS_Store after the window closes.
            for _ in range(60):
                if (volume / ".DS_Store").is_file():
                    break
                time.sleep(0.5)
            else:
                raise SystemExit("Finder did not save the window layout (.DS_Store).")
            run("sync")
            time.sleep(1)
            run("codesign", "--verify", "--deep", "--strict", str(volume / "PasaScope.app"))
        finally:
            detach(volume)
        run("hdiutil", "convert", str(writable), "-format", "ULFO", "-o", str(image))
    mount = Path(tempfile.mkdtemp())
    run("hdiutil", "attach", "-nobrowse", "-readonly", "-mountpoint", str(mount), str(image))
    try:
        run("codesign", "--verify", "--deep", "--strict", str(mount / "PasaScope.app"))
        for needed in (".DS_Store", ".background/background.tiff", "Applications"):
            if not (mount / needed).exists():
                raise SystemExit(f"The disk image is missing {needed}.")
    finally:
        detach(mount)
    checksum = image.with_name(image.name + ".sha256")
    checksum.write_text(f"{sha256(image)}  {image.name}\n", encoding="utf-8")
    return image


def detach(mount: Path) -> None:
    """Detach, retrying while Finder or Spotlight still holds the volume."""
    for attempt in range(10):
        if subprocess.run(["hdiutil", "detach", str(mount), "-quiet"]).returncode == 0:
            return
        time.sleep(1 + attempt)
    run("hdiutil", "detach", str(mount), "-force", "-quiet")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=Path, default=PROJECT_ROOT / "dist")
    parser.add_argument("--no-dmg", action="store_true", help="Build and test the .app only")
    parser.add_argument("--skip-smoke-test", action="store_true")
    parser.add_argument("--write-constraints", action="store_true",
                        help="Only record .venv312's versions in scripts/desktop_bundle/constraints.txt")
    args = parser.parse_args()
    if args.write_constraints:
        print(f"Wrote {write_constraints()}")
        return 0
    if sys.platform != "darwin":
        raise SystemExit("Build the macOS app on a Mac.")
    args.out.mkdir(parents=True, exist_ok=True)
    bundle = build_app(args.out)
    if not args.skip_smoke_test:
        smoke_test(bundle)
    sign(bundle)
    print(f"App: {bundle} ({sum(f.stat().st_size for f in bundle.rglob('*') if f.is_file()) / 1e9:.2f} GB)")
    if not args.no_dmg:
        image = build_dmg(bundle, args.out)
        print(f"Disk image: {image} ({image.stat().st_size / 1e9:.2f} GB), SHA-256 in {image.name}.sha256")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
