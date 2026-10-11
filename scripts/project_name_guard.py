"""Keep the project's previous name from returning to maintained files.

The project was renamed from LinguaLens to PasaScope. The old name may still
appear in historical records, in the names of external resources that were not
renamed, in persisted identifiers, and in the code that reads data written
under the old name. Anywhere else it is a regression.
"""

from __future__ import annotations

import re
from pathlib import Path

from release_scope import is_local_runtime_path, relative_files

PREVIOUS_NAME = re.compile(r"lingualens", re.IGNORECASE)

# Dated records and reports of past work: they describe the project as it was.
HISTORICAL_PREFIXES = (
    "docs/archive/",
    "docs/release_artifacts/",
    "docs/plans/",
    "docs/superpowers/",
    "docs/readiness/",
    "docs/frontend/",
    "docs/core-speech-testbed/",
    "docs/ux/",
    "docs/literature/",
    "reports/",
    "data/",
    ".agents/",
    ".windsurf/",
    "releases/",
)
HISTORICAL_FILES = {
    "CHANGELOG.md",
    "docs/ANTIGRAVITY_HANDOFF_PROGRESS.md",
    "docs/THERAPIST_APP_V2_RENAME_AUDIT.md",
    "docs/RENAME_FOLLOWUP.md",
    "scripts/project_name_guard.py",
    "tests/test_project_name_guard.py",
}
# Files whose job is to read data or settings written under the old name.
FALLBACK_FILES = {
    "apps/api/app/core/config.py",
    "apps/api/tests/test_workflow.py",
    "apps/pasascope-app/src/lib/storage-key-migration.ts",
    "apps/pasascope-app/src/__tests__/storage-key-migration.test.ts",
    "scripts/clean_mock_data.py",
    "scripts/report_transcript_review_time.py",
    "scripts/check_project.sh",
    "docker-compose.yml",
    "tests/test_deployment_config.py",
}
# External resources and persisted identifiers that keep the old name.
# See docs/RENAME_FOLLOWUP.md before changing any of these.
ALLOWED_TOKENS = [
    r"/Users/porschecaa/lingualens[^\s\"'`)>]*",
    r"[a-z]+://[^\s\"'`)>]*lingualens[^\s\"'`)>]*",
    r"monai86/lingualens",
    r"lingualens-web",
    r"lingualens-api\b(?:-staging|-production)?",
    r"lingualens-staging[a-z-]*",
    r"lingualens-production",
    r"[A-Za-z0-9_.+-]*@lingualens[a-z.-]*",
    r"org_lingualens_[a-z]",
    r"lingualens_assessment[a-z0-9_]*",
    r"lingualens_native_",
    r"lingualens-(?:thai-mixed-tokenizer|chat-subset|cha-parser|cha-serializer)-v1",
    r"lingualens-app-local",
    r"LinguaLens_ML_Features_and_Results_Summary",
    r"[\w./-]*lingualens-org[\w.-]*",
    r"เดิม LinguaLens",
]
_ALLOWED = re.compile("|".join(ALLOWED_TOKENS))


def _is_local_tool_directory(path: Path) -> bool:
    """Hidden top-level directories other than .github hold local tool state."""
    return len(path.parts) > 1 and path.parts[0].startswith(".") and path.parts[0] != ".github"


def previous_name_violations(root: Path) -> list[str]:
    violations: list[str] = []
    for relative in sorted(relative_files(root)):
        path = Path(relative)
        if (
            relative in HISTORICAL_FILES
            or relative in FALLBACK_FILES
            or relative.startswith(HISTORICAL_PREFIXES)
            or relative.endswith("package-lock.json")
            or is_local_runtime_path(path)
            or _is_local_tool_directory(path)
        ):
            continue
        if PREVIOUS_NAME.search(path.name):
            violations.append(f"previous project name in file name: {relative}")
        try:
            text = (root / path).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if PREVIOUS_NAME.search(_ALLOWED.sub("", line)):
                violations.append(f"previous project name in {relative}:{number}")
    return violations
