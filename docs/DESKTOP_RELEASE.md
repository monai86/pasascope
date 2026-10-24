# Releasing the desktop app

The desktop app updates itself from GitHub Releases of this public repository. Help → "Check for updates…" runs the check on demand, and the app also checks once a day on its own; the automatic check can be switched off in the same menu.

The release format is fixed. Each release:
- is tagged `vX.Y.Z`;
- is not a draft or a pre-release;
- carries the macOS disk image `PasaScope-X.Y.Z.dmg` and `PasaScope-X.Y.Z.dmg.sha256`;
- carries the Windows installer `PasaScope-X.Y.Z-windows-x64-setup.exe` and its `.sha256`, which GitHub Actions attaches (see Windows below).

Each platform's updater looks only for its own file, so a release that has only the disk image so far is offered on macOS and not yet on Windows.

The app (`packages/desktop/core/updates.py`):
1. takes the newest release with this platform's installer and compares its version with `pyproject.toml`;
2. offers a backup, written to `~/Documents/PasaScope backups/`;
3. downloads the installer into Downloads and checks it against the SHA-256 file;
4. installs it over the running copy, without uninstalling anything:
   - macOS: mounts the disk image without a Finder window, copies the new `PasaScope.app` beside the installed one as `.PasaScope-update.app`, checks its version, then offers **Restart now** or **Later**. Once PasaScope quits, a small script waits for the process to end, swaps the two apps (putting the old one back if the swap fails) and opens the new one; the log is `~/Library/Logs/PasaScope/update.log`. If the therapist cannot write to the folder the app is in, PasaScope falls back to opening the disk image for a drag onto Applications.
   - Windows: runs the installer with `/SILENT /SUPPRESSMSGBOXES /CLOSEAPPLICATIONS /NORESTART /relaunch=1` and quits; the installer replaces the program files and starts PasaScope again only because of `/relaunch=1` (its `RelaunchAfterUpdate` check). Other silent installs, such as the CI check, start nothing: a PasaScope started by the installer would keep PowerShell's `Start-Process -Wait` waiting for good.

Cases, recordings and settings live in `~/Library/Application Support/PasaScope` (`%APPDATA%\PasaScope` on Windows), apart from the app, so an update leaves them alone and the first-start walkthrough does not return. A copy older than 1.8.0 still updates the old way once: it opens the disk image or installer for the therapist.

## Download page

`site/` is the public download page, published to GitHub Pages (`https://monai86.github.io/pasascope/`) by `.github/workflows/pages.yml` whenever `site/` changes on `main`. It replaces the earlier page on the `gh-pages` branch: the repository's Pages source is set to GitHub Actions (`gh api -X PUT repos/monai86/pasascope/pages -f build_type=workflow`), and `gh-pages` is kept only as history. It is static: in the browser it reads the latest release from the GitHub API and links its `.dmg` and Windows installer directly, with their sizes, so a new release needs no change to the page. It offers the file for the visitor's computer first and falls back to the Releases page when the API cannot be reached. The page is in Thai and English (`?lang=en`), and its screenshots in `site/assets/` come from the demonstration data (`scripts/seed_desktop_demo.py`).

## Build

```bash
.venv312/bin/python scripts/build_macos_dmg.py
```

This builds `dist/PasaScope.app` and `dist/PasaScope-<version>.dmg` with its `.sha256`.

The disk image opens as an install window: PasaScope and Applications side by side over a drawn background (an arrow, and how to open the app the first time). Finder lays this window out, so:
- run the build in a logged-in session, and allow the terminal to control Finder when macOS asks (System Settings → Privacy & Security → Automation);
- eject any mounted `PasaScope <version>` volume first.

Applications in the image is a Finder alias with the folder's icon. On macOS 26 a symlink there shows as a blank tile.

The app carries:
- a standalone CPython 3.12, pinned by SHA-256;
- the packages in `scripts/desktop_bundle/requirements.txt`, at `.venv312`'s exact versions;
- the app code.

Before making the disk image, the script runs `scripts/desktop_bundle/smoke_test.py` with the bundled Python. The smoke test runs these steps without a window:
1. case, consent and session;
2. transcript import and attestation;
3. analysis;
4. a Thai report, drafted, signed and written to PDF;
5. importing the speech pipeline.

Speech models are not in the image. On first use the app downloads them and checks every file's SHA-256, using Settings → Download speech models, or the link on Home:
- the Thai Whisper model, 1.5 GB, a byte-identical copy of the project's own conversion;
- Whisper small;
- the child/adult voice model.

The models are stored in `~/Library/Application Support/PasaScope/.speech-models`. Backups skip that folder.

The bundle is signed ad hoc. Without an Apple Developer ID it cannot be notarised, so macOS blocks the first launch on another Mac. On macOS 15 and later the therapist allows it in System Settings → Privacy & Security → Open Anyway (การตั้งค่าระบบ → ความเป็นส่วนตัวและความปลอดภัย → ยืนยันจะเปิด); on macOS 12–14, right-click → Open also works.

## Windows

`.github/workflows/desktop-windows.yml` runs `scripts/build_windows.py` on a Windows runner. It:
- builds the same self-contained app: standalone CPython 3.12 pinned by SHA-256, the packages at the versions in `scripts/desktop_bundle/constraints.txt`, the app code, and a console-free launcher (`PasaScope.pyw`);
- runs the smoke test with the bundled Python, including a short transcription;
- makes an Inno Setup installer that installs per user in `%LOCALAPPDATA%\Programs\PasaScope` without administrator rights, adds Start menu and desktop shortcuts, and closes a running PasaScope before replacing it;
- installs it silently, opens PasaScope for 30 seconds, uninstalls it and checks that `%APPDATA%\PasaScope` is kept.

It runs on pushes to `feat/desktop-qt` that touch the build, on demand, and when a release is published; for a release it checks that the tag matches `pyproject.toml` and attaches the installer and its `.sha256` to that release, about ten minutes after publishing. The installer is not code-signed, so SmartScreen asks once ("More info", then "Run anyway").

The package versions both builds use come from `scripts/desktop_bundle/constraints.txt`. After changing `.venv312`, refresh it with `.venv312/bin/python scripts/build_macos_dmg.py --write-constraints`.

## Publish

1. Set the version in `pyproject.toml`, `README.md`, `PROJECT_STATUS.md` and `CHANGELOG.md` (repository version policy). Commit, and build.
2. Push the release commit to `main` first. `gh release create` makes the tag at the tip of `main` when the tag does not exist yet, so a release created before the push is tagged on the previous version's code, and GitHub runs the Windows workflow from `main`.
3. Create the release with the disk image (GitHub Actions adds the Windows installer):

   ```bash
   gh release create vX.Y.Z dist/PasaScope-X.Y.Z.dmg dist/PasaScope-X.Y.Z.dmg.sha256 \
       --target "$(git rev-parse HEAD)" --title "PasaScope X.Y.Z" --notes-file <notes>
   ```

   The notes are shown in the app's update window. GitHub accepts files up to 2 GB.
4. Wait for the "Desktop Windows installer" workflow to attach the Windows files (`gh run list --workflow desktop-windows.yml`). If it did not run, start it for the release: `gh workflow run desktop-windows.yml -f release_tag=vX.Y.Z`. That builds from the tag. If an installer fix landed after tagging, add `-f build_ref=main` to build from main (the app version must still match the tag); say so in the release notes.
5. Check the release from a copy of the previous version: Help → "Check for updates…".

Publishing a release makes it public, and every installed copy will offer it. It needs the project owner's go-ahead.
