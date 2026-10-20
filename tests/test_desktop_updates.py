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


# ----------------------------------------------------------------------
# Installing in place
# ----------------------------------------------------------------------
import plistlib  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402


def _fake_app(path, version, marker):
    contents = path / "Contents"
    contents.mkdir(parents=True)
    with (contents / "Info.plist").open("wb") as handle:
        plistlib.dump({"CFBundleShortVersionString": version}, handle)
    (contents / "marker.txt").write_text(marker, encoding="utf-8")
    return path


def _finished_pid():
    process = subprocess.Popen(["true"])
    process.wait()
    return process.pid


def test_running_app_bundle_finds_the_enclosing_app(tmp_path):
    inside = tmp_path / "Applications" / "PasaScope.app" / "Contents" / "Resources" / "app" / "updates.py"
    assert updates.running_app_bundle(inside) == tmp_path / "Applications" / "PasaScope.app"
    assert updates.running_app_bundle(tmp_path / "src" / "updates.py") is None


@pytest.mark.skipif(sys.platform == "win32", reason="the swap script is for macOS")
def test_swap_script_replaces_the_app_and_leaves_nothing_behind(tmp_path):
    bundle = _fake_app(tmp_path / "PasaScope.app", "1.0.0", "old")
    staged = _fake_app(tmp_path / updates.STAGED_NAME, "1.1.0", "new")
    script = tmp_path / "swap.sh"
    script.write_text(updates.macos_swap_script(bundle, staged, _finished_pid(), relaunch=False), encoding="utf-8")

    out = subprocess.run(["/bin/bash", str(script)], capture_output=True, text=True, timeout=30)

    assert "updated" in out.stdout
    assert (bundle / "Contents" / "marker.txt").read_text() == "new"
    assert not staged.exists() and not (tmp_path / updates.PREVIOUS_NAME).exists()


@pytest.mark.skipif(sys.platform == "win32", reason="the swap script is for macOS")
def test_swap_script_puts_the_old_app_back_when_the_new_one_is_missing(tmp_path):
    bundle = _fake_app(tmp_path / "PasaScope.app", "1.0.0", "old")
    script = tmp_path / "swap.sh"
    script.write_text(updates.macos_swap_script(bundle, tmp_path / updates.STAGED_NAME, _finished_pid(), relaunch=False),
                      encoding="utf-8")

    out = subprocess.run(["/bin/bash", str(script)], capture_output=True, text=True, timeout=30)

    assert "previous version is back" in out.stdout
    assert (bundle / "Contents" / "marker.txt").read_text() == "old"


@pytest.mark.skipif(sys.platform != "darwin" or not shutil.which("hdiutil"), reason="needs macOS disk images")
def test_staging_copies_the_new_app_out_of_the_disk_image(tmp_path):
    source = tmp_path / "image"
    _fake_app(source / "PasaScope.app", "1.1.0", "new")
    image = tmp_path / "PasaScope-1.1.0.dmg"
    made = subprocess.run(["hdiutil", "create", "-quiet", "-volname", "PasaScope", "-srcfolder", str(source),
                           "-format", "UDRO", str(image)], capture_output=True, text=True)
    if made.returncode != 0:
        pytest.skip(f"hdiutil create is not allowed here: {made.stderr.strip()}")
    bundle = _fake_app(tmp_path / "Applications" / "PasaScope.app", "1.0.0", "old")

    with pytest.raises(updates.UpdateError):
        updates.stage_macos_update(image, bundle, "2.0.0")
    assert not (bundle.parent / updates.STAGED_NAME).exists()

    staged = updates.stage_macos_update(image, bundle, "1.1.0")
    assert staged == bundle.parent / updates.STAGED_NAME
    assert (staged / "Contents" / "marker.txt").read_text() == "new"
    assert (bundle / "Contents" / "marker.txt").read_text() == "old"  # the installed copy is untouched until quit
