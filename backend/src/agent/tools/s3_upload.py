"""S3 图片/视频上传工具"""

import uuid
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from agent.config import S3_AK, S3_SK, S3_ENDPOINT, S3_REGION, S3_BUCKET, S3_BASE_URL

_s3_client = None


def _get_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            aws_access_key_id=S3_AK,
            aws_secret_access_key=S3_SK,
            endpoint_url=S3_ENDPOINT,
            region_name=S3_REGION,
            use_ssl=True,
        )
    return _s3_client


def upload_bytes(content: bytes, filename: str = "image.png") -> Optional[str]:
    """上传字节内容到 S3，返回完整 URL，失败返回 None。"""
    try:
        ext = Path(filename).suffix or ".png"
        key = f"{uuid.uuid4().hex}{ext}"
        _get_client().put_object(Bucket=S3_BUCKET, Key=key, Body=content)
        url = f"{S3_BASE_URL}/{key}"
        print(f"[S3] 上传成功 {key} -> {url}")
        return url
    except ClientError as e:
        print(f"[S3] 上传失败: {e.response}")
        return None
    except Exception as e:
        print(f"[S3] 上传失败: {e}")
        return None
