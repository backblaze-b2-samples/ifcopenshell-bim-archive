"""Artifact object I/O scoped to a project prefix.

Same repo/ layer as b2_client, so boto3/botocore usage is allowed. Reuses the
cached S3 client from b2_client for connection pooling and the shared listing
cache so writes/deletes here stay visible in the file browser and stats.
"""

from __future__ import annotations

import io
import json
from typing import Any

from botocore.exceptions import ClientError

from app.config import settings
from app.repo.b2_client import delete_file, get_s3_client, list_files
from app.repo.list_cache import invalidate as _invalidate_list_cache
from app.types import FileMetadata


def put_bytes(key: str, data: bytes, content_type: str) -> int:
    """Write raw bytes to B2 under `key`. Returns byte count. Raises on failure."""
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=io.BytesIO(data),
            ContentType=content_type,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 put failed for '{key}': {e}") from e
    _invalidate_list_cache()
    return len(data)


def put_json(key: str, obj: Any) -> int:
    """Serialize `obj` to pretty JSON and write it to B2."""
    data = json.dumps(obj, indent=2, default=str).encode("utf-8")
    return put_bytes(key, data, "application/json")


def list_prefix(prefix: str) -> list[FileMetadata]:
    """Every object under `prefix` (via the shared listing cache)."""
    return list_files(prefix)


def delete_prefix(prefix: str) -> int:
    """Delete every object under `prefix`. Returns the count deleted.

    Prefix-scoped by construction — callers pass a fully-qualified
    `projects/<slug>/` prefix so a delete can never wander outside one project.
    """
    files = list_files(prefix)
    for f in files:
        delete_file(f.key)
    return len(files)
