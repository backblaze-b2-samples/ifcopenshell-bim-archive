"""The `run` path: parse -> extract geometry -> analyze, archived to B2.

Downloads a project's source IFC models from B2, runs the isolated IfcOpenShell
worker on each (parse + geometry), fans the derived artifacts back out under the
project prefix (metadata JSON, geometry OBJ zips, quantity CSV, clash JSON),
computes write amplification, and persists the final manifest. No database.
"""

from __future__ import annotations

import csv
import io
import json
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from app.repo import get_object_bytes, project_prefix, put_bytes, put_json
from app.service.ifc_worker import (
    IfcCrashed,
    IfcParseError,
    IfcTimeout,
    run_model,
)
from app.service.projects import (
    ProjectError,
    compute_amplification,
    load_project,
    save_project,
)
from app.types import (
    BimStats,
    ClashCandidate,
    ModelEntry,
    PipelineStage,
    Project,
    ProjectStatus,
)

# Bound the clash pass so a large model can't blow up the O(n^2) comparison.
_MAX_CLASH_ELEMENTS = 800

STAGES = ("Parse", "Extract Geometry", "Analyze")


def _stages(status: ProjectStatus, detail: str = "") -> list[PipelineStage]:
    return [PipelineStage(name=name, status=status, detail=detail) for name in STAGES]


def _model_stem(model: ModelEntry) -> str:
    base = model.filename[:-4] if model.filename.lower().endswith(".ifc") else model.filename
    return f"{model.discipline.value}__{base}"


def _zip_meshes(mesh_dir: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for obj_file in sorted(mesh_dir.glob("*.obj")):
            zf.write(obj_file, arcname=obj_file.name)
    return buf.getvalue()


def _overlap_volume(a: dict, b: dict) -> float:
    dx = min(a["max"][0], b["max"][0]) - max(a["min"][0], b["min"][0])
    dy = min(a["max"][1], b["max"][1]) - max(a["min"][1], b["min"][1])
    dz = min(a["max"][2], b["max"][2]) - max(a["min"][2], b["min"][2])
    if dx > 0 and dy > 0 and dz > 0:
        return dx * dy * dz
    return 0.0


def _clash_candidates(aabbs: list[dict], multi_model: bool) -> list[ClashCandidate]:
    """AABB-overlap pairs. Cross-model when >1 model, else intra-model."""
    elements = aabbs[:_MAX_CLASH_ELEMENTS]
    clashes: list[ClashCandidate] = []
    for i in range(len(elements)):
        for j in range(i + 1, len(elements)):
            a, b = elements[i], elements[j]
            if multi_model and a["model"] == b["model"]:
                continue
            vol = _overlap_volume(a, b)
            if vol > 0:
                clashes.append(
                    ClashCandidate(
                        element_a=a["name"] or a["global_id"],
                        element_b=b["name"] or b["global_id"],
                        model_a=a["model"],
                        model_b=b["model"],
                        ifc_type_a=a["ifc_type"],
                        ifc_type_b=b["ifc_type"],
                        overlap_volume=round(vol, 4),
                    )
                )
    return clashes


def _quantities_csv(type_counts: dict[str, int], discipline_counts: dict[str, int]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["category", "key", "count"])
    for t, c in sorted(type_counts.items()):
        writer.writerow(["ifc_type", t, c])
    for d, c in sorted(discipline_counts.items()):
        writer.writerow(["discipline", d, c])
    writer.writerow(["total", "elements", sum(type_counts.values())])
    return buf.getvalue().encode("utf-8")


def _process_model(slug: str, model: ModelEntry, detail: str, work: Path) -> dict:
    """Download one model, run the worker, archive its metadata + geometry."""
    stem = _model_stem(model)
    ifc_path = work / f"{stem}.ifc"
    ifc_path.write_bytes(get_object_bytes(model.key))
    out_dir = work / stem
    out_dir.mkdir(parents=True, exist_ok=True)

    result = run_model(str(ifc_path), str(out_dir), detail)

    metadata = json.loads((out_dir / "metadata.json").read_text())
    put_json(f"{project_prefix(slug)}metadata/{stem}.json", metadata)

    mesh_dir = out_dir / "meshes"
    if mesh_dir.exists():
        put_bytes(
            f"{project_prefix(slug)}geometry/{stem}.obj.zip",
            _zip_meshes(mesh_dir),
            "application/zip",
        )

    aabbs = json.loads((out_dir / "aabbs.json").read_text())
    for a in aabbs:
        a["model"] = stem
        a["discipline"] = model.discipline.value
    return {"result": result, "aabbs": aabbs}


def run_pipeline(slug: str) -> Project:
    project = load_project(slug)
    if not project.models:
        raise ProjectError(
            "No IFC models to run. Ingest a model (or load the samples) first.",
            status_code=409,
        )

    project.status = ProjectStatus.RUNNING
    project.pipeline = _stages(ProjectStatus.RUNNING)
    project.error = None
    save_project(project)

    type_counts: dict[str, int] = {}
    discipline_counts: dict[str, int] = {}
    all_aabbs: list[dict] = []
    element_count = space_count = storey_count = mesh_count = 0

    try:
        with tempfile.TemporaryDirectory(prefix="ifc-run-") as tmp:
            work = Path(tmp)
            for model in project.models:
                processed = _process_model(slug, model, project.geometry_detail.value, work)
                r = processed["result"]
                element_count += r.element_count
                space_count += r.space_count
                storey_count += r.storey_count
                mesh_count += r.mesh_count
                for t, c in r.type_counts.items():
                    type_counts[t] = type_counts.get(t, 0) + c
                discipline_counts[model.discipline.value] = (
                    discipline_counts.get(model.discipline.value, 0) + r.element_count
                )
                all_aabbs.extend(processed["aabbs"])
    except (IfcParseError, IfcTimeout, IfcCrashed) as exc:
        project.status = ProjectStatus.FAILED
        project.error = str(exc)
        project.pipeline = _stages(ProjectStatus.FAILED, str(exc))
        project.updated_at = datetime.now(UTC)
        save_project(project)
        return load_project(slug)

    clashes = _clash_candidates(all_aabbs, multi_model=len(project.models) > 1)
    put_bytes(
        f"{project_prefix(slug)}analysis/quantities.csv",
        _quantities_csv(type_counts, discipline_counts),
        "text/csv",
    )
    put_json(
        f"{project_prefix(slug)}analysis/clash-report.json",
        {
            "generated_at": datetime.now(UTC).isoformat(),
            "multi_model": len(project.models) > 1,
            "candidate_count": len(clashes),
            "candidates": [c.model_dump() for c in clashes],
        },
    )

    project.stats = BimStats(
        model_count=len(project.models),
        element_count=element_count,
        space_count=space_count,
        storey_count=storey_count,
        mesh_count=mesh_count,
        type_counts=type_counts,
        discipline_counts=discipline_counts,
        clash_candidate_count=len(clashes),
    )
    project.write_amplification = compute_amplification(slug)
    project.status = ProjectStatus.SUCCEEDED
    project.pipeline = _stages(ProjectStatus.SUCCEEDED)
    project.last_run_at = datetime.now(UTC)
    project.updated_at = datetime.now(UTC)
    save_project(project)
    return load_project(slug)
