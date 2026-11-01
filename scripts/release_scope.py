"""Canonical filesystem policy for source review and repository hygiene."""

from __future__ import annotations

from pathlib import Path


FORBIDDEN_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    ".local",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
    "coverage",
    "dist",
    "build",
    ".open-next",
    "uploads",
    "release_artifacts",
    "superpowers",
}
FORBIDDEN_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".tsbuildinfo",
    ".sqlite",
    ".db",
    ".wav",
    ".mp3",
    ".m4a",
    ".flac",
    ".ogg",
    ".zip",
    ".tar",
    ".gz",
    ".docx",
}
LOCAL_ONLY_ROOTS = {
    ".agents",
    ".codex",
    "data/raw",
    "data/curated",
    "docs/release_artifacts",
    "releases",
    # Term paper drafts live beside the code but are git-excluded (the repo is public).
    "TermPaper",
}
LOCAL_RUNTIME_DIR_NAMES = {
    ".freebuff",
    ".worktrees",
    ".venv",
    "venv",
    "node_modules",
    ".local",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
    "coverage",
    "dist",
    "build",
    ".open-next",
    "uploads",
}
LOCAL_RUNTIME_SUFFIXES = {".pyc", ".pyo", ".tsbuildinfo"}
CONTROLLED_PLANNING_ROOTS = {
    "docs/superpowers/plans",
    "docs/superpowers/specs",
}


def is_local_runtime_path(path: Path) -> bool:
    return bool(
        set(path.parts) & LOCAL_RUNTIME_DIR_NAMES
        or any(part.startswith(".venv") for part in path.parts)
        or path.suffix.lower() in LOCAL_RUNTIME_SUFFIXES
    )


def relative_files(root: Path) -> set[str]:
    """Return the same normalized filesystem view with or without Git metadata."""
    files: set[str] = set()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if ".git" in relative.parts:
            continue
        files.add(relative.as_posix())
    return files


def forbidden_reason(relative: str | Path) -> str | None:
    path = Path(relative)
    path_string = path.as_posix()
    is_controlled_planning = any(
        path_string == root or path_string.startswith(root + "/")
        for root in CONTROLLED_PLANNING_ROOTS
    )
    if set(path.parts) & FORBIDDEN_DIR_NAMES and not is_controlled_planning:
        return f"forbidden directory: {path.as_posix()}"
    if path.name == ".DS_Store" or path.name == ".env" or (
        path.name.startswith(".env.") and path.name != ".env.example"
    ):
        return f"forbidden local/secret file: {path.as_posix()}"
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        return f"forbidden file type: {path.as_posix()}"
    if path.as_posix().startswith("scratch/"):
        return f"unclassified planning file: {path.as_posix()}"
    if path_string.startswith("docs/superpowers/") and not is_controlled_planning:
        return f"unclassified planning file: {path.as_posix()}"
    return None


def is_local_only(relative: str | Path) -> bool:
    value = Path(relative).as_posix()
    return any(value == root or value.startswith(root + "/") for root in LOCAL_ONLY_ROOTS)


def consistency_violations(root: Path, *, ignore_local_runtime: bool = False) -> list[str]:
    """Evaluate hygiene without consulting Git, including local raw archives."""
    violations: list[str] = []
    for value in sorted(relative_files(root)):
        path = Path(value)
        if ignore_local_runtime and is_local_runtime_path(path):
            continue
        if value.startswith("data/raw/") and path.suffix.lower() in {".zip", ".tar", ".gz"}:
            violations.append(f"raw corpus archive exists: {value}")
            continue
        reason = forbidden_reason(path)
        if reason and not is_local_only(path):
            violations.append(reason)
    return violations
