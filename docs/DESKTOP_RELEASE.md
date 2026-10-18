# Releasing the desktop app

The desktop app updates itself from GitHub Releases of this public repository. Help → "Check for updates…" runs the check on demand, and the app also checks once a day on its own; the automatic check can be switched off in the same menu.

The release format is fixed. Each release:
- is tagged `vX.Y.Z`;
- is not a draft or a pre-release;
- carries two files: `PasaScope-X.Y.Z.dmg` and `PasaScope-X.Y.Z.dmg.sha256`.

The app (`packages/desktop/core/updates.py`):
1. takes the newest such release and compares its version with `pyproject.toml`;
2. offers a backup, written to `~/Documents/PasaScope backups/`;
3. downloads the disk image into Downloads and checks it against the SHA-256 file before opening it.

The therapist then quits the app and drags it onto Applications. Cases, recordings and settings live in `~/Library/Application Support/PasaScope`, apart from the app, so an update leaves them alone.

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

The bundle is signed ad hoc. Without an Apple Developer ID it cannot be notarised, so the first launch on another Mac needs right-click → Open.

## Publish

1. Set the version in `pyproject.toml`, `apps/api/app/main.py`, `README.md`, `PROJECT_STATUS.md` and `CHANGELOG.md` (repository version policy). Commit, and build.
2. Create the release:

   ```bash
   gh release create vX.Y.Z dist/PasaScope-X.Y.Z.dmg dist/PasaScope-X.Y.Z.dmg.sha256 \
       --title "PasaScope X.Y.Z" --notes-file <notes>
   ```

   The notes are shown in the app's update window. GitHub accepts files up to 2 GB.
3. Check the release from a copy of the previous version: Help → "Check for updates…".

Publishing a release makes it public, and every installed copy will offer it. It needs the project owner's go-ahead.
