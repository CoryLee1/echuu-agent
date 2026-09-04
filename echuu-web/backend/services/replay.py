"""Replay payload for an archived live session.

A session's performance is `timeline.json` + step audio. The frontend re-drives
the VRM avatar from those events, so this module only has to find the timeline
(local session dir first, S3 archive second) and make every `audio_url` fetchable.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    from ..config import SCRIPTS_DIR
except ImportError:  # pragma: no cover - flat import when run as a script
    from config import SCRIPTS_DIR

TIMELINE_FILENAME = "timeline.json"


def _s3_bucket() -> str:
    return os.getenv("S3_BUCKET", "echuu-storage")


def _s3_region() -> str:
    return os.getenv("S3_REGION") or os.getenv("AWS_REGION") or "us-east-2"


def s3_public_url(key: str, bucket: Optional[str] = None, region: Optional[str] = None) -> str:
    return f"https://{bucket or _s3_bucket()}.s3.{region or _s3_region()}.amazonaws.com/{key}"


def _session_dir(session: Any) -> Path:
    script_path = getattr(session, "script_path", None)
    if script_path:
        return Path(script_path).parent
    return Path(SCRIPTS_DIR) / str(session.session_id)


def _read_local_timeline(session: Any) -> Optional[dict]:
    path = _session_dir(session) / TIMELINE_FILENAME
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("timeline.json unreadable for %s: %s", session.session_id, exc)
        return None
    return data if isinstance(data, dict) else None


def _read_s3_timeline(session: Any) -> Optional[dict]:
    prefix = str(getattr(session, "s3_prefix", "") or "")
    if not prefix:
        return None
    try:
        import boto3  # local import: boto3 is optional for dev machines
    except ImportError:  # pragma: no cover
        return None
    try:
        client = boto3.client("s3", region_name=_s3_region())
        body = client.get_object(Bucket=_s3_bucket(), Key=f"{prefix}{TIMELINE_FILENAME}")["Body"].read()
        data = json.loads(body)
    except Exception as exc:  # noqa: BLE001 - any S3 failure just means "no replay"
        logger.info("no S3 timeline for %s: %s", session.session_id, exc)
        return None
    if not isinstance(data, dict):
        return None
    # Audio was uploaded next to the timeline; point every step at the public object.
    for event in data.get("events") or []:
        audio_url = event.get("audio_url") if isinstance(event, dict) else None
        if isinstance(audio_url, str) and audio_url:
            event["audio_url"] = s3_public_url(f"{prefix}{Path(audio_url).name}")
    return data


def normalize_timeline(raw: dict) -> dict:
    """Keep only playable step events, sorted by anchor, with the fields replay needs."""
    events = []
    for index, event in enumerate(raw.get("events") or []):
        if not isinstance(event, dict):
            continue
        if event.get("type", "step") != "step":
            continue
        speech = str(event.get("speech") or "").strip()
        audio_url = event.get("audio_url")
        if not speech and not audio_url:
            continue
        item = dict(event)
        item["type"] = "step"
        item["t"] = float(item.get("t") or 0.0)
        item["duration"] = float(item.get("duration") or 0.0)
        item["speech"] = speech
        item.setdefault("index", index)
        events.append(item)
    events.sort(key=lambda item: (item["t"], item["index"]))
    total = float(raw.get("total_duration") or 0.0)
    if events:
        last = events[-1]
        total = max(total, last["t"] + last["duration"])
    return {
        "version": int(raw.get("version") or 1),
        "mode": str(raw.get("mode") or "storytelling"),
        "meta": raw.get("meta") if isinstance(raw.get("meta"), dict) else {},
        "total_duration": round(total, 3),
        "events": events,
    }


def load_replay_timeline(session: Any) -> Optional[dict]:
    """Timeline for a session, or None when nothing replayable was recorded."""
    raw = _read_local_timeline(session) or _read_s3_timeline(session)
    if not raw:
        return None
    timeline = normalize_timeline(raw)
    return timeline if timeline["events"] else None
