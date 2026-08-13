<!-- last_verified: 2026-08-06 -->
# Architecture

This is a BIM digital-twin archive: projects own a B2 prefix, IFC models are
ingested into them, and a local IfcOpenShell pipeline fans each model out into
metadata, geometry, and analysis artifacts archived on B2. The starter's
full-bucket File Explorer, Upload, and design system are kept as-is; the project
+ pipeline domain is layered on top.

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - **Projects** library + detail: create/read/edit/delete/run, pipeline
    timeline, BIM stats, write-amplification panel, project-scoped asset explorer
  - Dashboard with archive-wide write amplification + project/model counts, plus
    upload stats, chart, recent uploads
  - Full-bucket file browser (preview, download, delete) and drag-and-drop upload
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - REST API for projects, the IfcOpenShell pipeline run, ingest, and artifacts
  - **IfcOpenShell** engine wrapper (parse entity tree, mesh geometry to OBJ,
    quantity take-off + bounding-box clash candidates), run in an isolated
    subprocess with a hard timeout
  - B2 S3 integration via boto3; per-project `manifest.json` as the record
  - File metadata extraction (IFC header/entity-tree, plus images, PDFs)
  - Health check, structured JSON logging, Prometheus-format metrics endpoint
- **packages/shared/** — TypeScript type definitions
  - Mirrors Pydantic models from the API (files + project domain)
  - Consumed by `apps/web/` as workspace dependency

## Backend Layering

The API follows a strict layered architecture:

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access (boto3 B2 client) — no business logic
  |
service/   Business logic — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` only allowed in `repo/` layer
4. All boundary data uses Pydantic models (no raw dicts across layers)
5. Authored Python files under `services/api/app/` stay under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (FileMetadata, Project, BimStats, ...)
    config/                Settings loaded from environment (B2_REGION-derived endpoint)
    repo/                  B2 S3 client + manifest/artifact I/O + IfcOpenShell engine
                           (b2_client, artifacts, manifest, ifc_engine, ifc_child)
    service/               Business logic (upload, files, projects, ingest,
                           archive_runner, ifc_worker)
    runtime/               FastAPI route handlers (files, upload, projects, ...)
  seed/                    Tiny synthetic seed IFC models (license-clean)
  tests/                   pytest tests (structural + integration + engine)
```

IfcOpenShell imports are contained to `repo/ifc_engine.py` (authoring + parse +
analyze) and `repo/ifc_child.py` (the subprocess geometry entrypoint). `boto3`
stays only in `repo/`.

## Boundary Invariants

- **No external SDK leakage**: `boto3` is only imported in `app/repo/`. All other layers interact with B2 through the repo interface.
- **No raw dicts at boundaries**: All data crossing layer boundaries uses typed Pydantic models.
- **No cross-layer mutable state**: Configuration is read-only after init, and no mutable state is shared *between* layers. Intra-layer caches/counters (the listing cache in `repo/list_cache.py`, the B2 connectivity cache in `repo/b2_client.py`, the download counter in `repo/counter.py`, the rate-limit and metrics state in `runtime/`) are module-local and guarded by a `threading.Lock`. The listing cache also owns the only background thread in the app: a stale entry is served immediately while that thread re-scans (stale-while-revalidate), and `main.lifespan` warms it once at startup so no user pays for the cold full-bucket scan.
- **Validated inputs**: All HTTP inputs validated by FastAPI/Pydantic. File keys reject empty and path-traversal patterns; optional prefix confinement via `ALLOWED_KEY_PREFIX` (off by default).

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently`
  - Web: `localhost:3000`
  - API: `localhost:8000`
- **Railway** — two services from the same repository: `web` builds from the
  repository root because it consumes `packages/shared`; `api` builds from
  `services/api`. The versioned per-service configs and the human-approved
  staging/production contract live in [infra/railway/README.md](infra/railway/README.md).
- **Vercel** — one project using [Vercel Services](https://vercel.com/docs/services):
  the `web` (Next.js) and `api` (FastAPI) services build from the same repo and
  share one origin — the web app at `/`, the API under `/api`. The repo-root
  `vercel.json` declares both services and routes `/api/*` to the API service;
  the Vercel-only `services/api/index.py` strips the `/api` prefix so FastAPI
  keeps its native paths (`/health`, `/files`, …). Uploads go directly from the
  browser to B2 via a presigned PUT (see
  [File Upload](docs/features/file-upload.md)), so they bypass the Function's
  4.5 MB payload ceiling entirely — the bucket must allow the deploy origin in
  its CORS. A two-separate-Projects alternative and the full delivery contract
  live in [infra/vercel/README.md](infra/vercel/README.md).

External provisioning and deployment remain explicit user-approved actions.

## IfcOpenShell pipeline & subprocess isolation

The `run` path (`service/archive_runner.py`) downloads each source IFC from B2,
then runs the heavy parse + geometry + analyze pass in an **isolated subprocess**
(`service/ifc_worker.py` → `python -m app.repo.ifc_child`) with a hard timeout.
The child writes metadata JSON, per-element OBJ meshes, and axis-aligned bounding
boxes; the runner uploads them (metadata JSON, geometry OBJ zip), aggregates
quantity take-off and cross-model clash candidates, computes write amplification
from B2 object sizes, and persists the manifest. Worker failures are typed
(`IfcParseError` / `IfcTimeout` / `IfcCrashed`, the last covering a native
segfault) so a crashing geometry pass surfaces as a failed run instead of wedging
the API. IfcOpenShell is CPU-only — there is no GPU path.

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API), the sole data store
  - Source IFC models and every derived artifact stored under a per-project
    prefix (`projects/<slug>/...`)
  - The canonical per-project index is `projects/<slug>/manifest.json` — **no
    application database**; the manifest IS the record. The model list and
    write-amplification are re-derived live from B2 object sizes on read.
  - Listing and metadata via S3 `list_objects_v2` / `head_object`

## External Services

- **Backblaze B2 S3 API** — file storage, retrieval, deletion, presigned URLs

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend -> API** — CORS-restricted to configured origins. `CORSMiddleware` is registered LAST in `main.py` (outermost) so it wraps **every** response, including uncaught-exception 500s — otherwise the browser would block error responses and the UI would only see an opaque "network error". See [docs/RELIABILITY.md](docs/RELIABILITY.md#error-handling). A per-IP rate-limit middleware sits inner to CORS; see [docs/SECURITY.md](docs/SECURITY.md#rate-limiting).
- **API -> B2** — authenticated via application keys, signature v4
- **Client -> B2** — presigned URLs for download (10-min expiry, forced attachment)

## Data Flows

- **Create project**: Browser -> `POST /projects` -> service writes `manifest.json` under a new slug prefix
- **Ingest**: `POST /projects/{slug}/ingest-samples` (server authors synthetic IFC and puts them under the prefix) OR `POST /projects/{slug}/ingest/presign` -> browser PUTs an IFC **directly to B2** under `projects/{slug}/models/<discipline>/`
- **Run pipeline**: Browser -> `POST /projects/{slug}/run` -> runner downloads each model from B2 -> isolated IfcOpenShell subprocess (parse + mesh + AABB) -> uploads metadata/geometry/analysis -> updates manifest (status, BIM stats, write amplification)
- **Artifacts**: `GET /projects/{slug}/artifacts` lists project-scoped objects; `GET /projects/{slug}/artifacts/download?key=` presigns one for downstream serving
- **Upload**: Browser -> `POST /upload/presign` -> Browser PUTs bytes **directly to B2** -> `POST /upload/verify`
- **List / Download / Delete** (full-bucket): `GET /files`, `GET /files/{key}/download`, `DELETE /files/{key}`

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware (logs duration per request; also the catch-all that converts uncaught exceptions to a typed JSON 500)
- `/metrics` endpoint (Prometheus format: request count, latency, upload count)
- `/health` endpoint (B2 connectivity check)

## API Contract

- Checked-in OpenAPI artifact: `docs/api/openapi.json`
- Export/check command: `pnpm contract:export` / `pnpm contract:check`
- FastAPI freshness test: `services/api/tests/test_openapi_contract.py`
- Frontend route drift test: `apps/web/src/lib/api-contract.test.ts`

The frontend client keeps a small `API_CLIENT_ROUTES` registry in
`apps/web/src/lib/api-client.ts`. Tests compare that registry to the checked-in
OpenAPI artifact so route changes fail loudly before the hand-written client can
silently drift from FastAPI. `GET /metrics` is intentionally server-only.

## Canonical Files

- Projects router: `services/api/app/runtime/projects.py`
- Project store: `services/api/app/service/projects.py`
- Pipeline run: `services/api/app/service/archive_runner.py`
- Subprocess worker: `services/api/app/service/ifc_worker.py`
- IfcOpenShell engine: `services/api/app/repo/ifc_engine.py` (+ `repo/ifc_child.py`)
- Manifest / artifact I/O: `services/api/app/repo/manifest.py`, `repo/artifacts.py`
- B2 data access (repo layer): `services/api/app/repo/b2_client.py`
- Pydantic models: `services/api/app/types/` (`projects.py`, `files.py`, `upload.py`, `stats.py`, `formatting.py`)
- Config (pydantic-settings): `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`; engine tests: `tests/test_ifc_engine.py`
- OpenAPI contract: `docs/api/openapi.json`; exporter: `services/api/scripts/export_openapi.py`
- Frontend API client: `apps/web/src/lib/api-client.ts`; project UI: `apps/web/src/components/projects/`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [Projects](docs/features/projects.md)
- [IFC pipeline](docs/features/ifc-pipeline.md)
- [Write amplification](docs/features/write-amplification.md)
- [Clash & quantities](docs/features/clash-quantities.md)
- [Metadata Extraction](docs/features/metadata-extraction.md)
- [File Upload](docs/features/file-upload.md)
- [File Browser](docs/features/file-browser.md)
- [Dashboard](docs/features/dashboard.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
