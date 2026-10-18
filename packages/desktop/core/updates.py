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
