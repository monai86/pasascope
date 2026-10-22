"""Build the Windows installer, PasaScope-<version>-windows-x64-setup.exe, on a Windows machine.

The macOS counterpart is scripts/build_macos_dmg.py; this one makes the same
self-contained app for 64-bit Windows 10 and 11:

* a standalone CPython 3.12 (python-build-standalone, pinned by SHA-256);
* the desktop app's packages at the tested versions
  (``scripts/desktop_bundle/requirements.txt`` with ``constraints.txt``);
* the app's code, and ``PasaScope.pyw``, which starts it without a console;
* an Inno Setup installer that installs for the current user (no
  administrator rights), adds Start menu and desktop shortcuts, closes a
  running PasaScope before replacing it, and leaves the data folder
  (``%APPDATA%\\PasaScope``) alone on update and uninstall.

Before packaging, the headless smoke test runs with the bundled Python,
including a short transcription with Whisper ``tiny`` (``--transcribe``).
The installer is not code-signed, so Windows SmartScreen asks once
("More info", then "Run anyway").

It runs in GitHub Actions (.github/workflows/desktop-windows.yml) and needs
Inno Setup 6 (``ISCC.exe``).

Usage (on Windows):
    python scripts/build_windows.py                   # dist/PasaScope-<version>-windows-x64-setup.exe
    python scripts/build_windows.py --skip-installer  # build/PasaScope only
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tomllib
import urllib.request

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYTHON_URL = (
    "https://github.com/astral-sh/python-build-standalone/releases/download/20261003/"
    "cpython-3.12.15%2B20261003-x86_64-pc-windows-msvc-install_only.tar.gz"
)
PYTHON_SHA256 = "4b6f0beebbb695a0f3ea237b8c3eaa5bd424f47a7bc25b2fbe3a43390c770f08"
CACHE = PROJECT_ROOT / ".local" / "cache" / "windows-build"
BUNDLE = PROJECT_ROOT / "scripts" / "desktop_bundle"
ICON_PNG = PROJECT_ROOT / "packages" / "desktop" / "ui" / "assets" / "icon.png"
APP_ID = "org.pasascope.desktop"
# Inno Setup identifies the product by this; keep it for every version so updates replace the old one.
INNO_APP_ID = "{{6E0C2F3B-7A41-4B8E-9D0F-5C1A2E7B9F64}"

# What the app runs from; everything else in the repository stays out (as for macOS).
CODE = ["packages", "src", "apps/api/app", "pyproject.toml", "scripts/desktop_bundle"]
SKIP_DIRS = {"__pycache__", "tests", ".pytest_cache", "node_modules"}
SKIP_CODE: set[str] = set()

LAUNCHER = '''"""Start PasaScope without a console window (run by pythonw.exe from the Start menu shortcut)."""
import os
from pathlib import Path
import sys

APP = Path(__file__).resolve().parent
os.chdir(APP)
sys.path.insert(0, str(APP))
os.environ.setdefault("PYTHONNOUSERSITE", "1")
logs = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "PasaScope" / "Logs"
logs.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("NUMBA_CACHE_DIR", str(logs.parent / "numba"))
# pythonw has no console: keep errors in a log the therapist can send.
sys.stdout = sys.stderr = open(logs / "desktop.log", "a", encoding="utf-8", buffering=1)
try:
    import ctypes

    # Group the window under PasaScope's own taskbar icon, not Python's.
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("%(app_id)s")
except Exception:
    pass
from packages.desktop.app import main

raise SystemExit(main(sys.argv[1:]))
''' % {"app_id": APP_ID}

INNO_SCRIPT = r"""
[Setup]
AppId=%(inno_id)s
AppName=PasaScope
AppVersion=%(version)s
AppVerName=PasaScope %(version)s
AppPublisher=PasaScope
AppPublisherURL=https://monai86.github.io/pasascope/
AppSupportURL=https://github.com/monai86/pasascope/issues
AppUpdatesURL=https://github.com/monai86/pasascope/releases
DefaultDirName={localappdata}\Programs\PasaScope
DisableProgramGroupPage=yes
DisableDirPage=auto
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=%(out)s
OutputBaseFilename=PasaScope-%(version)s-windows-x64-setup
SetupIconFile=%(icon)s
UninstallDisplayIcon={app}\PasaScope.ico
UninstallDisplayName=PasaScope
Compression=lzma2/normal
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
; An update replaces the program files completely; the data folder (%%APPDATA%%\PasaScope) is elsewhere.
Type: filesandordirs; Name: "{app}\app"
Type: filesandordirs; Name: "{app}\python"

[UninstallDelete]
; Python writes __pycache__ next to the code at run time; Inno Setup only removes what it installed.
Type: filesandordirs; Name: "{app}\app"
Type: filesandordirs; Name: "{app}\python"

[Files]
Source: "%(source)s\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\PasaScope"; Filename: "{app}\python\pythonw.exe"; Parameters: "-s %(q)s{app}\app\PasaScope.pyw%(q)s"; WorkingDir: "{app}\app"; IconFilename: "{app}\PasaScope.ico"; AppUserModelID: "%(app_id)s"
Name: "{autodesktop}\PasaScope"; Filename: "{app}\python\pythonw.exe"; Parameters: "-s %(q)s{app}\app\PasaScope.pyw%(q)s"; WorkingDir: "{app}\app"; IconFilename: "{app}\PasaScope.ico"; AppUserModelID: "%(app_id)s"; Tasks: desktopicon

[Run]
Filename: "{app}\python\pythonw.exe"; Parameters: "-s %(q)s{app}\app\PasaScope.pyw%(q)s"; WorkingDir: "{app}\app"; Description: "{cm:LaunchProgram,PasaScope}"; Flags: nowait postinstall skipifsilent
; An update from inside PasaScope runs this installer with /SILENT /relaunch=1; start PasaScope again
; afterwards. Other silent installs (such as CI) pass no /relaunch and nothing is started.
Filename: "{app}\python\pythonw.exe"; Parameters: "-s %(q)s{app}\app\PasaScope.pyw%(q)s"; WorkingDir: "{app}\app"; Flags: nowait; Check: RelaunchAfterUpdate

[Code]
function RelaunchAfterUpdate: Boolean;
begin
  Result := WizardSilent and (ExpandConstant('{param:relaunch|0}') = '1');
end;
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
    archive = CACHE / "cpython-3.12.15-x86_64-pc-windows-msvc.tar.gz"
    if not archive.is_file() or sha256(archive) != PYTHON_SHA256:
        print("Downloading standalone Python…", flush=True)
        with urllib.request.urlopen(PYTHON_URL, timeout=120) as response, archive.open("wb") as sink:
            shutil.copyfileobj(response, sink)
    if sha256(archive) != PYTHON_SHA256:
        archive.unlink()
        raise SystemExit("The standalone Python archive does not match its pinned SHA-256.")
    return archive


def copy_code(app_dir: Path) -> None:
    def ignore(directory: str, names: list[str]) -> set[str]:
        relative = Path(directory).resolve().relative_to(PROJECT_ROOT).as_posix()
        skipped = {name for name in names if name in SKIP_DIRS or name.endswith((".pyc", ".pyo"))}
        skipped |= {name for name in names if f"{relative}/{name}".lstrip("./") in SKIP_CODE}
        return skipped

    for item in CODE:
        source, target = PROJECT_ROOT / item, app_dir / item
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, ignore=ignore)
        else:
            shutil.copy2(source, target)


def write_icon(python: Path, destination: Path) -> None:
    """PasaScope.ico from the app icon, drawn by the bundled Qt (its ICO writer)."""
    script = (
        "import sys\n"
        "from PySide6.QtGui import QGuiApplication, QImage\n"
        "from PySide6.QtCore import Qt\n"
        "app = QGuiApplication(['icon'])\n"
        "image = QImage(sys.argv[1]).scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio, "
        "Qt.TransformationMode.SmoothTransformation)\n"
        "assert image.save(sys.argv[2], 'ICO'), 'Qt could not write the icon'\n"
    )
    run(str(python), "-s", "-c", script, str(ICON_PNG), str(destination),
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"})


def build_app(build: Path) -> Path:
    root = build / "PasaScope"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    with tarfile.open(fetch_python()) as archive:
        archive.extractall(root, filter="data")  # unpacks to root/python
    python = root / "python" / "python.exe"
    run(str(python), "-m", "pip", "install", "--no-cache-dir", "--disable-pip-version-check",
        "--no-warn-script-location", "-r", str(BUNDLE / "requirements.txt"), "-c", str(BUNDLE / "constraints.txt"))
    copy_code(root / "app")
    (root / "app" / "PasaScope.pyw").write_text(LAUNCHER, encoding="utf-8")
    write_icon(python, root / "PasaScope.ico")
    return root


def smoke_test(root: Path) -> None:
    env = {key: value for key, value in os.environ.items() if not key.startswith(("PYTHON", "VIRTUAL_ENV"))}
    env.update({"PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1", "QT_QPA_PLATFORM": "offscreen"})
    run(str(root / "python" / "python.exe"), "-s", "scripts/desktop_bundle/smoke_test.py", "--transcribe",
        cwd=root / "app", env=env)
    for cache in root.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


def find_iscc() -> str:
    for candidate in (
        shutil.which("ISCC"),
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
    ):
        if candidate and Path(candidate).is_file():
            return str(candidate)
    raise SystemExit("Inno Setup 6 (ISCC.exe) is needed: https://jrsoftware.org/isinfo.php")


def build_installer(root: Path, out: Path) -> Path:
    app_version = version()
    out.mkdir(parents=True, exist_ok=True)
    script = root.parent / "PasaScope.iss"
    script.write_text(INNO_SCRIPT % {
        "inno_id": INNO_APP_ID, "version": app_version, "out": out, "icon": root / "PasaScope.ico",
        "source": root, "app_id": APP_ID, "q": '""',  # Inno Setup writes a quote inside quotes as ""
    }, encoding="utf-8")
    run(find_iscc(), "/Q", str(script))
    installer = out / f"PasaScope-{app_version}-windows-x64-setup.exe"
    checksum = installer.with_name(installer.name + ".sha256")
    checksum.write_text(f"{sha256(installer)}  {installer.name}\n", encoding="utf-8")
    return installer


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--build", type=Path, default=PROJECT_ROOT / "build" / "windows")
    parser.add_argument("--out", type=Path, default=PROJECT_ROOT / "dist")
    parser.add_argument("--skip-smoke-test", action="store_true")
    parser.add_argument("--skip-installer", action="store_true")
    args = parser.parse_args()
    if sys.platform != "win32":
        raise SystemExit("Build the Windows installer on Windows (see .github/workflows/desktop-windows.yml).")
    root = build_app(args.build)
    if not args.skip_smoke_test:
        smoke_test(root)
    size = sum(f.stat().st_size for f in root.rglob("*") if f.is_file()) / 1e9
    print(f"App: {root} ({size:.2f} GB)")
    if not args.skip_installer:
        installer = build_installer(root, args.out)
        print(f"Installer: {installer} ({installer.stat().st_size / 1e9:.2f} GB), SHA-256 in {installer.name}.sha256")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
