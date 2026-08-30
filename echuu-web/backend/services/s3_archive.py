"""S3 归档服务 — 将直播 session 的音频和脚本上传到 S3"""
import os
import asyncio
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from functools import partial

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

logger = logging.getLogger(__name__)

def _s3_bucket() -> str:
    return os.getenv("S3_BUCKET", "echuu-storage")


def _s3_region() -> str:
    return os.getenv("S3_REGION") or os.getenv("AWS_REGION") or "us-east-2"


def _s3_credentials() -> tuple[str | None, str | None]:
    access_key = os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("S3_ACCESS_KEY")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY") or os.getenv("S3_SECRET_KEY")
    return access_key, secret_key


@dataclass(frozen=True)
class ArchiveResult:
    bucket: str
    prefix: str
    uploaded_count: int
    status: str
    error: str | None = None


def _upload_session_sync(session_id: str, session_dir: Path) -> ArchiveResult:
    """同步上传 session 目录中的所有文件到 S3（在 executor 中运行）"""
    access_key, secret_key = _s3_credentials()
    s3 = boto3.client(
        "s3",
        region_name=_s3_region(),
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )

    prefix = f"streaming_content/{session_id}/"
    uploaded = 0
    errors: list[str] = []
    for filepath in session_dir.iterdir():
        if not filepath.is_file():
            continue
        key = f"{prefix}{filepath.name}"
        content_type = "audio/wav" if filepath.suffix == ".wav" else "application/json"
        try:
            s3.upload_file(
                str(filepath),
                _s3_bucket(),
                key,
                ExtraArgs={"ContentType": content_type},
            )
            uploaded += 1
        except ClientError as e:
            logger.error("Failed to upload %s: %s", key, e)
            errors.append(f"{filepath.name}: {e}")

    status = "completed" if uploaded > 0 and not errors else "failed"
    return ArchiveResult(
        bucket=_s3_bucket(),
        prefix=prefix,
        uploaded_count=uploaded,
        status=status,
        error="; ".join(errors)[:2000] or ("session directory was empty" if uploaded == 0 else None),
    )


async def archive_session_to_s3(session_id: str, session_dir: Path) -> dict:
    """异步归档 session 目录到 S3，返回可持久化的结构化结果。"""
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None, partial(_upload_session_sync, session_id, session_dir)
        )
        logger.info(
            "Archived session %s to S3: %d files uploaded", session_id, result.uploaded_count
        )
        return asdict(result)
    except Exception as exc:
        logger.exception("Failed to archive session %s to S3", session_id)
        return asdict(ArchiveResult(
            bucket=_s3_bucket(),
            prefix=f"streaming_content/{session_id}/",
            uploaded_count=0,
            status="failed",
            error=str(exc)[:2000],
        ))
