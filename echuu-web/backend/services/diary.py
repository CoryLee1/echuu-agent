"""Shared live diary — public by default, never recites the planner topic title."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    from ..config import SCRIPTS_DIR
except ImportError:
    from config import SCRIPTS_DIR

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

VISIBILITY_PUBLIC = "public"
VISIBILITY_PRIVATE = "private"
GENERIC_LEDE = "今晚聊了一件很小、但想起来还是会停一下的事。"
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
    if hook and len(brief) <= 14:
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
    if not _script_lines(script):
        script = _read_json(_session_file(session, "timeline.json"))
    story_points = [str(item).strip() for item in (memory.get("story_points") or []) if str(item).strip()]
    lines = _script_lines(script)
    started = getattr(session, "started_at", None)
    ended = getattr(session, "ended_at", None)
    duration = _duration_minutes(started, ended)
    cached = meta.get("diary") if isinstance(meta.get("diary"), dict) else {}

    title = str(cached.get("title") or "") or diary_title(topic, story_points, character_name)
    if topic and (title == topic or topic in title):
        title = diary_title(topic, story_points, character_name)

    lede = str(cached.get("lede") or "")
    if lede == GENERIC_LEDE:
        lede = ""
    lede = lede or _lede(lines, topic)
    scene = str(cached.get("scene") or "")
    if cached.get("source") != "llm" and duration and scene and f"{duration} 分钟" not in scene:
        scene = ""
    scene = scene or _scene(story_points, duration, voice)
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


def persist_diary(record: Any, db: Any, rewrite: bool = False) -> dict[str, Any]:
    diary = compose_diary(record)
    cached = (record.session_metadata or {}).get("diary") if isinstance(record.session_metadata, dict) else {}
    already_written = isinstance(cached, dict) and cached.get("source") == "llm" and cached.get("lede") not in {"", GENERIC_LEDE}
    if rewrite or not already_written:
        try:
            diary = {**diary, **write_diary_with_llm(record, diary)}
            diary["source"] = "llm"
        except Exception as exc:  # noqa: BLE001 — 创作失败仍保存模板日记
            print(f"[diary] llm write skipped: {exc}")
            diary["source"] = diary.get("source") or "template"
    meta = dict(record.session_metadata or {})
    meta["diary"] = diary
    record.session_metadata = meta
    try:
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(record, "session_metadata")
    except Exception:
        pass
    _write_diary_file(record, diary)
    db.commit()
    return diary


def write_diary_with_llm(session: Any, draft: dict[str, Any] | None = None) -> dict[str, Any]:
    """再调用一次 LLM，把本场收成第一人称公开日记。"""
    draft = draft or compose_diary(session)
    lines = _session_speeches(session)
    story_points = list(draft.get("tags") or [])
    topic = str(getattr(session, "topic", "") or "")
    name = str(draft.get("character_name") or "我")
    prompt = (
        f"角色名：{name}\n"
        f"本场由头（不要整句复述）：{topic or '今晚随口聊了一会儿'}\n"
        f"时长：{draft.get('duration_minutes') or 0} 分钟\n"
        f"当场说过的话：\n" + ("\n".join(f"- {line}" for line in lines[:16]) or "- （没有留下台词文本）")
    )
    from echuu.live.llm_factory import create_llm_client

    raw = create_llm_client(thinking_level="low").call(
        prompt=prompt,
        system=_DIARY_SYSTEM,
        max_tokens=400,
    )
    written = parse_diary_llm(raw, topic=topic)
    source_material = {"topic": topic, "lines": lines, "story_points": story_points}
    for key in ("title", "lede", "scene", "voice_note"):
        if written.get(key):
            written[key] = _safe_audience(str(written[key]), source_material, draft.get(key) or "")
    if topic and written.get("title") == topic:
        written["title"] = draft.get("title") or diary_title(topic, story_points, name)
    return {key: written[key] for key in ("title", "lede", "scene", "voice_note", "tags") if written.get(key)}


_DIARY_SYSTEM = """你是刚下播的主播本人，用第一人称写一条很短的公开直播日记。
只根据本场说过的话来写，不要编造没发生的大情节，不要复述策划标题全文，不要提 AI / 模型 / prompt。
像写给熟人和观众看的随手记录：有一点余温，不要工作汇报。
有台词：只能用台词里出现过的物件和感觉。
没有台词：只写空落落的余温，不要发明具体食物、地点、人名。
只输出 JSON，不要 markdown：
{"title":"今晚，……（不超过14字）","lede":"第一人称一两句，40到90字","scene":"这一场留下的物件或停顿，一句话","voice_note":"嗓子或气氛的一句余韵","tags":["两到四个短词"]}"""


def parse_diary_llm(raw: str, topic: str = "") -> dict[str, Any]:
    data = _extract_json_object(raw)
    title = str(data.get("title") or "").strip("。．… \n")[:18]
    lede = str(data.get("lede") or "").strip()[:120]
    scene = str(data.get("scene") or "").strip()[:80]
    voice_note = str(data.get("voice_note") or "").strip()[:80]
    tags: list[str] = []
    for item in data.get("tags") or []:
        chunk = str(item).strip()[:6]
        if 2 <= len(chunk) and chunk not in tags:
            tags.append(chunk)
        if len(tags) >= 4:
            break
    if topic and title:
        bare = title.removeprefix("今晚，").removeprefix("今晚")
        if title == topic or topic.startswith(title) or (bare and topic.startswith(bare)):
            title = ""
    if lede == GENERIC_LEDE:
        lede = ""
    return {
        "title": title,
        "lede": lede,
        "scene": scene,
        "voice_note": voice_note,
        "tags": tags,
    }


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("diary llm did not return JSON")
    data = json.loads(cleaned[start:end + 1])
    if not isinstance(data, dict):
        raise ValueError("diary llm JSON was not an object")
    return data


def _safe_audience(text: str, source_material: Any, fallback: str) -> str:
    try:
        from echuu.core.output_safety import sanitize_audience_text
        return sanitize_audience_text(text, source_material=source_material, fallback=fallback).text or fallback
    except Exception:
        return text or fallback


def _session_speeches(session: Any) -> list[str]:
    script = _read_json(getattr(session, "script_path", None) or _session_file(session, "full_script.json"))
    lines = _script_lines(script)
    if not lines:
        lines = _script_lines(_read_json(_session_file(session, "timeline.json")))
    return [line for line in lines if line]


def _write_diary_file(session: Any, diary: dict[str, Any]) -> None:
    try:
        path = _session_file(session, "diary.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(diary, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        print(f"[diary] write file skipped: {exc}")


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
    return GENERIC_LEDE


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
    for event in script.get("events") or []:
        if not isinstance(event, dict):
            continue
        text = str(event.get("speech") or event.get("text") or "").strip()
        if text:
            lines.append(text)
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
