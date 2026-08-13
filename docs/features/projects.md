<!-- last_verified: 2026-08-13 -->
# Feature: Projects

## Purpose
A **Project** is one building or coordination effort — the primary entity of the
archive. It owns a B2 prefix (`projects/<slug>/`) whose `manifest.json` is the
canonical record; there is no database.

## Used By
- UI: `/projects` (library) and `/projects/[slug]` (detail)
- API: `GET/POST /projects`, `GET/PATCH/DELETE /projects/{slug}`,
  `POST /projects/{slug}/run`, `GET /projects/stats`,
  `GET /projects/capabilities`

## Core Functions
- `service/projects.py` — `create_project`, `list_projects`, `get_project`,
  `update_project`, `delete_project`, `get_capabilities`, `get_archive_stats`,
  `compute_amplification`, `slugify`
- `repo/manifest.py` — `read_manifest`, `write_manifest`, `list_manifest_keys`

## Canonical Files
- Pattern exemplar: `services/api/app/service/projects.py`
- Router: `services/api/app/runtime/projects.py`
- Form UX exemplar: `apps/web/src/components/projects/project-form.tsx`

## Inputs
- `ProjectCreate`: `name` (str, 1–120), `discipline` (enum), `geometry_detail` (enum)
- `ProjectUpdate`: any of the above, optional
- `slug`: path parameter (generated from name; uniqueness suffix `-2`, `-3`, …)

## Outputs
- `Project` record (persisted as `manifest.json`), with derived `models`,
  `stats`, and `write_amplification`
- Side effects: B2 `put_object` (manifest), `delete_object` (prefix-scoped delete)

## Lifecycle (all five verbs are user-accessible)
- **create** — `POST /projects` → create dialog on the library
- **read** — `GET /projects` + `GET /projects/{slug}` → library + detail
- **edit** — `PATCH /projects/{slug}` → pre-filled edit dialog
- **delete** — `DELETE /projects/{slug}` → confirm dialog; removes every object
  under `projects/<slug>/` (prefix-scoped)
- **run** — `POST /projects/{slug}/run` → runs the IfcOpenShell pipeline (see
  [IFC pipeline](ifc-pipeline.md))

## Form UX
Finite-option fields are **selectors**, never free text, on both create and edit:
`discipline` and `geometry_detail`. The create form surfaces safe-default
guidance via `FormDescription` (name placeholder, discipline default
*coordination*, geometry-detail default *standard*) — guidance only, no autofill
button. Edit mode opens pre-filled with no default hints.

## Edge Cases
- Duplicate name → slug gets a numeric suffix; both projects coexist
- Delete of a missing project → 404
- `manifest.json` is the record; the `models` list is re-derived from B2 on read,
  so a browser (BYO) ingest shows up without a manifest write
- **Resilient listing**: a single manifest this app can't parse (schema drift, or
  a foreign object dropped in the shared bucket) is logged and skipped by
  `list_projects` rather than 500-ing the whole library. `get_archive_stats`
  counts the same valid set (`len(list_projects())`), so the dashboard's project
  count and the library agree. Genuine infra errors (B2 unreachable) still
  surface — only parse failures are tolerated.

## UX States
- Empty — "No projects yet" with a create CTA
- Loading — skeleton cards / detail skeletons
- Error — inline `ErrorState` with retry
- **Running (stay-on-page)** — the Run request blocks for the whole run, so the
  cached project is optimistically flipped to `running` (`markProjectRunning` in
  `lib/queries.ts`): the status badge shows a spinning "Running" and the pipeline
  stages show per-stage spinners until the response lands, then it reconciles
  (or rolls back on error)

## Verification
- Test files: `services/api/tests/test_projects_service.py`,
  `apps/web/src/lib/queries.test.ts` (`markProjectRunning` optimistic state)
- Required cases: create/read/update/delete, slug uniqueness, capabilities,
  amplification accounting, resilient listing skips a bad manifest, dashboard
  project count agrees with the library
- Focused verify command: `cd services/api && .venv/bin/python -m pytest tests/test_projects_service.py`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: CRUD round-trips against the mocked repo; capabilities report `device: cpu`

## Related Docs
- [README.md](../../README.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [docs/app-workflows.md](../app-workflows.md)
- [IFC pipeline](ifc-pipeline.md)
