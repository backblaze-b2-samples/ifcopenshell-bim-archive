"""Project + BIM-pipeline routes.

Handlers are sync `def` on purpose: the service layer is blocking (B2 I/O and, on
`/run`, a subprocess geometry pass), and Starlette runs sync handlers in its
threadpool — so one slow run never stalls the event loop (see runtime/files.py).
Static paths (`/projects/stats`, `/projects/capabilities`) are declared before
`/projects/{slug}` so the literal routes win over the path param.
"""

import logging

from fastapi import APIRouter, HTTPException

from app.service import ingest
from app.service.archive_runner import run_pipeline
from app.service.projects import (
    ProjectError,
    create_project,
    delete_project,
    get_archive_stats,
    get_capabilities,
    get_project,
    list_projects,
    update_project,
)
from app.types import (
    ArtifactEntry,
    IngestPresignRequest,
    PresignUploadResponse,
    Project,
    ProjectCreate,
    ProjectStats,
    ProjectUpdate,
    ServerCapabilities,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _handle(exc: ProjectError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("/projects", response_model=list[Project])
def list_projects_endpoint():
    return list_projects()


@router.post("/projects", response_model=Project, status_code=201)
def create_project_endpoint(payload: ProjectCreate):
    return create_project(payload)


@router.get("/projects/stats", response_model=ProjectStats)
def project_stats_endpoint():
    return get_archive_stats()


@router.get("/projects/capabilities", response_model=ServerCapabilities)
def project_capabilities_endpoint():
    return get_capabilities()


@router.get("/projects/{slug}", response_model=Project)
def get_project_endpoint(slug: str):
    try:
        return get_project(slug)
    except ProjectError as e:
        raise _handle(e) from None


@router.patch("/projects/{slug}", response_model=Project)
def update_project_endpoint(slug: str, payload: ProjectUpdate):
    try:
        return update_project(slug, payload)
    except ProjectError as e:
        raise _handle(e) from None


@router.delete("/projects/{slug}")
def delete_project_endpoint(slug: str):
    try:
        deleted = delete_project(slug)
    except ProjectError as e:
        raise _handle(e) from None
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Failed to delete project") from None
    logger.info("Project deleted: slug=%s objects=%d", slug, deleted)
    return {"deleted": True, "slug": slug, "objects_removed": deleted}


@router.post("/projects/{slug}/run", response_model=Project)
def run_project_endpoint(slug: str):
    try:
        return run_pipeline(slug)
    except ProjectError as e:
        raise _handle(e) from None
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Storage error during run") from None


@router.post("/projects/{slug}/ingest-samples", response_model=Project)
def ingest_samples_endpoint(slug: str):
    try:
        return ingest.ingest_samples(slug)
    except ProjectError as e:
        raise _handle(e) from None
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Failed to write sample models") from None


@router.post("/projects/{slug}/ingest/presign", response_model=PresignUploadResponse)
def ingest_presign_endpoint(slug: str, payload: IngestPresignRequest):
    try:
        return ingest.presign_ingest(
            slug,
            payload.filename,
            payload.discipline,
            payload.content_type,
            payload.size_bytes,
        )
    except ProjectError as e:
        raise _handle(e) from None


@router.get("/projects/{slug}/artifacts", response_model=list[ArtifactEntry])
def list_artifacts_endpoint(slug: str):
    try:
        return ingest.list_artifacts(slug)
    except ProjectError as e:
        raise _handle(e) from None


@router.get("/projects/{slug}/artifacts/download")
def artifact_download_endpoint(slug: str, key: str):
    try:
        return {"url": ingest.artifact_download_url(slug, key)}
    except ProjectError as e:
        raise _handle(e) from None
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Failed to sign artifact URL") from None
