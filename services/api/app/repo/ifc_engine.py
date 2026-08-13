"""Thin wrapper over IfcOpenShell — the sample's local, keyless BIM engine.

Everything that touches the `ifcopenshell` native wheel lives in this repo/
module (and its subprocess sibling `ifc_child.py`). Imports are lazy so a
missing//broken wheel degrades to a clear per-feature error instead of taking
down the whole API at import time.

Two responsibilities:
  * author tiny, fully-synthetic seed IFC models (license-clean demo data), and
  * parse a model's entity tree + quantities to JSON-serializable dicts.

Geometry meshing (the crash-prone native pass) is NOT here — it runs in an
isolated subprocess; see `ifc_child.py` and `service/ifc_worker.py`.
"""

from __future__ import annotations

from typing import Any

# Linear-deflection (metres) per geometry-detail level. Smaller = finer mesh.
DEFLECTION_BY_DETAIL: dict[str, float] = {
    "coarse": 0.05,
    "standard": 0.01,
    "fine": 0.002,
}


def deflection_for(detail: str) -> float:
    return DEFLECTION_BY_DETAIL.get(detail, DEFLECTION_BY_DETAIL["standard"])


def engine_version() -> str:
    """IfcOpenShell version string, or 'unavailable' if the wheel won't import."""
    try:
        import ifcopenshell

        return str(ifcopenshell.version)
    except Exception:
        return "unavailable"


def _pset_summary(element: Any) -> dict[str, Any]:
    import ifcopenshell.util.element as ue

    try:
        psets = ue.get_psets(element)
    except Exception:
        return {}
    # Drop the internal `id` bookkeeping key ifcopenshell adds per pset.
    return {
        name: {k: v for k, v in props.items() if k != "id"}
        for name, props in psets.items()
    }


def parse_entity_tree(model: Any) -> dict[str, Any]:
    """Serialize a model's spatial tree, elements, spaces and property sets.

    Bounded and JSON-safe: this is what gets archived as `metadata/<model>.json`.
    """
    import ifcopenshell.util.element as ue

    projects = model.by_type("IfcProject")
    project_name = projects[0].Name if projects else None

    storeys = []
    for st in model.by_type("IfcBuildingStorey"):
        storeys.append(
            {
                "global_id": st.GlobalId,
                "name": st.Name,
                "elevation": float(st.Elevation) if st.Elevation is not None else None,
            }
        )

    spaces = []
    for sp in model.by_type("IfcSpace"):
        spaces.append(
            {
                "global_id": sp.GlobalId,
                "name": sp.Name,
                "long_name": getattr(sp, "LongName", None),
            }
        )

    elements = []
    type_counts: dict[str, int] = {}
    for el in model.by_type("IfcElement"):
        ifc_type = el.is_a()
        type_counts[ifc_type] = type_counts.get(ifc_type, 0) + 1
        container = None
        try:
            parent = ue.get_container(el)
            container = parent.Name if parent is not None else None
        except Exception:
            container = None
        elements.append(
            {
                "global_id": el.GlobalId,
                "ifc_type": ifc_type,
                "name": el.Name,
                "storey": container,
                "property_sets": _pset_summary(el),
            }
        )

    return {
        "schema": model.schema,
        "project_name": project_name,
        "counts": {
            "elements": len(elements),
            "spaces": len(spaces),
            "storeys": len(storeys),
        },
        "type_counts": type_counts,
        "storeys": storeys,
        "spaces": spaces,
        "elements": elements,
    }


def analyze_quantities(model: Any) -> dict[str, Any]:
    """Quantity take-off: element counts by IfcType + spatial totals."""
    type_counts: dict[str, int] = {}
    for el in model.by_type("IfcElement"):
        t = el.is_a()
        type_counts[t] = type_counts.get(t, 0) + 1
    return {
        "type_counts": type_counts,
        "element_count": sum(type_counts.values()),
        "space_count": len(model.by_type("IfcSpace")),
        "storey_count": len(model.by_type("IfcBuildingStorey")),
    }


def author_seed_models() -> dict[str, bytes]:
    """Return a dict of {discipline: ifc_bytes} of tiny synthetic models.

    Fully authored in-process via the IfcOpenShell API — no third-party data,
    so redistribution is license-clean. Two overlapping models (architectural +
    structural) so a demo `run` produces real cross-model clash candidates.
    """
    return {
        "architectural": _author_architectural(),
        "structural": _author_structural(),
    }


def _new_model(project_name: str):
    from ifcopenshell.api import run

    model = run("project.create_file")
    project = run("root.create_entity", model, ifc_class="IfcProject", name=project_name)
    run("unit.assign_unit", model)
    ctx = run("context.add_context", model, context_type="Model")
    body = run(
        "context.add_context",
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=ctx,
    )
    site = run("root.create_entity", model, ifc_class="IfcSite", name="Site")
    building = run("root.create_entity", model, ifc_class="IfcBuilding", name="Building")
    storey = run(
        "root.create_entity", model, ifc_class="IfcBuildingStorey", name="Level 1"
    )
    run("aggregate.assign_object", model, relating_object=project, products=[site])
    run("aggregate.assign_object", model, relating_object=site, products=[building])
    run("aggregate.assign_object", model, relating_object=building, products=[storey])
    return model, body, storey


def _add_wall(model, body, storey, name, length, height, thickness):
    from ifcopenshell.api import run

    wall = run("root.create_entity", model, ifc_class="IfcWall", name=name)
    rep = run(
        "geometry.add_wall_representation",
        model,
        context=body,
        length=length,
        height=height,
        thickness=thickness,
    )
    run("geometry.assign_representation", model, product=wall, representation=rep)
    run("spatial.assign_container", model, relating_structure=storey, products=[wall])
    return wall


def _author_architectural() -> bytes:
    from ifcopenshell.api import run

    model, body, storey = _new_model("Seed — Architectural")
    w1 = _add_wall(model, body, storey, "Exterior Wall N", 6.0, 3.0, 0.3)
    _add_wall(model, body, storey, "Exterior Wall E", 4.0, 3.0, 0.3)
    slab = run("root.create_entity", model, ifc_class="IfcSlab", name="Floor Slab")
    slab_rep = run(
        "geometry.add_slab_representation",
        model,
        context=body,
        depth=0.3,
        polyline=[(0.0, 0.0), (6.0, 0.0), (6.0, 4.0), (0.0, 4.0)],
    )
    run("geometry.assign_representation", model, product=slab, representation=slab_rep)
    run("spatial.assign_container", model, relating_structure=storey, products=[slab])
    space = run("root.create_entity", model, ifc_class="IfcSpace", name="Room 101")
    run("aggregate.assign_object", model, relating_object=storey, products=[space])
    pset = run("pset.add_pset", model, product=w1, name="Pset_WallCommon")
    run(
        "pset.edit_pset",
        model,
        pset=pset,
        properties={"IsExternal": True, "LoadBearing": False},
    )
    return model.to_string().encode("utf-8")


def _author_structural() -> bytes:
    from ifcopenshell.api import run

    model, body, storey = _new_model("Seed — Structural")
    # A load-bearing wall placed to overlap the architectural exterior wall's
    # bounding box, so cross-model clash detection has a real candidate.
    w = _add_wall(model, body, storey, "Shear Wall N", 6.0, 3.0, 0.4)
    beam = run("root.create_entity", model, ifc_class="IfcBeam", name="Roof Beam")
    beam_rep = run(
        "geometry.add_wall_representation",
        model,
        context=body,
        length=6.0,
        height=0.4,
        thickness=0.3,
    )
    run("geometry.assign_representation", model, product=beam, representation=beam_rep)
    run("spatial.assign_container", model, relating_structure=storey, products=[beam])
    pset = run("pset.add_pset", model, product=w, name="Pset_WallCommon")
    run("pset.edit_pset", model, pset=pset, properties={"LoadBearing": True})
    return model.to_string().encode("utf-8")
