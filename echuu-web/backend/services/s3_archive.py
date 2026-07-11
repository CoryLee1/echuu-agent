"""S3 归档服务 — 将直播 session 的音频和脚本上传到 S3"""
import os
import asyncio
import logging
from pathlib import Path
from functools import partial

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

S3_BUCKET = os.getenv("S3_BUCKET", "nextjs-vtuber-assets")
S3_REGION = os.getenv("S3_REGION", "us-east-2")


def _upload_session_sync(session_id: str, session_dir: Path) -> int:
    """同步上传 session 目录中的所有文件到 S3（在 executor 中运行）"""
    s3 = boto3.client(
        "s3",
        region_name=S3_REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )

    uploaded = 0
    for filepath in session_dir.iterdir():
        if not filepath.is_file():
            continue
        key = f"streaming_content/{session_id}/{filepath.name}"
        content_type = "audio/wav" if filepath.suffix == ".wav" else "application/json"
        try:
            s3.upload_file(
                str(filepath),
                S3_BUCKET,
                key,
                ExtraArgs={"ContentType": content_type},
            )
            uploaded += 1
        except ClientError as e:
            logger.error("Failed to upload %s: %s", key, e)

    return uploaded


async def archive_session_to_s3(session_id: str, session_dir: Path) -> int:
    """异步归档 session 目录到 S3，返回上传文件数"""
    loop = asyncio.get_event_loop()
    try:
        uploaded = await loop.run_in_executor(
            None, partial(_upload_session_sync, session_id, session_dir)
        )
        logger.info(
            "Archived session %s to S3: %d files uploaded", session_id, uploaded
        )
        return uploaded
    except Exception:
        logger.exception("Failed to archive session %s to S3", session_id)
        return 0
