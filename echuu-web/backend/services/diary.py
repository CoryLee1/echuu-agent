"""Shared live diary — public by default, never recites the planner topic title."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from ..config import SCRIPTS_DIR
except ImportError:
    from config import SCRIPTS_DIR

VISIBILITY_PUBLIC = "public"
VISIBILITY_PRIVATE = "private"
_SKIP_TAG_CHUNKS = {
    "时候", "最后", "发现", "一起", "半夜", "第二天", "下雨天",
    "出去", "却发现", "想办法",
}


def is_public_diary(metadata: Any) -> bool:
    if not isinstance(metadata, dict):
        return True
    diary = metadata.get("diary")
    visibility = ""
    if isinstance(diary, dict):
        visibility = str(diary.get("visibility") or "")
    visibility = visibility or str(metadata.get("visibility") or "")
    return visibility.strip().lower() != VISIBILITY_PRIVATE


def diary_title(topic: str, story_points: list[str], character_name: str = "") -> str:
    """Audience-facing title. Never echo the full topic brief."""
    brief = (topic or "").strip()
    for point in story_points:
        hook = _first_clause(point)
        if hook and hook != brief:
            return _tonight(hook)
    hook = _first_clause(brief)
    if hook and hook != brief and len(hook) <= 14:
        return _tonight(hook)
    if character_name:
        return f"今晚这一场 · {character_name}"
    return "今晚这一场"


def tags_from_topic(topic: str, story_points: list[str] | None = None) -> list[str]:
    tags: list[str] = []
    for point in story_points or []:
        chunk = _first_clause(point)
        if 2 <= len(chunk) <= 6 and chunk not in tags:
            tags.append(chunk)
    for match in re.finditer(r"[\u4e00-\u9fff]{2,4}", topic or ""):
        chunk = match.group(0)
        if chunk in _SKIP_TAG_CHUNKS or chunk in tags:
            continue
        tags.append(chunk)
        if len(tags) >= 4:
            break
    return tags[:4] or ["夜聊"]


def compose_diary(session: Any) -> dict[str, Any]:
    meta = dict(session.session_metadata or {})
    topic = str(session.topic or "")
    character_name = str(
        meta.get("character_name")
        or (session.character.name if getattr(session, "character", None) else "")
        or ""
    )
    voice = str(meta.get("voice") or "")
    if not voice and getattr(session, "voice_config", None):
        voice = str(getattr(session.voice_config, "voice_name", "") or "")

    memory = _read_json(_session_file(session, "memory.json"))
    script = _read_json(getattr(session, "script_path", None) or _session_file(session, "full_script.json"))
    story_points = [str(item).strip() for item in (memory.get("story_points") or []) if str(item).strip()]
    lines = _script_lines(script)
    started = getattr(session, "started_at", None)
    ended = getattr(session, "ended_at", None)
    duration = _duration_minutes(started, ended)
    cached = meta.get("diary") if isinstance(meta.get("diary"), dict) else {}

    title = str(cached.get("title") or "") or diary_title(topic, story_points, character_name)
    if topic and (title == topic or topic in title):
        title = diary_title(topic, story_points, character_name)

    lede = str(cached.get("lede") or "") or _lede(lines, topic)
    scene = str(cached.get("scene") or "") or _scene(story_points, duration, voice)
    voice_note = str(cached.get("voice_note") or "") or _voice_note(voice, started)
    tags = list(cached.get("tags") or tags_from_topic(topic, story_points))

    return {
        "visibility": str(cached.get("visibility") or VISIBILITY_PUBLIC),
        "session_id": session.session_id,
        "title": title,
        "lede": lede,
        "scene": scene,
        "voice_note": voice_note,
        "tags": tags[:4],
        "character_name": character_name,
        "voice": voice,
        "cover_url": cached.get("cover_url") or meta.get("cover_url"),
        "started_at": _iso(started),
        "ended_at": _iso(ended),
        "duration_minutes": duration,
        "status": _status_value(session),
        "archive_status": getattr(session, "archive_status", None),
    }


def persist_diary(record: Any, db: Any) -> dict[str, Any]:
    diary = compose_diary(record)
    meta = dict(record.session_metadata or {})
    meta["diary"] = diary
    record.session_metadata = meta
    try:
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(record, "session_metadata")
    except Exception:
        pass
    db.commit()
    return diary


def _tonight(hook: str) -> str:
    text = hook.strip("。．… ")
    if text.startswith("今晚"):
        return text
    return f"今晚，{text}"


def _first_clause(text: str) -> str:
    raw = re.split(r"[，,。！？!?\n—–]", (text or "").strip())[0].strip()
    return raw[:18]


def _lede(lines: list[str], topic: str) -> str:
    for line in lines:
        cleaned = line.strip()
        if topic and topic in cleaned:
            cleaned = cleaned.replace(topic, "刚才那事")
        if len(cleaned) >= 12:
            return cleaned[:90]
    return "今晚聊了一件很小、但想起来还是会停一下的事。"


def _scene(story_points: list[str], duration: int, voice: str) -> str:
    parts: list[str] = []
    if duration:
        parts.append(f"这场开了大约 {duration} 分钟")
    if voice:
        parts.append(f"声音是 {voice}")
    if story_points:
        parts.append("场上留下：" + "、".join(story_points[:3]))
    return "。".join(parts) + "。" if parts else "场上没有再记下别的，就这一场。"


def _voice_note(voice: str, started: datetime | None) -> str:
    hour = started.hour if started else 21
    if hour < 6:
        when = "后半夜"
    elif hour < 12:
        when = "上午"
    elif hour < 18:
        when = "下午"
    else:
        when = "夜里"
    if voice:
        return f"{when}用的是 {voice}，像刚说完还没完全从那场里出来。"
    return f"{when}这一场，嗓子还停在刚才的句子上。"


def _script_lines(script: Any) -> list[str]:
    if isinstance(script, list):
        return [str(item.get("text") or "").strip() for item in script if isinstance(item, dict) and item.get("text")]
    if not isinstance(script, dict):
        return []
    lines: list[str] = []
    for unit in script.get("units") or []:
        if not isinstance(unit, dict):
            continue
        for line in unit.get("lines") or []:
            text = str((line or {}).get("text") or "").strip()
            if text:
                lines.append(text)
    return lines


def _session_file(session: Any, name: str) -> Path:
    script_path = getattr(session, "script_path", None)
    if script_path:
        return Path(script_path).parent / name
    return SCRIPTS_DIR / str(session.session_id) / name


def _read_json(path: str | Path | None) -> dict:
    if not path:
        return {}
    file_path = Path(path)
    if not file_path.is_file():
        return {}
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() + ("Z" if value and value.tzinfo is None else "") if value else None


def _duration_minutes(started: datetime | None, ended: datetime | None) -> int:
    if not started or not ended:
        return 0
    return max(0, int(round((ended - started).total_seconds() / 60)))


def _status_value(session: Any) -> str:
    status = getattr(session, "status", None)
    if hasattr(status, "value"):
        return str(status.value)
    return str(status or "")
