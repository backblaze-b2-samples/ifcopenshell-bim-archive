<!-- last_verified: 2026-08-13 -->
# Feature: Clash & quantities (Analyze stage)

## Purpose
The Analyze stage of the pipeline: a quantity take-off (element counts by IfcType
and discipline) and an axis-aligned bounding-box (AABB) clash-candidate pass.

## Used By
- UI: the model-insight panel (quantity take-off table, clash-candidate count) on
  `/projects/[slug]`
- API: produced during `POST /projects/{slug}/run`; archived as
  `analysis/quantities.csv` and `analysis/clash-report.json`

## Core Functions
- `service/archive_runner.py` — `_quantities_csv`, `_clash_candidates`,
  `_overlap_volume`
- `repo/ifc_engine.py` — `analyze_quantities`

## Canonical Files
- Pattern exemplar: `services/api/app/service/archive_runner.py`

## Inputs
- Per-element type counts (from parse) and per-element AABBs (from the geometry
  pass), tagged with model + discipline

## Outputs
- `analysis/quantities.csv` — rows of `ifc_type,<Type>,<count>`,
  `discipline,<name>,<count>`, and a `total,elements,<n>` row
- `analysis/clash-report.json` — `{ multi_model, candidate_count, candidates[] }`
  where each candidate names the two elements/models/types and the overlap volume

## Flow
- Quantity take-off: aggregate `type_counts` across models; add per-discipline
  element counts
- Clash: for each element pair whose AABBs overlap (positive volume), emit a
  candidate. With **multiple models**, only *cross-model* pairs are kept
  (coordination clashes); with a **single model**, intra-model overlaps are kept.
  The pass is bounded (`_MAX_CLASH_ELEMENTS`) so a large model can't blow up the
  O(n²) comparison.

## Scope / honesty
This is a **bounding-box candidate** pass for demonstration — it flags elements
worth a closer look, not a substitute for a full geometric BIM clash-detection
engine.

## Edge Cases
- Single-model project → intra-model overlaps (degraded mode)
- No overlaps → empty `candidates`, `candidate_count: 0`
- Very large models → capped element set for the clash comparison

## UX States
- Clash-candidate count shows as a metric card; `0` is a valid, common result

## Verification
- Test files: `services/api/tests/test_projects_service.py`
  (`test_clash_candidates_cross_model_only`, `test_clash_ignores_same_model_when_multi`,
  `test_quantities_csv_has_types_and_total`)
- Focused verify command: `cd services/api && .venv/bin/python -m pytest tests/test_projects_service.py -k "clash or quantities"`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: overlapping cross-model AABBs yield exactly one candidate; CSV carries types + total

## Related Docs
- [README.md](../../README.md)
- [IFC pipeline](ifc-pipeline.md)
