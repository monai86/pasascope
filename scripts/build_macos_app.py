"""Build double-clickable macOS launchers for the desktop app.

Creates ``PasaScope.app`` (real data) and ``PasaScope Demo.app`` (``--demo``)
in ``~/Applications``. Each is a small bundle that starts this checkout's
desktop app with its Python environment, so it works on this computer only;
it carries the app icon and the microphone permission text macOS needs.

Usage:
    .venv312/bin/python scripts/build_macos_app.py
    .venv312/bin/python scripts/build_macos_app.py --dest dist/
"""

from __future__ import annotations

import argparse
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ICON_PNG = PROJECT_ROOT / "packages" / "desktop" / "ui" / "assets" / "icon.png"
LOGO_PNG = PROJECT_ROOT / "packages" / "desktop" / "ui" / "assets" / "logo.png"
BUNDLE_ID = "org.pasascope.desktop"

LAUNCHER = """#!/bin/bash
# Starts the PasaScope desktop app from {root}
ROOT="{root}"
PYTHON="$ROOT/{python}"
if [ ! -x "$PYTHON" ]; then
    osascript -e 'display alert "PasaScope" message "ไม่พบ Python ของโปรแกรมที่ {root}/{python}"'
    exit 1
fi
cd "$ROOT"
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
mkdir -p "$ROOT/.local/logs"
exec "$PYTHON" -m packages.desktop.app {args} 2>>"$ROOT/.local/logs/desktop.log"
"""


def draw_icon(size: int):
    """The app icon: the PasaScope mark (assets/logo.png) on a white rounded square, as macOS icons are drawn."""
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPen

    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    margin = size * 0.09
    rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
    gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    gradient.setColorAt(0, QColor("#ffffff"))
    gradient.setColorAt(1, QColor("#f1f4f9"))
    p.setPen(QPen(QColor(0, 0, 0, 28), max(1.0, size / 512)))
    p.setBrush(gradient)
    p.drawRoundedRect(rect, size * 0.2, size * 0.2)
    mark = QImage(str(LOGO_PNG))
    inset = rect.width() * 0.13
    p.drawImage(rect.adjusted(inset, inset, -inset, -inset), mark)
    p.end()
    return image


def build_icns(destination: Path) -> None:
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication(["build"])  # noqa: F841 - needed for QPainter
    ICON_PNG.parent.mkdir(parents=True, exist_ok=True)
    draw_icon(512).save(str(ICON_PNG))
    with tempfile.TemporaryDirectory() as tmp:
        iconset = Path(tmp) / "PasaScope.iconset"
        iconset.mkdir()
        for base in (16, 32, 128, 256, 512):
            draw_icon(base).save(str(iconset / f"icon_{base}x{base}.png"))
            draw_icon(base * 2).save(str(iconset / f"icon_{base}x{base}@2x.png"))
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(destination)], check=True)


def build_bundle(dest_dir: Path, name: str, args: str, python: str, icns: Path, bundle_suffix: str) -> Path:
    bundle = dest_dir / f"{name}.app"
    if bundle.exists():
        shutil.rmtree(bundle)
    macos = bundle / "Contents" / "MacOS"
    resources = bundle / "Contents" / "Resources"
    macos.mkdir(parents=True)
    resources.mkdir(parents=True)
    shutil.copy(icns, resources / "PasaScope.icns")
    launcher = macos / "PasaScope"
    launcher.write_text(LAUNCHER.format(root=PROJECT_ROOT, python=python, args=args), encoding="utf-8")
    launcher.chmod(0o755)
    info = {
        "CFBundleName": name,
        "CFBundleDisplayName": name,
        "CFBundleIdentifier": BUNDLE_ID + bundle_suffix,
        "CFBundleExecutable": "PasaScope",
        "CFBundleIconFile": "PasaScope",
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": _version(),
        "LSMinimumSystemVersion": "12.0",
        "NSHighResolutionCapable": True,
        "NSMicrophoneUsageDescription": "PasaScope บันทึกเสียงใน session บำบัดเพื่อถอดเสียงบนเครื่องนี้ เสียงไม่ถูกส่งออกไปที่ใด",
    }
    with (bundle / "Contents" / "Info.plist").open("wb") as handle:
        plistlib.dump(info, handle)
    return bundle


def _version() -> str:
    import tomllib

    try:
        return tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    except (OSError, KeyError, ValueError):
        return "0"


def main() -> int:
    if sys.platform != "darwin":
        raise SystemExit("This builds macOS app bundles.")
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dest", type=Path, default=Path.home() / "Applications")
    parser.add_argument("--python", default=".venv312/bin/python", help="Python inside the checkout")
    args = parser.parse_args()

    args.dest.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        icns = Path(tmp) / "PasaScope.icns"
        build_icns(icns)
        built = [
            build_bundle(args.dest, "PasaScope", "", args.python, icns, ""),
            build_bundle(args.dest, "PasaScope Demo", "--demo", args.python, icns, ".demo"),
        ]
    for bundle in built:
        subprocess.run(["touch", str(bundle)], check=False)
        print(f"Built {bundle}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
