# Build plan — `ifcopenshell-bim-archive`

Source of truth (starter kit): `.claude/scratch/vcsk-6f3787de-7990-4b34-b1b4-fcb50774a57b/`
Target: `./ifcopenshell-bim-archive`
Trending OSS: **IfcOpenShell** — https://github.com/IfcOpenShell/IfcOpenShell

## 1. Purpose

A full-stack **BIM digital-twin archive** for architecture/engineering/construction (AEC)
teams. A user creates a **Project** (one building/coordination effort), ingests
discipline-specific **IFC** building-information models, then runs **IfcOpenShell**
locally to (1) **parse** the entity tree and serialize structured metadata JSON,
(2) **extract geometry** to OBJ meshes bundled as a zip, and (3) **analyze** the model
(quantity take-off + bounding-box clash candidates). Every source model and every
derived artifact is archived on **Backblaze B2** over the S3-compatible API, indexed by a
per-project `manifest.json`. The headline is **write amplification**: a handful of IFC
models fan out into geometry bundles, metadata JSON, and analysis reports whose total
footprint meets or exceeds the source bytes — and B2 is the single storage layer that
holds all of it and serves it back to viewers/coordination tools via presigned URLs.

Audience: AEC data engineers, BIM managers, and AI/dev teams evaluating B2 as the
long-term store for large model archives with heavy derived-artifact fan-out. Runs on
local OSS only — IfcOpenShell is keyless; the **only** secret is B2 credentials.

This is architecturally the same shape as the shipped `colmap-photogrammetry-archive`
sample (ingest → local keyless engine → derived-artifact fan-out → B2 archive → project
lifecycle + write-amplification), remapped from photogrammetry to BIM. The builder builds
this from the **vibe-coding-starter-kit** source only; colmap is named here purely as the
proven reference shape, not a tree to copy.

## 2. Architecture delta from vibe-coding-starter-kit

The starter kit is the ceiling. It already ships: a B2-backed FastAPI service (S3 client,
listing cache, upload/presign, metadata extraction, health, rate limit, metrics), a
Next.js 16 / React 19 / Tailwind v4 / shadcn UI with a **full-bucket File Explorer**,
drag-and-drop **Upload**, a **Dashboard** (stats + recent uploads + upload chart), a
**Settings** showcase, and a `/design` system page. Keep that spine; layer a Project +
BIM-pipeline domain on top.

### KEEP (as-is or light rename only)
- Entire `services/api/app/repo/` S3 spine: `b2_client.py`, `b2_object.py`, `b2_upload.py`,
  `list_cache.py`, `counter.py` (rename user-agent only — see §6).
- `services/api/app/runtime/`: `health.py`, `files.py`, `upload.py`, `metrics.py`,
  `ratelimit.py`. `main.py` (rename API title + import the new `projects` router).
- `services/api/app/service/`: `files.py`, `upload.py` (kept; Upload doubles as project Ingest).
- `services/api/app/types/`: `files.py`, `errors.py`, `formatting.py`, `stats.py`, `upload.py`.
- Whole test harness style + `tests/` scaffolding (adapt/extend, don't delete the structural tests).
- **Full-bucket File Explorer** (`apps/web/src/app/files/`, `components/files/*`) — **NEVER
  removed** (non-negotiable keep). It browses the entire bucket; the new project-scoped asset
  explorer is additive, not a replacement.
- Upload page + dropzone/queue, Dashboard, Settings (showcase), `/design`, layout (sidebar/
  header/theme), all `components/ui/*`, all `lib/*` utilities, `scripts/*`, `infra/*`, CI.

### TRIM (remove from starter)
- Nothing structural. The starter's metadata extraction is **image/PDF-oriented**; keep the
  module but **extend** it with IFC-header extraction (see §4) rather than deleting. Image/PDF
  paths stay (a BIM archive may still hold reference PDFs/renders in the bucket).
- `docs/features/*` that don't apply get rewritten or replaced (see §5), not left stale.

### ADD (new for ifcopenshell-bim-archive)
Backend (`services/api/app/`):
- `repo/ifc_engine.py` — thin wrapper over IfcOpenShell: open a model, parse the entity tree
  (spaces/elements/property sets/relationships) to a JSON-serializable dict, iterate geometry
  to per-element OBJ meshes, and compute quantity take-off + AABB clash candidates. Keeps all
  `ifcopenshell` imports contained here.
- `service/ifc_worker.py` — runs the heavy IfcOpenShell parse+geometry+analyze in an
  **isolated subprocess** with a hard timeout (mirror colmap's worker isolation), so a heavy
  or crashing native geometry pass can't wedge the API. Raises typed
  `IfcParseError` / `IfcTimeout` / `IfcCrashed`.
- `service/projects.py` — B2-backed project store: create/list/get/update/delete, slug
  generation, and the canonical per-project `manifest.json` reader/writer (no database).
- `service/archive_runner.py` — the `run` path: download the project's source IFC models from
  B2, invoke the isolated worker, write metadata JSON / geometry zip / analysis CSV+clash JSON
  back under the project prefix, compute write amplification, persist the final manifest.
  (Split from `projects.py` to stay under the repo's ~300-line module ceiling.)
- `repo/manifest.py` + `repo/artifacts.py` — manifest object I/O and artifact-listing helpers
  scoped to a project prefix.
- `runtime/projects.py` — the router (routes in §4).
- `types/projects.py` — Pydantic models: `Project`, `ProjectCreate`, `ProjectUpdate`,
  `ProjectStatus` (StrEnum: draft/queued/running/succeeded/failed), `Discipline` (StrEnum),
  `GeometryDetail` (StrEnum: coarse/standard/fine), `PipelineStage`, `BimStats`,
  `WriteAmplification`, `ArtifactEntry`, `ProjectStats`, `ServerCapabilities`.
- Seed data: a **tiny, license-clean, synthetic** IFC model under
  `services/api/seed/` (IFC is ASCII STEP text, not a binary asset). Prefer generating it with
  a small `scripts/make_seed_ifc.py` that authors a handful of `IfcWall`/`IfcSlab`/`IfcSpace`
  entities via IfcOpenShell (fully synthetic → no third-party data license), or check in a
  minimal hand-authored `.ifc` (a few KB). This lets a demo `run` complete end-to-end. Add a
  README note to "bring your own IFC via Upload" too.

Frontend (`apps/web/src/`):
- `app/projects/page.tsx` (library) + `app/projects/[slug]/page.tsx` (detail).
- `components/projects/`: `projects-library.tsx`, `project-card.tsx`, `project-form.tsx`
  (create+edit), `project-detail.tsx`, `project-status.tsx`, `pipeline-timeline.tsx`
  (Parse → Extract Geometry → Analyze), `bim-stats.tsx` (element/space/discipline counts +
  quantity take-off + clash-candidate count), `write-amplification-panel.tsx`,
  `asset-explorer.tsx` (**project-scoped** explorer — the mandated sample-specific asset
  explorer, scoped to `projects/<slug>/`), `downstream-snippet.tsx` (copyable presigned-serving
  snippet for viewers/coordination tools).
- `lib/queries.ts` — add project query/mutation hooks (create/list/get/update/delete/run).
- Sidebar: add a **Projects** nav entry (primary), keep **Files** (full-bucket explorer),
  **Upload**, **Dashboard**, **Settings**.
- Dashboard: extend `stats-cards`/chart to surface archive-wide **write amplification**
  (source vs artifact bytes) and project/model counts alongside existing upload stats.

**Note on the bucket-explorer tension:** none. The full-bucket File Explorer stays as the
"browse everything" view; the project-scoped asset explorer is the additive per-project view.
Both coexist (same as colmap).

## 3. B2 surface (S3-compatible only — no b2-native)

All via the existing boto3 S3 client in `repo/b2_client.py` (custom user agent, standard env
vars). Operations exercised:
- `put_object` — archive source IFC (via presigned PUT from the browser on Upload) and write
  all derived artifacts + `manifest.json` (server-side).
- `list_objects_v2` (paginated, cached) — full-bucket explorer, dashboard stats, per-project
  artifact/asset listing.
- `head_object` — file/artifact metadata + existence checks.
- `get_object` — download source IFC into the worker for processing; artifact downloads.
- `delete_object` — delete artifacts / delete a project's objects.
- `generate_presigned_url` (GET) — serve/download models + geometry to viewers (downstream
  snippet) and the UI; presigned PUT for direct browser upload.
- `head_bucket` — health check.

**No b2-native API anywhere.** Flag: none.

B2 key layout (per-project prefix so the manifest, scoped explorer, and write-amplification
are clean — this reconciles the brief's flat `metadata/`,`geometry/`,`analysis/` folders into
a project-scoped tree):
```
projects/<slug>/models/<discipline>/<file>.ifc     # source IFC (ingest)
projects/<slug>/metadata/<model>.json              # parsed entity-tree metadata
projects/<slug>/geometry/<model>.obj.zip           # OBJ mesh bundle
projects/<slug>/analysis/quantities.csv            # quantity take-off
projects/<slug>/analysis/clash-report.json         # bbox clash candidates
projects/<slug>/manifest.json                      # canonical per-project index (no DB)
```

## 4. Key features (seed README + docs/features/*.md)

Per-feature `deployment` is an explicit field (builder/reviewer gate on it).

1. **Projects library & lifecycle** — create/browse/edit/delete building projects; each is a
   B2 prefix indexed by `manifest.json`. `deployment: local` (no external provider).
2. **IFC parse → metadata JSON** — IfcOpenShell reads each model, extracts spaces, elements,
   property sets, and relationships into structured JSON archived under `metadata/`.
   `deployment: local`.
3. **Geometry extraction → OBJ bundle** — IfcOpenShell iterates element geometry to OBJ
   meshes, zipped under `geometry/`. (OBJ is the honest, pure-Python-serializable default;
   note GLTF as a possible extension rather than claiming it.) `deployment: local`.
4. **Analyze — quantity take-off + clash candidates** — element/quantity counts by IfcType and
   discipline → `quantities.csv`; axis-aligned bounding-box overlap between elements → clash
   candidates → `clash-report.json`. Degrades gracefully to intra-model overlaps when a project
   has a single model. `deployment: local`.
5. **Write-amplification archive on B2** — per-project and archive-wide source-vs-artifact
   bytes and ratio; B2 as the sole store; presigned serving to downstream viewers.
   `deployment: local`.
6. **Kept-from-starter** — full-bucket File Explorer + drag-and-drop Upload (Upload = project
   Ingest step). `deployment: local`.

**External API provider:** NONE. IfcOpenShell is a local, keyless, CPU-only native Python
wheel (like `pycolmap` in colmap). No second API key; B2 credentials only. Per
`api-provider-selection.md`, this whole sample is `deployment: local` and inherits the
CPU-default / GPU-autodetect rule — but IfcOpenShell has **no** GPU path, so it is
unconditionally CPU. Estimated cost of one full demo run: **$0** (local compute + B2 storage
of a few MB of seed artifacts). No Genblaze (the brief does not mention it).

### Primary-entity lifecycle (mandatory UI completeness)
Primary entity: **Project**. All five verbs are user-accessible and MUST be built in the UI:
- **create** — `POST /projects` → `project-form.tsx` (create mode) on the Projects library.
- **read** — `GET /projects` (library) + `GET /projects/{slug}` (detail) → library + detail.
- **edit** — `PATCH /projects/{slug}` → `project-form.tsx` (edit mode, pre-filled).
- **delete** — `DELETE /projects/{slug}` (deletes the project's B2 objects, prefix-scoped) →
  confirm dialog (`alert-dialog`) on card/detail.
- **run** — `POST /projects/{slug}/run` → "Run pipeline" button on detail; executes
  Parse → Extract Geometry → Analyze and archives artifacts.

`omitted_ui_verbs`: **none** — every verb is built. (Phase 5 records an empty list.)

Support routes (not lifecycle verbs): `GET /projects/stats`, `GET /projects/capabilities`
(reports `engine`, ifcopenshell version, `device: cpu`), `GET /projects/{slug}/artifacts`
(+`/download`).

### Form UX conventions (create/edit `project-form.tsx`)
Follow the starter's `components/settings/settings-form.tsx` exemplar (react-hook-form + zod +
shadcn `Select`/`FormDescription`).
- **Finite-value fields → selectors (never free text), on BOTH create and edit:**
  - `discipline` → `Select`: `architectural`, `structural`, `mechanical`, `electrical`,
    `plumbing`, `civil`, `coordination` (multi-discipline). This is the project's primary
    discipline label; per-model discipline is chosen at Upload/Ingest time via the same enum.
  - `geometry_detail` → `Select`: `coarse` / `standard` / `fine` (maps to IfcOpenShell geometry
    settings — deflection/precision).
- **Free-text field:** `name` (required, 1–120 chars).
- **CREATE-only safe defaults, surfaced as placeholder / `FormDescription` (guidance only — no
  autofill button):** name placeholder e.g. `Riverside Community Hospital`; `discipline`
  defaults to `coordination` ("all disciplines"); `geometry_detail` defaults to `standard`
  ("balanced mesh detail — good for a first run"). Edit mode opens pre-filled from the real
  project (no default hints).

## 5. Doc transforms
- **Rewrite** `docs/features/metadata-extraction.md` → cover IFC-header + entity-tree parsing
  (keep the image/PDF note as a secondary paragraph).
- **Rewrite** `docs/features/file-browser.md` and `file-upload.md` → keep, add BIM framing
  (Upload = Ingest; File Explorer = full-bucket vs project-scoped asset explorer).
- **Rewrite** `docs/features/dashboard.md` → add write-amplification + project/model counts.
- **New stubs** (from `_template.md`): `projects.md`, `ifc-pipeline.md` (Parse → Geometry →
  Analyze), `write-amplification.md`, `clash-quantities.md`.
- **README.md** — full rewrite around the BIM archive story (headline: write amplification),
  "What it looks like" with the standard image placeholders (screenshots come in a LATER
  pipeline step — reference `docs/images/*.png` paths, do not create images), Quick Start
  (Node ≥20, pnpm ≥9, Python ≥3.12, free B2 account; no GPU; IfcOpenShell keyless), standard
  B2 UTM links, `<!-- labs-project-page -->` placeholder line, and a FAQ / When-to-use /
  When-not-to-use section (AEO). Keep ARCHITECTURE.md/AGENTS.md/PRODUCT.md updated to the new
  domain.
- Keep `docs/RELIABILITY.md`, `docs/SECURITY.md`, `docs/design-system.md`, `dev-workflows.md`
  (rename identifiers only).

## 6. Rename table
| From (vibe-coding-starter-kit) | To (ifcopenshell-bim-archive) |
|---|---|
| kebab repo / dir `vibe-coding-starter-kit` | `ifcopenshell-bim-archive` |
| root `package.json` name `vibe-coding-starter-kit` | `ifcopenshell-bim-archive` |
| npm scope `@vibe-coding-starter-kit/web` | `@ifcopenshell-bim-archive/web` |
| Title Case "Vibe Coding Starter Kit" | "IfcOpenShell BIM Archive" |
| `APP_NAME` in `apps/web/src/lib/app-config.ts` | `IfcOpenShell BIM Archive` |
| `APP_DESCRIPTION` | `BIM digital-twin archive powered by Backblaze B2 + IfcOpenShell` |
| API title in `services/api/main.py` | `IfcOpenShell BIM Archive API` |
| `user_agent_extra="b2ai-oss-start"` (b2_client.py) | `b2ai-ifcopenshell-bim-archive` |
| UTM `utm_content` tag | `b2ai-ifcopenshell-bim-archive` |
| Railway/Vercel image tags / workflow slugs referencing the starter name | `ifcopenshell-bim-archive` |
| any `vibe-coding` / `vcsk` string in docs/tests/infra | BIM-archive equivalents |

Also apply the **env-var standardization** (parent CLAUDE.md standard #3, matching every
recent sample): rename `B2_KEY_ID`→`B2_APPLICATION_KEY_ID`, keep `B2_APPLICATION_KEY` /
`B2_BUCKET_NAME`, add `B2_REGION` (derive the S3 endpoint as
`https://s3.<region>.backblazeb2.com` via a settings property; keep an optional `B2_ENDPOINT`
advanced override empty by default), and `B2_PUBLIC_URL`→`B2_PUBLIC_URL_BASE`. Update
`settings.py`, `main.py` startup validation, `.env.example`, `scripts/setup_b2_cors.py`, tests,
and README accordingly. (The starter's `B2_KEY_ID`/no-`B2_REGION` shape is a known deviation;
new samples MUST ship the standard names.)

## 7. Dependencies
- Add `ifcopenshell` to `services/api/requirements.txt` **and** `requirements.lock`, pinned to
  a recent version that publishes **macOS arm64 + cp312 wheels** (native prebuilt wheel — no
  build-from-source, same story as `pycolmap`). Also add `numpy` if not already present
  (geometry arrays). Keep everything else the starter ships. The dependency-lock structural
  test must pass.
- Python ≥3.12 (starter's `.python-version`). CPU-only; no CUDA/MPS.

## 8. Standards checklist (parent CLAUDE.md — reviewer gates on these)
1. S3-compatible API is the default (no b2-native). ✅ by design.
2. Custom user agent `b2ai-ifcopenshell-bim-archive` on the S3 client. ✅
3. Standard `B2_*` env var names (`B2_APPLICATION_KEY_ID`, `B2_APPLICATION_KEY`,
   `B2_BUCKET_NAME`, `B2_REGION`, `B2_PUBLIC_URL_BASE`). ✅
- No hardcoded secrets/account IDs/bucket names/internal URLs; credentials only via `.env`
  (gitignored); `.env.example` uses placeholders.
- Reproducible from a fresh clone; README updated to actual behavior; repo AI-agent-readable.
