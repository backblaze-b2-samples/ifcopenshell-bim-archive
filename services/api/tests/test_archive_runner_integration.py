"""End-to-end run_pipeline test with the REAL IfcOpenShell subprocess.

Only the B2 boundary is swapped for an in-memory object store; IfcOpenShell
authoring, the isolated subprocess worker, geometry meshing, OBJ zipping, clash
detection, and write-amplification accounting all run for real. This exercises
the sample's primary feature end-to-end (create → ingest → run → artifacts)
without needing live B2 credentials.
"""

import json

import pytest

from app.service import archive_runner, ingest, projects
from app.types import FileMetadata, ProjectCreate


@pytest.fixture
def b2(monkeypatch):
    store: dict[str, bytes] = {}

    def put_bytes(key, data, content_type):
        store[key] = data
        return len(data)

    def put_json(key, obj):
        data = json.dumps(obj, default=str).encode("utf-8")
        store[key] = data
        return len(data)

    def get_object_bytes(key):
        return store[key]

    def read_manifest(slug):
        raw = store.get(f"projects/{slug}/manifest.json")
        return json.loads(raw) if raw is not None else None

    def write_manifest(slug, data):
        store[f"projects/{slug}/manifest.json"] = json.dumps(data, default=str).encode()

    def list_manifest_keys():
        return [k for k in store if k.endswith("/manifest.json")]

    def list_prefix(prefix):
        out = []
        for k, v in store.items():
            if not k.startswith(prefix):
                continue
            out.append(
                FileMetadata(
                    key=k,
                    filename=k.rsplit("/", 1)[-1],
                    folder=k.rsplit("/", 1)[0] + "/",
                    size_bytes=len(v),
                    size_human=f"{len(v)} B",
                    content_type="application/octet-stream",
                    uploaded_at="2026-08-13T00:00:00Z",
                )
            )
        return out

    # Patch the B2 boundary wherever each module imported it.
    monkeypatch.setattr(projects, "read_manifest", read_manifest)
    monkeypatch.setattr(projects, "write_manifest", write_manifest)
    monkeypatch.setattr(projects, "list_manifest_keys", list_manifest_keys)
    monkeypatch.setattr(projects, "list_prefix", list_prefix)
    monkeypatch.setattr(ingest, "put_bytes", put_bytes)
    monkeypatch.setattr(archive_runner, "get_object_bytes", get_object_bytes)
    monkeypatch.setattr(archive_runner, "put_bytes", put_bytes)
    monkeypatch.setattr(archive_runner, "put_json", put_json)
    return store


def test_full_pipeline_with_real_ifcopenshell(b2):
    project = projects.create_project(ProjectCreate(name="Riverside Hospital"))
    slug = project.slug

    # Ingest the two synthetic models (real IfcOpenShell authoring), then run.
    ingest.ingest_samples(slug)
    result = archive_runner.run_pipeline(slug)

    assert result.status == "succeeded"
    assert result.stats is not None
    assert result.stats.model_count == 2
    assert result.stats.element_count >= 3
    assert result.stats.mesh_count >= 3  # walls + slab + beam
    assert "IfcWall" in result.stats.type_counts

    # Cross-model clash candidates (the two models overlap by construction).
    assert result.stats.clash_candidate_count >= 1

    # Write amplification: derived artifacts vs. source IFC bytes.
    amp = result.write_amplification
    assert amp is not None and amp.source_bytes > 0 and amp.artifact_bytes > 0
    # The one-click demo runs at the default "standard" detail and must genuinely
    # amplify: derived artifacts meet or exceed the source IFC bytes (the app's
    # whole thesis). This guards against seed models too trivial to fan out.
    assert amp.artifact_bytes >= amp.source_bytes
    assert amp.ratio >= 1.0

    # Real artifacts were archived under the project prefix.
    keys = set(b2)
    assert any(k.endswith(".obj.zip") for k in keys)
    assert any("/metadata/" in k and k.endswith(".json") for k in keys)
    assert f"projects/{slug}/analysis/quantities.csv" in keys
    assert f"projects/{slug}/analysis/clash-report.json" in keys

    clash = json.loads(b2[f"projects/{slug}/analysis/clash-report.json"])
    assert clash["multi_model"] is True
    assert clash["candidate_count"] == result.stats.clash_candidate_count
