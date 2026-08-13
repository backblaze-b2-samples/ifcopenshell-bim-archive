"""B2-backed project store — create/list/get/update/delete, no database.

Each project is a `projects/<slug>/` prefix whose `manifest.json` IS the record.
This module owns the manifest <-> Project mapping and the archive-wide rollup;
the pipeline run lives in `archive_runner.py` and ingest in `ingest.py`.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from datetime import UTC, datetime

from app.repo import (
    delete_prefix,
    engine_version,
    list_manifest_keys,
    list_prefix,
    project_prefix,
    read_manifest,
    slug_from_manifest_key,
    write_manifest,
)
from app.types import (
    Discipline,
    GeometryDetail,
    ModelEntry,
    Project,
    ProjectCreate,
    ProjectStats,
    ProjectStatus,
    ProjectUpdate,
    ServerCapabilities,
    WriteAmplification,
)
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)

PROJECTS_ROOT = "projects/"
MODELS_SECTION = "models"
ARTIFACT_SECTIONS = ("metadata", "geometry", "analysis")


class ProjectError(Exception):
    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class ProjectNotFound(ProjectError):
    def __init__(self, slug: str):
        super().__init__(f"Project '{slug}' not found", status_code=404)


class ProjectConflict(ProjectError):
    def __init__(self, detail: str):
        super().__init__(detail, status_code=409)


def _now() -> datetime:
    return datetime.now(UTC)


def slugify(name: str) -> str:
    ascii_name = (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    )
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_name).strip("-").lower()
    return slug or "project"


def _unique_slug(base: str, existing: set[str]) -> str:
    if base not in existing:
        return base
    n = 2
    while f"{base}-{n}" in existing:
        n += 1
    return f"{base}-{n}"


def _list_models(slug: str) -> list[ModelEntry]:
    """Source models under `projects/<slug>/models/<discipline>/`, from B2.

    Derived live so a browser (BYO) ingest or a sample load shows up on the next
    read without a separate manifest write.
    """
    prefix = f"{project_prefix(slug)}{MODELS_SECTION}/"
    models: list[ModelEntry] = []
    for f in list_prefix(PROJECTS_ROOT):
        if not f.key.startswith(prefix):
            continue
        rest = f.key[len(prefix):]
        parts = rest.split("/", 1)
        raw = parts[0] if len(parts) == 2 else ""
        try:
            discipline = Discipline(raw)
        except ValueError:
            discipline = Discipline.COORDINATION
        models.append(
            ModelEntry(
                key=f.key,
                filename=f.filename,
                discipline=discipline,
                size_bytes=f.size_bytes,
                size_human=f.size_human,
                uploaded_at=f.uploaded_at,
            )
        )
    models.sort(key=lambda m: m.key)
    return models


def load_project(slug: str) -> Project:
    data = read_manifest(slug)
    if data is None:
        raise ProjectNotFound(slug)
    project = Project.model_validate(data)
    # Model list is always derived from the bucket so ingests reflect instantly.
    project.models = _list_models(slug)
    return project


def save_project(project: Project) -> None:
    write_manifest(project.slug, project.model_dump(mode="json"))


def _all_slugs() -> set[str]:
    return {slug_from_manifest_key(k) for k in list_manifest_keys()}


def create_project(payload: ProjectCreate) -> Project:
    slug = _unique_slug(slugify(payload.name), _all_slugs())
    now = _now()
    project = Project(
        slug=slug,
        name=payload.name,
        discipline=payload.discipline,
        geometry_detail=payload.geometry_detail,
        status=ProjectStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )
    save_project(project)
    return project


def _safe_load_project(slug: str) -> Project | None:
    """Load one project, tolerating a single unreadable/foreign manifest.

    The manifest IS the record (no database), so a foreign object dropped in the
    shared bucket — or future schema drift — could yield a manifest this app
    can't parse. Aggregations must not let one bad object blank the whole
    discovery hub, so a parse failure (Pydantic `ValidationError`/`ValueError`,
    a bad JSON body, or a mid-scan disappearance) is logged and skipped. Genuine
    infrastructure errors (e.g. B2 unreachable) are *not* caught here and still
    surface, so a real outage isn't silently hidden as "no projects".
    """
    try:
        return load_project(slug)
    except (ProjectError, ValueError) as exc:
        logger.warning("Skipping unreadable project manifest: slug=%s error=%s", slug, exc)
        return None


def list_projects() -> list[Project]:
    loaded = (_safe_load_project(slug_from_manifest_key(k)) for k in list_manifest_keys())
    projects = [p for p in loaded if p is not None]
    projects.sort(key=lambda p: p.created_at, reverse=True)
    return projects


def get_project(slug: str) -> Project:
    return load_project(slug)


def update_project(slug: str, payload: ProjectUpdate) -> Project:
    project = load_project(slug)
    if payload.name is not None:
        project.name = payload.name
    if payload.discipline is not None:
        project.discipline = payload.discipline
    if payload.geometry_detail is not None:
        project.geometry_detail = payload.geometry_detail
    project.updated_at = _now()
    save_project(project)
    return project


def delete_project(slug: str) -> int:
    # Confirm it exists first so a delete of a missing project is a clean 404.
    load_project(slug)
    # Prefix-scoped: only this project's objects are removed.
    return delete_prefix(project_prefix(slug))


def get_capabilities() -> ServerCapabilities:
    return ServerCapabilities(
        engine="IfcOpenShell",
        engine_version=engine_version(),
        device="cpu",
        disciplines=[d.value for d in Discipline],
        geometry_details=[g.value for g in GeometryDetail],
        accepted_extensions=[".ifc"],
    )


def _section_of(key: str, slug: str) -> str | None:
    """Return the section (`models`/`metadata`/...) of a project-scoped key."""
    rest = key[len(project_prefix(slug)):]
    parts = rest.split("/", 1)
    return parts[0] if len(parts) == 2 else None


def compute_amplification(slug: str) -> WriteAmplification:
    """Source-vs-artifact byte accounting for one project, from B2 object sizes."""
    source_bytes = 0
    artifact_bytes = 0
    prefix = project_prefix(slug)
    for f in list_prefix(PROJECTS_ROOT):
        if not f.key.startswith(prefix):
            continue
        section = _section_of(f.key, slug)
        if section == MODELS_SECTION:
            source_bytes += f.size_bytes
        elif section in ARTIFACT_SECTIONS:
            artifact_bytes += f.size_bytes
    total = source_bytes + artifact_bytes
    ratio = (artifact_bytes / source_bytes) if source_bytes else 0.0
    return WriteAmplification(
        source_bytes=source_bytes,
        artifact_bytes=artifact_bytes,
        total_bytes=total,
        source_human=humanize_bytes(source_bytes),
        artifact_human=humanize_bytes(artifact_bytes),
        total_human=humanize_bytes(total),
        ratio=round(ratio, 3),
    )


def get_archive_stats() -> ProjectStats:
    """Archive-wide rollup across every project prefix (for the dashboard)."""
    source_bytes = 0
    artifact_bytes = 0
    model_count = 0
    artifact_count = 0
    project_count = 0
    for f in list_prefix("projects/"):
        rest = f.key[len("projects/"):]
        parts = rest.split("/")
        if len(parts) < 2:
            continue
        section = parts[1] if len(parts) >= 3 else None
        if section == MODELS_SECTION:
            source_bytes += f.size_bytes
            model_count += 1
        elif section in ARTIFACT_SECTIONS:
            artifact_bytes += f.size_bytes
            artifact_count += 1
    # Count only projects the library can actually load, so the dashboard's
    # project count agrees with /projects (both tolerate a foreign/drifted
    # manifest instead of one poisoning the surface).
    project_count = len(list_projects())
    total = source_bytes + artifact_bytes
    ratio = (artifact_bytes / source_bytes) if source_bytes else 0.0
    return ProjectStats(
        project_count=project_count,
        model_count=model_count,
        artifact_count=artifact_count,
        write_amplification=WriteAmplification(
            source_bytes=source_bytes,
            artifact_bytes=artifact_bytes,
            total_bytes=total,
            source_human=humanize_bytes(source_bytes),
            artifact_human=humanize_bytes(artifact_bytes),
            total_human=humanize_bytes(total),
            ratio=round(ratio, 3),
        ),
    )
