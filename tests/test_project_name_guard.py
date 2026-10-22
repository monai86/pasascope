from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from project_name_guard import previous_name_violations  # noqa: E402


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_repository_has_no_stray_previous_name():
    assert previous_name_violations(PROJECT_ROOT) == []


def test_previous_name_in_maintained_code_is_reported(tmp_path):
    _write(tmp_path, "apps/api/app/service.py", "name = 'PasaScope'\nclient = LinguaLensClient()\n")
    _write(tmp_path, "scripts/lingualens_tool.py", "print('ok')\n")

    assert previous_name_violations(tmp_path) == [
        "previous project name in apps/api/app/service.py:2",
        "previous project name in file name: scripts/lingualens_tool.py",
    ]


def test_external_names_history_and_local_files_are_allowed(tmp_path):
    _write(tmp_path, "docs/RUNBOOK.md", "Deploy to https://lingualens-web.example.workers.dev using db lingualens_assessment_v2.\n")
    _write(tmp_path, "reports/metrics/old-run.md", "LinguaLens run\n")
    _write(tmp_path, "CHANGELOG.md", "Renamed LinguaLens to PasaScope.\n")
    _write(tmp_path, "apps/pasascope-app/node_modules/pkg/index.js", "// lingualens\n")
    _write(tmp_path, ".local/lingualens-app-repository.json", "{}\n")

    assert previous_name_violations(tmp_path) == []


def test_allowed_token_does_not_excuse_the_rest_of_the_line(tmp_path):
    _write(tmp_path, "docs/RUNBOOK.md", "The lingualens-web worker serves the LinguaLens app.\n")

    assert previous_name_violations(tmp_path) == ["previous project name in docs/RUNBOOK.md:1"]
