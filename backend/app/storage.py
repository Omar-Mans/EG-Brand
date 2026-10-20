"""Stores rendered images and returns a public URL (Instagram fetches the image from that URL)."""

import os
import uuid

import httpx

from .config import get_settings


def save_image(data: bytes, company_id: str, ext: str = "png", content_type: str = "image/png") -> str:
    s = get_settings()
    key = f"{company_id}/{uuid.uuid4().hex}.{ext}"
    if s.storage_backend == "s3":
        import boto3

        client = boto3.client("s3", endpoint_url=s.s3_endpoint_url or None,
                              aws_access_key_id=s.s3_access_key, aws_secret_access_key=s.s3_secret_key)
        client.put_object(Bucket=s.s3_bucket, Key=key, Body=data, ContentType=content_type)
        return f"{s.s3_public_base_url.rstrip('/')}/{key}"
    path = os.path.join(s.upload_dir, key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return f"{s.public_base_url.rstrip('/')}/uploads/{key}"


def load_bytes(url: str, max_bytes: int = 40_000_000) -> bytes:
    """Reads back a file we stored (or any public URL). Local files are read from disk, not over HTTP."""
    s = get_settings()
    local = f"{s.public_base_url.rstrip('/')}/uploads/"
    if url.startswith(local):
        root = os.path.realpath(s.upload_dir)
        path = os.path.realpath(os.path.join(root, url[len(local):]))
        if not path.startswith(root + os.sep):
            raise ValueError("bad path")
        with open(path, "rb") as f:
            return f.read(max_bytes)
    with httpx.Client(timeout=60, follow_redirects=True) as c:
        r = c.get(url)
        r.raise_for_status()
        return r.content[:max_bytes]
