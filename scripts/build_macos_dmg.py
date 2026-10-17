"""Build PasaScope.app and a disk image that installs on any Apple Silicon Mac.

Unlike scripts/build_macos_app.py (launchers for this checkout), the bundle
carries everything it runs:

* a standalone CPython 3.12 (python-build-standalone, pinned by SHA-256);
* the desktop app's packages, at the exact versions of this project's tested
  environment (``.venv312``'s ``pip freeze`` as constraints);
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

# What the app runs from; everything else in the repository stays out.
CODE = ["packages", "src", "apps/api/app", "pyproject.toml", "scripts/desktop_bundle"]
SKIP_DIRS = {"__pycache__", "tests", ".pytest_cache", "node_modules"}
# Not part of the desktop app.
SKIP_CODE = {"packages/gui", "packages/tui"}

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


def constraints(destination: Path) -> Path:
    """The tested environment's exact versions, so the bundle runs what the tests ran."""
    frozen = subprocess.run([str(PROJECT_ROOT / ".venv312" / "bin" / "python"), "-m", "pip", "freeze"],
                            check=True, capture_output=True, text=True).stdout
    lines = [line for line in frozen.splitlines() if line and not line.startswith(("-e", "#")) and " @ " not in line]
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return destination


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

    with tempfile.TemporaryDirectory() as tmp:
        pins = constraints(Path(tmp) / "constraints.txt")
        run(str(python), "-m", "pip", "install", "--no-cache-dir", "--disable-pip-version-check",
            "-r", str(REQUIREMENTS), "-c", str(pins))
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


def build_dmg(bundle: Path, out: Path) -> Path:
    app_version = version()
    image = out / f"PasaScope-{app_version}.dmg"
    image.unlink(missing_ok=True)
    stale = image.with_name(image.name + ".sha256")
    stale.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp) / "PasaScope"
        staging.mkdir()
        run("ditto", str(bundle), str(staging / "PasaScope.app"))
        (staging / "Applications").symlink_to("/Applications")
        run("hdiutil", "create", "-volname", f"PasaScope {app_version}", "-srcfolder", str(staging),
            "-fs", "HFS+", "-format", "ULFO", "-ov", str(image))
    mount = Path(tempfile.mkdtemp())
    run("hdiutil", "attach", "-nobrowse", "-readonly", "-mountpoint", str(mount), str(image))
    try:
        run("codesign", "--verify", "--deep", "--strict", str(mount / "PasaScope.app"))
    finally:
        run("hdiutil", "detach", str(mount), "-quiet")
    checksum = image.with_name(image.name + ".sha256")
    checksum.write_text(f"{sha256(image)}  {image.name}\n", encoding="utf-8")
    return image


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=Path, default=PROJECT_ROOT / "dist")
    parser.add_argument("--no-dmg", action="store_true", help="Build and test the .app only")
    parser.add_argument("--skip-smoke-test", action="store_true")
    args = parser.parse_args()
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
