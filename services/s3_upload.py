"""
上传 echuu 产出到 AWS S3 存储桶 nextjs-vtuber-assets。

- streaming_content/: 剧本 JSON + 音频 MP3（文+声音）
- memory/: 记忆/收藏 diary（PerformerMemory 快照）
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import boto3
    from botocore.exceptions import ClientError
    _HAS_BOTO = True
except ImportError:
    _HAS_BOTO = False


def _get_bucket() -> str:
    return os.environ.get("S3_BUCKET", "nextjs-vtuber-assets")


def _get_client():
    if not _HAS_BOTO:
        raise RuntimeError("请安装 boto3: pip install boto3")
    return boto3.client(
        "s3",
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    )


def is_s3_configured() -> bool:
    """是否已配置 S3（有 boto3 且至少配置了 key）。"""
    if not _HAS_BOTO:
        return False
    return bool(os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"))


def _serialize_memory(memory: Any) -> Dict[str, Any]:
    """将 PerformerMemory 转为可 JSON 序列化的 dict（含 UserProfile 与 datetime）。"""
    if memory is None:
        return {}
    if isinstance(memory, dict):
        return json.loads(json.dumps(memory, default=str))

    out: Dict[str, Any] = {}

    if hasattr(memory, "script_progress"):
        out["script_progress"] = memory.script_progress or {}
    if hasattr(memory, "danmaku_memory"):
        out["danmaku_memory"] = memory.danmaku_memory or {}
    if hasattr(memory, "story_points"):
        out["story_points"] = memory.story_points or {}
    if hasattr(memory, "promises"):
        out["promises"] = memory.promises or []
    if hasattr(memory, "emotion_track"):
        out["emotion_track"] = memory.emotion_track or []

    if hasattr(memory, "user_profiles") and memory.user_profiles:
        profiles = {}
        for username, u in memory.user_profiles.items():
            p = {
                "username": getattr(u, "username", username),
                "interaction_count": getattr(u, "interaction_count", 0),
                "bonding_level": getattr(u, "bonding_level", 0),
                "reaction_style": getattr(u, "reaction_style", ""),
                "preferred_topics": getattr(u, "preferred_topics", []),
                "special_moments": getattr(u, "special_moments", []),
                "total_sc_amount": getattr(u, "total_sc_amount", 0),
                "sc_history": getattr(u, "sc_history", []),
            }
            for attr in ("first_seen", "last_seen"):
                v = getattr(u, attr, None)
                p[attr] = v.isoformat() if hasattr(v, "isoformat") else v
            profiles[username] = p
        out["user_profiles"] = profiles

    return json.loads(json.dumps(out, default=str))


def upload_streaming_content(
    script_path: Path,
    audio_path: Optional[Path] = None,
    session_key: Optional[str] = None,
    bucket: Optional[str] = None,
) -> Dict[str, str]:
    """
    上传一次直播的「文+声音」到 S3 streaming_content/。

    - script_path: 剧本 JSON 本地路径
    - audio_path: 音频 MP3 本地路径（可选）
    - session_key: S3 下前缀，默认用 script_path.stem（如 20260301_212528_测试_打个招呼）
    - bucket: 桶名，默认从环境变量 S3_BUCKET 读取

    Returns:
        上传后的 S3 key 或 URL 信息，例如 {"script": "streaming_content/xxx/script.json", "audio": "..."}
    """
    bucket = bucket or _get_bucket()
    client = _get_client()
    session_key = session_key or script_path.stem
    prefix = f"streaming_content/{session_key}"
    result = {}

    if not script_path.exists():
        raise FileNotFoundError(f"剧本文件不存在: {script_path}")

    script_key = f"{prefix}/script.json"
    client.upload_file(str(script_path), bucket, script_key, ExtraArgs={"ContentType": "application/json"})
    result["script"] = script_key

    if audio_path and audio_path.exists():
        audio_key = f"{prefix}/audio.mp3"
        client.upload_file(str(audio_path), bucket, audio_key, ExtraArgs={"ContentType": "audio/mpeg"})
        result["audio"] = audio_key

    return result


def upload_memory(
    memory_snapshot: Any,
    session_key: str,
    bucket: Optional[str] = None,
    prefix: str = "memory",
) -> str:
    """
    上传记忆/收藏 diary 到 S3 memory/。

    - memory_snapshot: PerformerMemory 实例或已序列化的 dict
    - session_key: 本次会话标识（如与 streaming_content 同名的 stem）
    - bucket: 桶名
    - prefix: 前缀，默认 "memory"

    Returns:
        上传后的 S3 key，例如 memory/20260301_212528_测试_打个招呼_memory.json
    """
    bucket = bucket or _get_bucket()
    client = _get_client()
    data = _serialize_memory(memory_snapshot)
    key = f"{prefix}/{session_key}_memory.json"
    body = json.dumps(data, ensure_ascii=False, indent=2)
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body.encode("utf-8"),
        ContentType="application/json; charset=utf-8",
    )
    return key


def upload_after_run(
    scripts_dir: Path,
    script_path: Optional[Path] = None,
    audio_path: Optional[Path] = None,
    memory: Any = None,
    bucket: Optional[str] = None,
) -> Dict[str, Any]:
    """
    在一次 run 结束后调用：根据目录中最新的剧本/音频上传到 S3，并可选上传记忆。

    - scripts_dir: 本地 output/scripts 目录
    - script_path: 若已知剧本路径可直接传入；否则在 scripts_dir 下找最新的 .json
    - audio_path: 若已知音频路径可直接传入；否则在 scripts_dir 下找最新的 .mp3
    - memory: PerformerMemory 实例（可选），会上传到 memory/
    - bucket: 桶名

    Returns:
        {"streaming_content": {"script": "...", "audio": "..."}, "memory": "..."}
    """
    if not is_s3_configured():
        return {"skipped": True, "reason": "S3 not configured"}

    bucket = bucket or _get_bucket()
    result = {"streaming_content": {}, "memory": None}

    if script_path is None and scripts_dir.exists():
        jsons = sorted(scripts_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        script_path = jsons[0] if jsons else None
    if script_path is None:
        return result

    session_key = script_path.stem

    if audio_path is None and scripts_dir.exists():
        mp3s = sorted(scripts_dir.glob("*.mp3"), key=lambda p: p.stat().st_mtime, reverse=True)
        audio_path = mp3s[0] if mp3s else None

    try:
        result["streaming_content"] = upload_streaming_content(
            script_path=script_path,
            audio_path=audio_path,
            session_key=session_key,
            bucket=bucket,
        )
    except Exception as e:
        result["streaming_content_error"] = str(e)

    if memory is not None:
        try:
            result["memory"] = upload_memory(memory_snapshot=memory, session_key=session_key, bucket=bucket)
        except Exception as e:
            result["memory_error"] = str(e)

    return result
