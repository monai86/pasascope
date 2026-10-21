"""Find, download and check a newer PasaScope desktop release.

Releases are published on GitHub (``monai86/pasascope``, a public
repository): a release tagged ``vX.Y.Z`` carries an installer for each
platform with its SHA-256 beside it:

* macOS: ``PasaScope-X.Y.Z.dmg`` and ``PasaScope-X.Y.Z.dmg.sha256``
* Windows: ``PasaScope-X.Y.Z-windows-x64-setup.exe`` and its ``.sha256``

The app asks GitHub's public API for the newest release that has an
installer for this platform, compares versions, downloads it to the
Downloads folder and checks it against the published SHA-256 before opening
it. The data folder is separate from the app, so an update leaves cases,
recordings and settings where they are, and the app offers a backup first.

Only the version check and the download touch the network; no data about the
children or the therapist is sent.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sys

REPOSITORY = "monai86/pasascope"
RELEASES_URL = f"https://api.github.com/repos/{REPOSITORY}/releases?per_page=20"
RELEASE_PAGE = f"https://github.com/{REPOSITORY}/releases"
INSTALLER_NAMES = {
    "darwin": re.compile(r"^PasaScope-(\d+\.\d+\.\d+)\.dmg$"),
    "win32": re.compile(r"^PasaScope-(\d+\.\d+\.\d+)-windows-x64-setup\.exe$"),
}
CHUNK = 1 << 20


class UpdateError(RuntimeError):
    pass


@dataclass(frozen=True)
class Release:
    version: str
    tag: str
    notes: str
    page_url: str
    installer_url: str
    installer_name: str
    size: int
    sha256_url: str | None


def parse_version(text: str) -> tuple[int, ...]:
    """(1, 7, 3) from "1.7.3" or "v1.7.3"; () when it is not a version."""
    match = re.match(r"^v?(\d+(?:\.\d+)*)", (text or "").strip())
    return tuple(int(part) for part in match.group(1).split(".")) if match else ()


def is_newer(candidate: str, current: str) -> bool:
    return parse_version(candidate) > parse_version(current) if parse_version(candidate) else False


def _get(url: str, opener: Callable[[str], object] | None = None):
    import urllib.request

    if opener is not None:
        return opener(url)
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "PasaScope-desktop"})
    return urllib.request.urlopen(request, timeout=20)


def releases_from(payload: list[dict], platform: str | None = None) -> list[Release]:
    """Published (not draft, not pre-release) releases with an installer for ``platform``, newest version first.

    ``platform`` is a ``sys.platform`` value; a platform without installers (Linux) finds none.
    """
    pattern = INSTALLER_NAMES.get(platform or sys.platform)
    if pattern is None:
        return []
    found = []
    for item in payload:
        if item.get("draft") or item.get("prerelease"):
            continue
        assets = {asset.get("name", ""): asset for asset in item.get("assets") or []}
        for name, asset in assets.items():
            match = pattern.match(name)
            if not match:
                continue
            checksum = assets.get(name + ".sha256")
            found.append(Release(
                version=match.group(1),
                tag=item.get("tag_name", ""),
                notes=(item.get("body") or "").strip(),
                page_url=item.get("html_url") or RELEASE_PAGE,
                installer_url=asset.get("browser_download_url", ""),
                installer_name=name,
                size=int(asset.get("size") or 0),
                sha256_url=checksum.get("browser_download_url") if checksum else None,
            ))
    return sorted(found, key=lambda release: parse_version(release.version), reverse=True)


def check_for_update(
    current_version: str, *, opener: Callable[[str], object] | None = None, platform: str | None = None,
) -> Release | None:
    """The newest release for this platform when it is newer than ``current_version``, else None."""
    try:
        with _get(RELEASES_URL, opener) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - offline, rate-limited or GitHub down
        raise UpdateError(f"Could not reach GitHub: {exc}") from exc
    newest = next(iter(releases_from(payload if isinstance(payload, list) else [], platform)), None)
    return newest if newest and is_newer(newest.version, current_version) else None


def download_release(
    release: Release,
    folder: Path,
    progress: Callable[[int, int], None] | None = None,
    *,
    cancelled: Callable[[], bool] | None = None,
    opener: Callable[[str], object] | None = None,
) -> Path:
    """Download the installer into ``folder`` and check it against the published SHA-256."""
    if not release.sha256_url:
        raise UpdateError("This release has no SHA-256 file, so the download cannot be checked.")
    with _get(release.sha256_url, opener) as response:
        expected = response.read().decode("utf-8").split()[0].strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise UpdateError("The release's SHA-256 file is not a SHA-256.")
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / release.installer_name
    partial = target.with_name(target.name + ".partial")
    digest = hashlib.sha256()
    done = 0
    with _get(release.installer_url, opener) as response, partial.open("wb") as sink:
        for chunk in iter(lambda: response.read(CHUNK), b""):
            if cancelled and cancelled():
                sink.close()
                partial.unlink(missing_ok=True)
                raise UpdateError("Download cancelled.")
            digest.update(chunk)
            sink.write(chunk)
            done += len(chunk)
            if progress:
                progress(done, release.size or done)
    if digest.hexdigest() != expected:
        partial.unlink(missing_ok=True)
        raise UpdateError("The downloaded file does not match the release's SHA-256; it was deleted.")
    partial.replace(target)
    return target


# ----------------------------------------------------------------------
# Installing in place: the new version replaces this copy, the data stays
# ----------------------------------------------------------------------
# The data folder (cases, recordings, settings) is apart from the app, so
# swapping the app leaves it untouched and nothing has to be uninstalled.
# On macOS the new PasaScope.app is copied out of the disk image beside this
# one while the app runs; once it quits a small script swaps the two, puts
# the old one back if the swap fails, and opens the new one. On Windows the
# installer runs silently over the installed copy and starts it again.
STAGED_NAME = ".PasaScope-update.app"
PREVIOUS_NAME = ".PasaScope-previous.app"


def running_app_bundle(start: Path | None = None) -> Path | None:
    """The macOS ``.app`` this copy runs from, or None when it runs from source."""
    here = (start or Path(__file__)).resolve()
    return next((parent for parent in here.parents if parent.suffix == ".app"), None)


def can_replace(bundle: Path) -> bool:
    """Whether this user may replace ``bundle`` (an Applications folder they cannot write to needs the manual way)."""
    import os

    return bundle.is_dir() and os.access(bundle.parent, os.W_OK) and os.access(bundle, os.W_OK)


def bundle_version(bundle: Path) -> str:
    import plistlib

    with (bundle / "Contents" / "Info.plist").open("rb") as handle:
        return str(plistlib.load(handle).get("CFBundleShortVersionString", ""))


def stage_macos_update(disk_image: Path, bundle: Path, expected_version: str, *, run=None) -> Path:
    """Copy the new PasaScope.app out of ``disk_image`` to a hidden copy beside ``bundle``; return it.

    The disk image is mounted without a Finder window and detached again.
    The copy must carry ``expected_version``, or it is removed and an
    ``UpdateError`` raised. Nothing of the installed app changes here.
    """
    import shutil
    import subprocess
    import tempfile

    run = run or (lambda *command: subprocess.run(command, check=True, capture_output=True, text=True))
    mount = Path(tempfile.mkdtemp(prefix="pasascope-update-"))
    staged = bundle.with_name(STAGED_NAME)
    try:
        try:
            run("hdiutil", "attach", "-nobrowse", "-readonly", "-noautoopen", "-mountpoint", str(mount), str(disk_image))
        except Exception as exc:  # noqa: BLE001 - reported as a failed update
            raise UpdateError(f"The disk image could not be opened: {exc}") from exc
        try:
            source = next((item for item in mount.iterdir() if item.suffix == ".app"), None)
            if source is None:
                raise UpdateError("The disk image has no PasaScope.app.")
            if bundle_version(source) != expected_version:
                raise UpdateError(f"The disk image holds version {bundle_version(source)}, not {expected_version}.")
            if staged.exists():
                shutil.rmtree(staged)
            run("ditto", str(source), str(staged))
        finally:
            try:
                run("hdiutil", "detach", str(mount), "-quiet")
            except Exception:  # noqa: BLE001 - a busy mount detaches by itself later
                try:
                    run("hdiutil", "detach", str(mount), "-force", "-quiet")
                except Exception:  # noqa: BLE001
                    pass
        try:
            run("xattr", "-dr", "com.apple.quarantine", str(staged))
        except Exception:  # noqa: BLE001 - only present if something marked it; harmless otherwise
            pass
        if bundle_version(staged) != expected_version:
            raise UpdateError("The copied app does not carry the new version.")
    except BaseException:
        shutil.rmtree(staged, ignore_errors=True)
        raise
    finally:
        shutil.rmtree(mount, ignore_errors=True)
    return staged


def macos_swap_script(bundle: Path, staged: Path, pid: int, relaunch: bool) -> str:
    """A shell script that waits for ``pid`` to quit, swaps ``staged`` in for ``bundle`` and reopens it."""
    import shlex

    previous = shlex.quote(str(bundle.with_name(PREVIOUS_NAME)))
    target, new = shlex.quote(str(bundle)), shlex.quote(str(staged))
    reopen = f"open {target}" if relaunch else ":"
    return f"""#!/bin/bash
# PasaScope update: replace the app once it has quit; the data folder is elsewhere and untouched.
for _ in $(seq 1 600); do kill -0 {int(pid)} 2>/dev/null || break; sleep 0.2; done
rm -rf {previous}
if mv {target} {previous}; then
  if mv {new} {target}; then
    rm -rf {previous}
    echo "updated"
  else
    mv {previous} {target}
    echo "swap failed; the previous version is back"
  fi
else
  echo "could not move the installed app aside; nothing changed"
fi
{reopen}
"""


def start_macos_swap(bundle: Path, staged: Path, pid: int, relaunch: bool = True, log: Path | None = None) -> Path:
    """Write the swap script and start it detached, so it outlives this process; return the script."""
    import subprocess
    import tempfile

    script = Path(tempfile.mkdtemp(prefix="pasascope-update-")) / "swap.sh"
    script.write_text(macos_swap_script(bundle, staged, pid, relaunch), encoding="utf-8")
    log = log or Path.home() / "Library" / "Logs" / "PasaScope" / "update.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as sink:
        subprocess.Popen(["/bin/bash", str(script)], stdout=sink, stderr=sink, stdin=subprocess.DEVNULL,
                         start_new_session=True, close_fds=True)
    return script


# /relaunch=1 asks the installer to start PasaScope again when it is done (see build_windows.py).
WINDOWS_SILENT_ARGS = ("/SILENT", "/SUPPRESSMSGBOXES", "/CLOSEAPPLICATIONS", "/NORESTART", "/relaunch=1")


def start_windows_install(installer: Path) -> None:
    """Run the installer over this copy without its wizard; it starts PasaScope again when done."""
    import subprocess

    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen([str(installer), *WINDOWS_SILENT_ARGS], creationflags=flags, close_fds=True)
