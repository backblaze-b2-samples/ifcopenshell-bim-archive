"""Ingest source IFC models into a project prefix, and serve its artifacts.

Two ingest paths, both landing under `projects/<slug>/models/<discipline>/`:
  * `ingest_samples` — author tiny synthetic models server-side (zero setup), and
  * `presign_ingest` — a project-scoped presigned PUT for bring-your-own IFC
    (the browser uploads bytes straight to B2, same pattern as the Upload page).

Also lists/serves everything archived under a project prefix (asset explorer +
downstream presigned serving).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from app.config import settings
from app.repo import (
    author_seed_models,
    generate_presigned_upload,
    get_file_metadata,
    get_presigned_url,
    list_prefix,
    project_prefix,
    put_bytes,
)
from app.service.projects import (
    ProjectError,
    load_project,
    save_project,
)
from app.types import ArtifactEntry, Discipline, PresignUploadResponse
from app.types.formatting import humanize_bytes

MODELS_SECTION = "models"
IFC_CONTENT_TYPE = "application/octet-stream"
_SAFE_NAME_RE = re.compile(r"[^\w.\-]")
# key -> artifact kind, by the section directly under projects/<slug>/.
_KIND_BY_SECTION = {
    "models": "model",
    "metadata": "metadata",
    "geometry": "geometry",
    "analysis": "analysis",
}


def _safe_name(filename: str) -> str:
    name = filename.replace("\\", "/").split("/")[-1]
    name = _SAFE_NAME_RE.sub("_", name).lstrip(".").strip()
    return name or "model.ifc"


def ingest_samples(slug: str):
    """Author license-clean synthetic IFC models and archive them in the project."""
    project = load_project(slug)  # 404s if missing
    for discipline, data in author_seed_models().items():
        key = f"{project_prefix(slug)}{MODELS_SECTION}/{discipline}/seed-{discipline}.ifc"
        put_bytes(key, data, IFC_CONTENT_TYPE)
    project.updated_at = datetime.now(UTC)
    save_project(project)
    return load_project(slug)


def presign_ingest(
    slug: str,
    filename: str,
    discipline: Discipline,
    content_type: str,
    size_bytes: int,
) -> PresignUploadResponse:
    """Presign a project-scoped PUT for a bring-your-own IFC model."""
    load_project(slug)  # 404s if missing
    if size_bytes <= 0:
        raise ProjectError("Empty file")
    if size_bytes > settings.max_file_size:
        raise ProjectError(
            f"File too large. Max size: {humanize_bytes(settings.max_file_size)}",
            status_code=413,
        )
    safe = _safe_name(filename)
    if not safe.lower().endswith(".ifc"):
        raise ProjectError("Only .ifc models can be ingested", status_code=415)
    ct = content_type or IFC_CONTENT_TYPE
    key = f"{project_prefix(slug)}{MODELS_SECTION}/{discipline.value}/{safe}"
    expires_in = settings.presign_upload_expiry_seconds
    url = generate_presigned_upload(key, ct, size_bytes, expires_in)
    return PresignUploadResponse(
        key=key,
        url=url,
        method="PUT",
        content_type=ct,
        headers={"Content-Type": ct},
        expires_in=expires_in,
    )


def _kind_of(key: str, slug: str) -> str:
    rest = key[len(project_prefix(slug)):]
    parts = rest.split("/")
    if len(parts) == 1 and parts[0] == "manifest.json":
        return "manifest"
    return _KIND_BY_SECTION.get(parts[0], "other")


def list_artifacts(slug: str) -> list[ArtifactEntry]:
    """Everything archived under the project prefix (the asset explorer feed)."""
    load_project(slug)  # 404s if missing
    prefix = project_prefix(slug)
    entries: list[ArtifactEntry] = []
    for f in list_prefix("projects/"):
        if not f.key.startswith(prefix):
            continue
        entries.append(
            ArtifactEntry(
                key=f.key,
                filename=f.filename,
                kind=_kind_of(f.key, slug),
                size_bytes=f.size_bytes,
                size_human=f.size_human,
                uploaded_at=f.uploaded_at,
            )
        )
    entries.sort(key=lambda e: e.key)
    return entries


def artifact_download_url(slug: str, key: str) -> str:
    """Presigned GET for one object, confined to this project's prefix."""
    prefix = project_prefix(slug)
    if not key.startswith(prefix) or ".." in key:
        raise ProjectError("Key is outside this project", status_code=400)
    metadata = get_file_metadata(key)
    if metadata is None:
        raise ProjectError("Artifact not found", status_code=404)
    return get_presigned_url(key, filename=metadata.filename, disposition="attachment")
