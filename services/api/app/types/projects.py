"""Pydantic models for the BIM-archive project domain.

A Project is one building/coordination effort. It owns a B2 prefix
(`projects/<slug>/`) whose canonical index is `manifest.json` — there is no
database, so these models ARE the persisted schema (see repo/manifest.py).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ProjectStatus(StrEnum):
    """Lifecycle of a project's IfcOpenShell pipeline run."""

    DRAFT = "draft"          # created, no run yet
    QUEUED = "queued"        # accepted, not started
    RUNNING = "running"      # parse -> geometry -> analyze in progress
    SUCCEEDED = "succeeded"  # artifacts archived, manifest final
    FAILED = "failed"        # a stage errored (see Project.error)


class Discipline(StrEnum):
    """AEC discipline label. `coordination` means multi-discipline."""

    ARCHITECTURAL = "architectural"
    STRUCTURAL = "structural"
    MECHANICAL = "mechanical"
    ELECTRICAL = "electrical"
    PLUMBING = "plumbing"
    CIVIL = "civil"
    COORDINATION = "coordination"


class GeometryDetail(StrEnum):
    """Mesh fidelity — maps to IfcOpenShell linear-deflection settings."""

    COARSE = "coarse"
    STANDARD = "standard"
    FINE = "fine"


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    discipline: Discipline = Discipline.COORDINATION
    geometry_detail: GeometryDetail = GeometryDetail.STANDARD


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    discipline: Discipline | None = None
    geometry_detail: GeometryDetail | None = None


class IngestPresignRequest(BaseModel):
    """Declared bring-your-own IFC upload — presigned into the project prefix."""

    filename: str
    discipline: Discipline = Discipline.COORDINATION
    content_type: str = "application/octet-stream"
    size_bytes: int


class ModelEntry(BaseModel):
    """One source IFC model ingested under `projects/<slug>/models/`."""

    key: str
    filename: str
    discipline: Discipline
    size_bytes: int
    size_human: str
    uploaded_at: datetime | None = None


class PipelineStage(BaseModel):
    """One step of Parse -> Extract Geometry -> Analyze."""

    name: str
    status: ProjectStatus
    detail: str = ""


class BimStats(BaseModel):
    """Aggregated model insight surfaced on the project detail page."""

    model_count: int = 0
    element_count: int = 0
    space_count: int = 0
    storey_count: int = 0
    mesh_count: int = 0
    # IfcType -> count, across every model in the project.
    type_counts: dict[str, int] = Field(default_factory=dict)
    # Discipline -> element count.
    discipline_counts: dict[str, int] = Field(default_factory=dict)
    clash_candidate_count: int = 0


class WriteAmplification(BaseModel):
    """Source-vs-derived byte accounting — the sample's headline metric."""

    source_bytes: int = 0
    artifact_bytes: int = 0
    total_bytes: int = 0
    source_human: str = "0 B"
    artifact_human: str = "0 B"
    total_human: str = "0 B"
    # artifact_bytes / source_bytes; >= 1.0 means derived data meets/exceeds
    # the source footprint. 0.0 when there is no source yet.
    ratio: float = 0.0


class ArtifactEntry(BaseModel):
    """A derived object archived under the project prefix."""

    key: str
    filename: str
    kind: str  # metadata | geometry | analysis | manifest | model
    size_bytes: int
    size_human: str
    uploaded_at: datetime | None = None


class ClashCandidate(BaseModel):
    """A pair of elements whose axis-aligned bounding boxes overlap."""

    element_a: str
    element_b: str
    model_a: str
    model_b: str
    ifc_type_a: str
    ifc_type_b: str
    overlap_volume: float


class Project(BaseModel):
    """The full project record — this is what `manifest.json` stores."""

    slug: str
    name: str
    discipline: Discipline
    geometry_detail: GeometryDetail
    status: ProjectStatus = ProjectStatus.DRAFT
    created_at: datetime
    updated_at: datetime
    last_run_at: datetime | None = None
    models: list[ModelEntry] = Field(default_factory=list)
    pipeline: list[PipelineStage] = Field(default_factory=list)
    stats: BimStats | None = None
    write_amplification: WriteAmplification | None = None
    error: str | None = None


class ProjectStats(BaseModel):
    """Archive-wide rollup for the dashboard."""

    project_count: int = 0
    model_count: int = 0
    artifact_count: int = 0
    write_amplification: WriteAmplification = Field(
        default_factory=WriteAmplification
    )


class ServerCapabilities(BaseModel):
    """What the local engine can do — reported to the UI."""

    engine: str
    engine_version: str
    device: str  # always "cpu" — IfcOpenShell has no GPU path
    disciplines: list[str]
    geometry_details: list[str]
    accepted_extensions: list[str]
