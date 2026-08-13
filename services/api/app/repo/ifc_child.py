"""Isolated subprocess entrypoint for the heavy IfcOpenShell pass.

Run as `python -m app.repo.ifc_child <ifc_path> <out_dir> <detail>`. It is
launched by `service/ifc_worker.py` in a separate process with a hard timeout,
so a crashing or runaway native geometry pass can never wedge the API worker.

It writes, under <out_dir>:
  * metadata.json            parsed entity tree (see ifc_engine.parse_entity_tree)
  * meshes/<n>_<id>.obj      one OBJ mesh per element with geometry
  * aabbs.json               per-element axis-aligned bounding boxes

and prints a one-line JSON summary to stdout. Exit code 0 == success; any
non-zero exit (including a native segfault's signal) is treated as a failure by
the parent worker.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from app.repo.ifc_engine import analyze_quantities, deflection_for, parse_entity_tree


def _write_obj(path: Path, name: str, verts: list[float], faces: list[int]) -> None:
    lines = [f"# {name}", "o " + (name or "element").replace(" ", "_")]
    for i in range(0, len(verts), 3):
        lines.append(f"v {verts[i]:.6f} {verts[i + 1]:.6f} {verts[i + 2]:.6f}")
    for i in range(0, len(faces), 3):
        # OBJ face indices are 1-based.
        lines.append(f"f {faces[i] + 1} {faces[i + 1] + 1} {faces[i + 2] + 1}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _aabb(verts: list[float]) -> tuple[list[float], list[float]]:
    xs = verts[0::3]
    ys = verts[1::3]
    zs = verts[2::3]
    return (
        [min(xs), min(ys), min(zs)],
        [max(xs), max(ys), max(zs)],
    )


def run(ifc_path: str, out_dir: str, detail: str) -> dict[str, Any]:
    import ifcopenshell
    import ifcopenshell.geom as geom

    out = Path(out_dir)
    mesh_dir = out / "meshes"
    mesh_dir.mkdir(parents=True, exist_ok=True)

    model = ifcopenshell.open(ifc_path)

    metadata = parse_entity_tree(model)
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    settings = geom.settings()
    settings.set("use-world-coords", True)
    settings.set("mesher-linear-deflection", deflection_for(detail))

    aabbs: list[dict[str, Any]] = []
    mesh_count = 0
    iterator = geom.iterator(settings, model)
    if iterator.initialize():
        index = 0
        while True:
            shape = iterator.get()
            verts = list(shape.geometry.verts)
            faces = list(shape.geometry.faces)
            if verts and faces:
                safe = "".join(c if c.isalnum() else "_" for c in (shape.name or "el"))
                _write_obj(mesh_dir / f"{index}_{safe}.obj", shape.name, verts, faces)
                mn, mx = _aabb(verts)
                aabbs.append(
                    {
                        "global_id": shape.guid,
                        "name": shape.name,
                        "ifc_type": shape.type,
                        "min": mn,
                        "max": mx,
                    }
                )
                mesh_count += 1
                index += 1
            if not iterator.next():
                break

    (out / "aabbs.json").write_text(json.dumps(aabbs, indent=2), encoding="utf-8")

    quantities = analyze_quantities(model)
    return {
        "ok": True,
        "mesh_count": mesh_count,
        "element_count": quantities["element_count"],
        "space_count": quantities["space_count"],
        "storey_count": quantities["storey_count"],
        "type_counts": quantities["type_counts"],
    }


def _emit(obj: dict) -> None:
    # stdout is this subprocess's result channel back to the parent worker —
    # a protocol line, not application logging (hence not the JSON logger).
    sys.stdout.write(json.dumps(obj) + "\n")


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        _emit({"ok": False, "error": "usage: ifc_child <ifc> <out> <detail>"})
        return 2
    _, ifc_path, out_dir, detail = argv
    try:
        summary = run(ifc_path, out_dir, detail)
    except Exception as exc:
        # Any native/parse failure is reported as a JSON result, not a traceback.
        _emit({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
        return 1
    _emit(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
