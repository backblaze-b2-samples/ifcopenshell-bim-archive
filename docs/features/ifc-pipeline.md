<!-- last_verified: 2026-08-13 -->
# Feature: IFC pipeline (Parse → Extract Geometry → Analyze)

## Purpose
Turn ingested IFC models into archived, queryable artifacts by running
IfcOpenShell locally: parse the entity tree to JSON, mesh element geometry to
OBJ, and analyze quantities + clash candidates — all fanned out onto Backblaze
B2.

## Used By
- UI: the **Run pipeline** button and pipeline timeline on `/projects/[slug]`
- API: `POST /projects/{slug}/run`

## Core Functions
- `service/archive_runner.py` — `run_pipeline` (orchestration), `_process_model`,
  `_clash_candidates`, `_quantities_csv`
- `service/ifc_worker.py` — `run_model` (subprocess + hard timeout; typed
  `IfcParseError` / `IfcTimeout` / `IfcCrashed`)
- `repo/ifc_engine.py` — `parse_entity_tree`, `analyze_quantities`,
  `author_seed_models`, `deflection_for`
- `repo/ifc_child.py` — the subprocess entrypoint (geometry meshing → OBJ + AABB)

## Canonical Files
- Pattern exemplar: `services/api/app/service/archive_runner.py`

## Inputs
- Source IFC models under `projects/<slug>/models/<discipline>/*.ifc` (B2)
- `geometry_detail` (coarse/standard/fine) → IfcOpenShell linear deflection

## Outputs (archived under the project prefix on B2)
- `metadata/<model>.json` — parsed entity tree (schema, storeys, spaces,
  elements, property sets, type counts)
- `geometry/<model>.obj.zip` — one OBJ mesh per element, zipped
- `analysis/quantities.csv` — quantity take-off (by IfcType + discipline)
- `analysis/clash-report.json` — bounding-box clash candidates
- Manifest update: status, `BimStats`, `WriteAmplification`, `last_run_at`

## Flow
1. Load the project; refuse a run with no models (409)
2. Set status `running`, persist the manifest
3. For each model: download bytes from B2 → run the isolated subprocess (parse +
   mesh + AABB) → upload metadata JSON and geometry OBJ zip
4. Aggregate quantity take-off and cross-model clash candidates; write
   `quantities.csv` + `clash-report.json`
5. Compute write amplification from B2 object sizes; persist status `succeeded`

## Why a subprocess
Native geometry meshing can be heavy or crash. `ifc_worker.run_model` runs
`python -m app.repo.ifc_child` with a hard wall-clock timeout and maps a signal
death (e.g. segfault) to `IfcCrashed`, a timeout to `IfcTimeout`, and a reported
parse/geometry error to `IfcParseError`. A bad model fails the run cleanly
instead of wedging the API worker.

## Device
IfcOpenShell is **CPU-only** — there is no GPU path, so `capabilities.device` is
always `cpu`.

## Edge Cases
- Single-model project → clash pass degrades to intra-model AABB overlaps
- Worker timeout / crash / parse error → status `failed`, `error` set, timeline
  shows the failed stage
- Element with no geometry → skipped in the mesh/AABB pass, still counted in parse

## UX States
- Draft (no run) — timeline shows all stages idle
- Running — timeline shows the in-progress spinner
- Succeeded / Failed — checks or an error with the failure detail

## Verification
- Test files: `services/api/tests/test_ifc_engine.py`,
  `services/api/tests/test_projects_service.py`
- Required cases: author seed → parse → mesh (real, in-process), clash overlap,
  quantities CSV, cross-model-only clash filtering
- Focused verify command: `cd services/api && .venv/bin/python -m pytest tests/test_ifc_engine.py`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: the child produces metadata/meshes/AABBs and a non-zero mesh count

## Related Docs
- [README.md](../../README.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Clash & quantities](clash-quantities.md)
- [Write amplification](write-amplification.md)
