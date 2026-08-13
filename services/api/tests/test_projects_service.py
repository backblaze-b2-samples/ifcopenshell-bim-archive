"""Project store + pipeline-helper tests with the B2 repo boundary mocked."""

import pytest

from app.service import archive_runner, projects
from app.types import (
    Discipline,
    FileMetadata,
    GeometryDetail,
    ProjectCreate,
    ProjectUpdate,
)


@pytest.fixture
def store(monkeypatch):
    """In-memory manifest + object store standing in for B2."""
    manifests: dict[str, dict] = {}
    objects: list[FileMetadata] = []

    def write_manifest(slug, data):
        manifests[slug] = data

    def read_manifest(slug):
        return manifests.get(slug)

    def list_manifest_keys():
        return [f"projects/{slug}/manifest.json" for slug in manifests]

    def list_prefix(prefix):
        return [o for o in objects if o.key.startswith(prefix)]

    def delete_prefix(prefix):
        before = len(objects)
        objects[:] = [o for o in objects if not o.key.startswith(prefix)]
        for slug in list(manifests):
            if prefix == f"projects/{slug}/":
                del manifests[slug]
        return before - len(objects)

    monkeypatch.setattr(projects, "write_manifest", write_manifest)
    monkeypatch.setattr(projects, "read_manifest", read_manifest)
    monkeypatch.setattr(projects, "list_manifest_keys", list_manifest_keys)
    monkeypatch.setattr(projects, "list_prefix", list_prefix)
    monkeypatch.setattr(projects, "delete_prefix", delete_prefix)
    return {"manifests": manifests, "objects": objects}


def test_create_read_update_delete(store):
    created = projects.create_project(
        ProjectCreate(
            name="Riverside Hospital",
            discipline=Discipline.ARCHITECTURAL,
            geometry_detail=GeometryDetail.FINE,
        )
    )
    assert created.slug == "riverside-hospital"
    assert created.status == "draft"

    fetched = projects.get_project("riverside-hospital")
    assert fetched.name == "Riverside Hospital"
    assert fetched.discipline == Discipline.ARCHITECTURAL

    updated = projects.update_project(
        "riverside-hospital", ProjectUpdate(name="Riverside Medical Center")
    )
    assert updated.name == "Riverside Medical Center"
    assert updated.discipline == Discipline.ARCHITECTURAL  # unchanged

    removed = projects.delete_project("riverside-hospital")
    assert removed >= 0
    with pytest.raises(projects.ProjectNotFound):
        projects.get_project("riverside-hospital")


def test_slug_uniqueness(store):
    a = projects.create_project(ProjectCreate(name="Tower A"))
    b = projects.create_project(ProjectCreate(name="Tower A"))
    assert a.slug == "tower-a"
    assert b.slug == "tower-a-2"


def test_list_projects_skips_unreadable_manifest(store):
    """One foreign/legacy manifest must not blank the whole Projects library."""
    projects.create_project(ProjectCreate(name="Good One"))
    # A manifest that doesn't conform to this app's schema (foreign object in the
    # shared bucket, or future drift): unknown status + missing required fields.
    store["manifests"]["legacy"] = {"slug": "legacy", "status": "archived"}

    listed = projects.list_projects()

    slugs = {p.slug for p in listed}
    assert "good-one" in slugs
    assert "legacy" not in slugs


def test_archive_stats_project_count_agrees_with_library(store):
    """The dashboard count and the library list tolerate the same bad manifest."""
    projects.create_project(ProjectCreate(name="Good One"))
    store["manifests"]["legacy"] = {"slug": "legacy", "status": "archived"}

    stats = projects.get_archive_stats()

    assert stats.project_count == len(projects.list_projects()) == 1


def test_capabilities_reports_cpu_and_engine():
    caps = projects.get_capabilities()
    assert caps.engine == "IfcOpenShell"
    assert caps.device == "cpu"
    assert "coordination" in caps.disciplines
    assert caps.accepted_extensions == [".ifc"]


def test_amplification_from_object_sizes(store):
    projects.create_project(ProjectCreate(name="Amp"))
    store["objects"].extend(
        [
            _obj("projects/amp/models/architectural/a.ifc", 1000),
            _obj("projects/amp/metadata/a.json", 2000),
            _obj("projects/amp/geometry/a.obj.zip", 3000),
            _obj("projects/amp/manifest.json", 50),  # excluded from amp
        ]
    )
    amp = projects.compute_amplification("amp")
    assert amp.source_bytes == 1000
    assert amp.artifact_bytes == 5000
    assert amp.ratio == 5.0


def test_clash_candidates_cross_model_only():
    a = _aabb("A", "arch", [0, 0, 0], [2, 2, 2])
    b = _aabb("B", "struct", [1, 1, 1], [3, 3, 3])  # overlaps A
    far = _aabb("C", "struct", [10, 10, 10], [11, 11, 11])
    clashes = archive_runner._clash_candidates([a, b, far], multi_model=True)
    assert len(clashes) == 1
    assert {clashes[0].model_a, clashes[0].model_b} == {"arch", "struct"}


def test_clash_ignores_same_model_when_multi():
    a = _aabb("A", "arch", [0, 0, 0], [2, 2, 2])
    b = _aabb("B", "arch", [1, 1, 1], [3, 3, 3])  # same model -> skipped
    assert archive_runner._clash_candidates([a, b], multi_model=True) == []


def test_quantities_csv_has_types_and_total():
    csv_bytes = archive_runner._quantities_csv({"IfcWall": 3}, {"architectural": 3})
    text = csv_bytes.decode()
    assert "ifc_type,IfcWall,3" in text
    assert "total,elements,3" in text


def _obj(key: str, size: int) -> FileMetadata:
    return FileMetadata(
        key=key,
        filename=key.rsplit("/", 1)[-1],
        folder=key.rsplit("/", 1)[0] + "/",
        size_bytes=size,
        size_human=f"{size} B",
        content_type="application/octet-stream",
        uploaded_at="2026-08-13T00:00:00Z",
    )


def _aabb(name: str, model: str, mn: list, mx: list) -> dict:
    return {
        "global_id": name,
        "name": name,
        "ifc_type": "IfcWall",
        "min": mn,
        "max": mx,
        "model": model,
        "discipline": "coordination",
    }
