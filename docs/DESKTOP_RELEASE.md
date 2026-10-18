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
3. downloads the installer into Downloads and checks it against the SHA-256 file before opening it.

On macOS the therapist then quits the app and drags it onto Applications; on Windows the installer opens and PasaScope closes so it can be replaced. Cases, recordings and settings live in `~/Library/Application Support/PasaScope`, apart from the app, so an update leaves them alone.

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

1. Set the version in `pyproject.toml`, `apps/api/app/main.py`, `README.md`, `PROJECT_STATUS.md` and `CHANGELOG.md` (repository version policy). Commit, and build.
2. Create the release with the disk image (GitHub Actions adds the Windows installer):

   ```bash
   gh release create vX.Y.Z dist/PasaScope-X.Y.Z.dmg dist/PasaScope-X.Y.Z.dmg.sha256 \
       --title "PasaScope X.Y.Z" --notes-file <notes>
   ```

   The notes are shown in the app's update window. GitHub accepts files up to 2 GB.
3. Wait for the "Desktop Windows installer" workflow to attach the Windows files (`gh run list --workflow desktop-windows.yml`).
4. Check the release from a copy of the previous version: Help → "Check for updates…".

Publishing a release makes it public, and every installed copy will offer it. It needs the project owner's go-ahead.
