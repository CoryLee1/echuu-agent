"""Locate a live session directory, including V4 compat-audio leftovers."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

try:
    from ..config import PROJECT_ROOT, SCRIPTS_DIR
except ImportError:
    from config import PROJECT_ROOT, SCRIPTS_DIR


def _safe_session_id(session_id: str) -> str:
    name = (session_id or "").strip()
    if not name or "/" in name or "\\" in name or ".." in name:
        raise FileNotFoundError(f"Session does not exist: {session_id}")
    return name


def compat_audio_dirs() -> list[Path]:
    candidates: list[Path] = []
    env = os.getenv("ECHUU_COMPAT_AUDIO_DIR", "").strip()
    if env:
        candidates.append(Path(env))
    candidates.append(PROJECT_ROOT / "output" / "compat-audio")
    worktrees = PROJECT_ROOT.parent / ".codex-worktrees"
    if worktrees.is_dir():
        candidates.extend(sorted(worktrees.glob("*/echuu-agent/output/compat-audio")))

    seen: set[Path] = set()
    dirs: list[Path] = []
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        dirs.append(resolved)
    return dirs


def stage_compat_audio(session_id: str) -> Path | None:
    name = _safe_session_id(session_id)
    files: list[Path] = []
    names: set[str] = set()
    for directory in compat_audio_dirs():
        if not directory.is_dir():
            continue
        for filepath in directory.glob(f"{name}*"):
            if filepath.is_file() and filepath.name not in names:
                names.add(filepath.name)
                files.append(filepath)
    if not files:
        return None
    dest = SCRIPTS_DIR / name
    dest.mkdir(parents=True, exist_ok=True)
    for filepath in files:
        target = dest / filepath.name
        if not target.exists():
            shutil.copy2(filepath, target)
    return dest


def resolve_session_dir(session_id: str) -> Path:
    name = _safe_session_id(session_id)
    direct = SCRIPTS_DIR / name
    if direct.is_dir() and any(direct.iterdir()):
        return direct
    staged = stage_compat_audio(name)
    if staged is not None:
        return staged
    raise FileNotFoundError(f"Session does not exist: {session_id}")
