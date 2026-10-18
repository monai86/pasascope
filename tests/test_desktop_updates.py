"""Update checks: the newest published release with a checked disk image."""

import hashlib
import io
import json

import pytest

from packages.desktop.core import updates
from packages.desktop.core.updates import UpdateError


def _release(version, *, draft=False, prerelease=False, checksum=True, windows=False):
    name = f"PasaScope-{version}-windows-x64-setup.exe" if windows else f"PasaScope-{version}.dmg"
    assets = [{"name": name, "browser_download_url": f"https://x/{name}", "size": 12}]
    if checksum:
        assets.append({"name": f"{name}.sha256", "browser_download_url": f"https://x/{version}.sha256"})
    return {"tag_name": f"v{version}", "draft": draft, "prerelease": prerelease, "body": "notes",
            "html_url": "https://x/release", "assets": assets}


def _opener(payloads: dict[str, bytes]):
    return lambda url: io.BytesIO(payloads[url])


def test_versions_compare_as_numbers():
    assert updates.is_newer("1.10.0", "1.9.9") and not updates.is_newer("1.7.2", "1.7.2")
    assert updates.parse_version("v1.7.3") == (1, 7, 3) and not updates.is_newer("web-build", "1.0.0")


def test_the_newest_published_release_with_a_disk_image_is_offered():
    payload = [_release("1.7.3"), _release("1.9.0", draft=True), _release("1.8.0", prerelease=True), _release("1.7.4"),
               {"tag_name": "v2.0.0", "assets": [{"name": "web.zip"}]}]
    opener = _opener({updates.RELEASES_URL: json.dumps(payload).encode()})
    release = updates.check_for_update("1.7.2", opener=opener, platform="darwin")
    assert release.version == "1.7.4" and release.sha256_url == "https://x/1.7.4.sha256"
    assert updates.check_for_update("1.7.4", opener=opener, platform="darwin") is None


def test_each_platform_is_offered_its_own_installer():
    # 1.8.0 has only the Mac disk image so far: Windows stays on the newest release with a setup file.
    payload = [_release("1.7.4"), _release("1.7.4", windows=True), _release("1.8.0")]
    opener = _opener({updates.RELEASES_URL: json.dumps(payload).encode()})
    mac = updates.check_for_update("1.7.3", opener=opener, platform="darwin")
    windows = updates.check_for_update("1.7.3", opener=opener, platform="win32")
    assert mac.version == "1.8.0" and mac.installer_name == "PasaScope-1.8.0.dmg"
    assert windows.version == "1.7.4" and windows.installer_name == "PasaScope-1.7.4-windows-x64-setup.exe"
    assert updates.check_for_update("1.7.3", opener=opener, platform="linux") is None


def test_offline_is_an_update_error():
    def offline(url):
        raise OSError("no network")
    with pytest.raises(UpdateError):
        updates.check_for_update("1.7.2", opener=offline)


def test_download_is_checked_against_the_published_sha256(tmp_path):
    data = b"disk image"
    release = updates.releases_from([_release("1.7.3")], "darwin")[0]
    good = _opener({release.sha256_url: f"{hashlib.sha256(data).hexdigest()}  PasaScope-1.7.3.dmg\n".encode(),
                    release.installer_url: data})
    path = updates.download_release(release, tmp_path, opener=good)
    assert path.read_bytes() == data and path.name == "PasaScope-1.7.3.dmg"

    bad = _opener({release.sha256_url: ("0" * 64).encode(), release.installer_url: data})
    with pytest.raises(UpdateError):
        updates.download_release(release, tmp_path / "bad", opener=bad)
    assert not list((tmp_path / "bad").glob("*.dmg*"))

    unchecked = updates.releases_from([_release("1.7.3", checksum=False)], "darwin")[0]
    with pytest.raises(UpdateError):
        updates.download_release(unchecked, tmp_path, opener=good)


def test_automatic_checks_run_once_a_day_and_can_be_switched_off(tmp_path):
    from datetime import datetime, timedelta, timezone

    from packages.desktop.core import DesktopService, open_workspace

    service = DesktopService(open_workspace(tmp_path / "ws"))
    assert service.update_check_due()
    profile = service.workspace.read_profile()
    now = datetime.now(timezone.utc)
    profile["last_update_check"] = now.isoformat()
    service.workspace.write_profile(profile)
    assert not service.update_check_due(now + timedelta(hours=2))
    assert service.update_check_due(now + timedelta(hours=25))
    service.set_auto_update_check(False)
    assert not service.update_check_due(now + timedelta(days=3))
