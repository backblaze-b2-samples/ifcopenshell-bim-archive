<!-- last_verified: 2026-08-13 -->
# Feature: Write amplification

## Purpose
Measure and surface the sample's headline metric: a handful of source IFC bytes
fan out into geometry bundles, metadata JSON, and analysis reports whose total
footprint meets or exceeds the source — and B2 holds all of it.

## Used By
- UI: the write-amplification panel on `/projects/[slug]` and the archive rollup
  card on the dashboard (`/`)
- API: per-project value inside `GET /projects/{slug}`; archive-wide via
  `GET /projects/stats`

## Core Functions
- `service/projects.py` — `compute_amplification` (per project),
  `get_archive_stats` (archive-wide)

## Canonical Files
- Pattern exemplar: `services/api/app/service/projects.py`
- UI: `apps/web/src/components/projects/write-amplification-panel.tsx`,
  `apps/web/src/components/dashboard/archive-stats.tsx`

## Inputs
- B2 object sizes under `projects/<slug>/` (per project) or `projects/` (archive)

## Outputs
- `WriteAmplification`: `source_bytes`, `artifact_bytes`, `total_bytes`, their
  human-readable forms, and `ratio` (artifact ÷ source; ≥ 1.0 means derived data
  meets/exceeds source; 0.0 when there is no source yet)

## Flow
- Classify each object by the section directly under the project prefix:
  `models/` → source; `metadata/`, `geometry/`, `analysis/` → artifact;
  `manifest.json` is excluded from the ratio
- Sum sizes, compute the ratio, humanize — all measured **live** from B2, never
  cached in the manifest as the source of truth

## Edge Cases
- No source models yet → ratio `0.0`, source `0 B`
- Reference PDFs/images stored elsewhere in the bucket do not affect a project's
  ratio (only the project prefix is scanned)
- The one-click demo (load samples → run at the default **standard** detail)
  amplifies: the synthetic seed models carry curved geometry whose tessellated
  OBJ, metadata JSON, and clash report together exceed the source IFC bytes, so
  the ratio lands above `1.0`. `test_full_pipeline_with_real_ifcopenshell` guards
  this so seed models can't regress to trivial (de-amplifying) geometry.

## UX States
- Panel only renders once `source_bytes > 0` (after a model is ingested/run)

## Verification
- Test files: `services/api/tests/test_projects_service.py`
  (`test_amplification_from_object_sizes`),
  `services/api/tests/test_archive_runner_integration.py`
  (`test_full_pipeline_with_real_ifcopenshell` — the default demo amplifies ≥ 1.0)
- Required cases: source vs. artifact classification, manifest excluded, ratio,
  default one-click demo lands above 1.0×
- Focused verify command: `cd services/api && .venv/bin/python -m pytest tests/test_projects_service.py -k amplification`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: ratio equals artifact_bytes ÷ source_bytes

## Related Docs
- [README.md](../../README.md)
- [IFC pipeline](ifc-pipeline.md)
- [Dashboard](dashboard.md)
