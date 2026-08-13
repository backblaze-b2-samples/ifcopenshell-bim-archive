"""Real, in-process IfcOpenShell engine tests (no B2, no network).

Authors the synthetic seed models and runs the actual parse + geometry pass via
the subprocess child's `run()` function directly. This proves the sample's
primary feature end-to-end at the engine boundary without touching storage.
"""

import json
from pathlib import Path

from app.repo import author_seed_models, engine_version
from app.repo.ifc_child import run as child_run
from app.repo.ifc_engine import analyze_quantities, parse_entity_tree


def test_engine_version_is_reported():
    version = engine_version()
    assert version != "unavailable"
    assert version[0].isdigit()


def test_author_seed_models_are_valid_ifc():
    models = author_seed_models()
    assert set(models) == {"architectural", "structural"}
    for data in models.values():
        assert data.startswith(b"ISO-10303-21;")
        assert len(data) > 500


def test_parse_and_quantities_on_seed(tmp_path: Path):
    import ifcopenshell

    data = author_seed_models()["architectural"]
    ifc_path = tmp_path / "arch.ifc"
    ifc_path.write_bytes(data)
    model = ifcopenshell.open(str(ifc_path))

    tree = parse_entity_tree(model)
    assert tree["counts"]["elements"] >= 2
    assert tree["counts"]["spaces"] >= 1
    # At least one wall carries the property set we authored.
    assert any(e["property_sets"] for e in tree["elements"])

    quantities = analyze_quantities(model)
    assert quantities["element_count"] == tree["counts"]["elements"]
    assert "IfcWall" in quantities["type_counts"]


def test_child_run_produces_geometry_metadata_and_aabbs(tmp_path: Path):
    data = author_seed_models()["architectural"]
    ifc_path = tmp_path / "arch.ifc"
    ifc_path.write_bytes(data)
    out_dir = tmp_path / "out"

    summary = child_run(str(ifc_path), str(out_dir), "standard")

    assert summary["ok"] is True
    assert summary["mesh_count"] >= 2
    assert summary["element_count"] >= 2

    metadata = json.loads((out_dir / "metadata.json").read_text())
    assert metadata["schema"].startswith("IFC")

    aabbs = json.loads((out_dir / "aabbs.json").read_text())
    assert len(aabbs) == summary["mesh_count"]
    assert all("min" in a and "max" in a for a in aabbs)

    objs = list((out_dir / "meshes").glob("*.obj"))
    assert len(objs) == summary["mesh_count"]
    assert "v " in objs[0].read_text()  # OBJ vertex lines
