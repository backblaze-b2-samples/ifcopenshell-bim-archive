"""Per-project manifest.json I/O — the canonical index (there is no database).

`projects/<slug>/manifest.json` stores the full Project record. This module is
the only reader/writer of that object; service/ layers go through it.
"""

from __future__ import annotations

import json
from typing import Any

from app.repo.artifacts import put_json
from app.repo.b2_client import get_file_metadata, list_files
from app.repo.b2_object import get_object_bytes

MANIFEST_NAME = "manifest.json"
PROJECT_PREFIX = "projects/"


def project_prefix(slug: str) -> str:
    return f"{PROJECT_PREFIX}{slug}/"


def manifest_key(slug: str) -> str:
    return f"{project_prefix(slug)}{MANIFEST_NAME}"


def read_manifest(slug: str) -> dict[str, Any] | None:
    """Return the parsed manifest for `slug`, or None if the project is absent."""
    key = manifest_key(slug)
    if get_file_metadata(key) is None:
        return None
    return json.loads(get_object_bytes(key))


def write_manifest(slug: str, data: dict[str, Any]) -> None:
    put_json(manifest_key(slug), data)


def list_manifest_keys() -> list[str]:
    """Every project's manifest key, discovered by scanning the projects/ tree."""
    keys = []
    for f in list_files(PROJECT_PREFIX):
        if f.key.endswith(f"/{MANIFEST_NAME}"):
            keys.append(f.key)
    return keys


def slug_from_manifest_key(key: str) -> str:
    # projects/<slug>/manifest.json -> <slug>
    return key[len(PROJECT_PREFIX):].rsplit("/", 1)[0]
