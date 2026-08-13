<!-- last_verified: 2026-08-06 -->
# App Workflows

User journeys inside the application.

## Projects & the IfcOpenShell pipeline

- User navigates to `/projects` and clicks **New project**
- The create form uses **selectors** (not free text) for the finite fields:
  **discipline** (architectural…coordination, default *coordination*) and
  **geometry detail** (coarse/standard/fine, default *standard*). The only free
  text is the **name**. Create-mode surfaces safe-default guidance as
  `FormDescription` hints; edit-mode opens pre-filled with no default hints
- On create the browser navigates to `/projects/<slug>` (the detail page)
- **Ingest** a model two ways: click **Load samples** (the API authors two tiny,
  license-clean synthetic IFC models server-side and archives them under
  `projects/<slug>/models/`), or pick a discipline and choose your own `.ifc`
  (uploaded **directly to B2** via a project-scoped presigned PUT)
- Click **Run pipeline**. The request blocks until the run finishes, then the
  pipeline timeline (Parse → Extract Geometry → Analyze), model insight (element/
  space/mesh/clash counts + quantity take-off), and the write-amplification panel
  fill in. A run with no models is refused with a clear message
- **Edit** (name/discipline/geometry detail) via a pre-filled dialog; **Delete**
  asks for confirmation and removes every object under the project's B2 prefix
- The **project-scoped asset explorer** lists source models and all derived
  artifacts under `projects/<slug>/`; each row downloads via a presigned URL. A
  copyable snippet shows how a downstream viewer pulls those presigned URLs
- See: [Projects](features/projects.md), [IFC pipeline](features/ifc-pipeline.md)

## Upload Files

- User navigates to `/upload`
- Drops or selects files in the dropzone
- Client validates file size (max 100MB) and type
- Files upload **directly from the browser to B2** (a presigned PUT). A determinate progress bar tracks the bytes leaving the browser; once they are all sent the row switches to "Verifying upload..." with an *indeterminate* sweeping bar while the API HEADs and magic-byte-sniffs the stored object. That phase has no percentage to report, and a bar parked at a full 100% read as finished-but-stuck
- On success: toast notification, green checkmark, and a "View in Files" link through to the browser
- On failure: red status icon with error message
- User can clear completed uploads
- The queue lives in an app-wide provider: navigating to another page keeps the upload running, shows an "Uploading N files" indicator in the header, and keeps the duplicate-upload guard armed
- Reloading or closing mid-upload asks for confirmation first; if the upload dies anyway, the next load says which file didn't finish
- See: [File Upload](features/file-upload.md)

## Browse and Manage Files

- User navigates to `/files`
- Page loads the 100 most recent objects from the API (sorted most recent first). While it loads, the page says so on screen and escalates the wording if the wait runs long — a full bucket listing measured 2.8s-21s cold
- If that limit was hit, a notice states how many objects the bucket actually holds — the page never claims to show everything
- Files displayed in tree view with folders and type-specific icons
- Folders auto-expand on load until the *majority* of the listed files are reachable without clicking, so the page's own "click a file" instruction is always actionable. Stopping at the first visible file was not enough: one stray top-level object left the other 99 sealed in collapsed folders while the page claimed to show 100
- Clicking a file row opens its preview; the per-row actions menu (preview / download / delete) is always visible, on every viewport
- Arriving at `/files?preview=<key>` expands that file's folders and opens its preview directly. This is how the ⌘K palette and the dashboard's recent-uploads rows hand off a *specific* file; the param is consumed on arrival so it doesn't re-fire later
- **Preview**: opens dialog with image/PDF preview + metadata panel, and the file's Download / Delete actions — the advertised "click a file" path offers everything the row menu does. The loading state holds until the media paints; a failure offers "Open in a new tab". The preview URL is signed with `Content-Disposition: inline` so PDFs render in place
- **Download**: shows a pending state on the row plus a toast while the presigned URL is fetched, then starts the download via an anchor click (which, unlike a popup, still works if the click's user activation expired during a slow presign). Failures are reported; the click can never silently do nothing
- **Delete**: the confirmation dialog stays open showing "Deleting..." until the request settles, then the row disappears with the toast (optimistic cache update) and the list reconciles with the server. The dialog is held deliberately — Radix closes on action click by default, which dismissed the only pending state and left the row looking untouched while the delete was still in flight
- Empty bucket shows "No files found" with upload prompt
- See: [File Browser](features/file-browser.md)

## View Dashboard

- User navigates to `/` (home)
- The archive rollup loads first: project count, source models, derived artifacts, and archive-wide **write amplification** (derived bytes vs. source bytes), all measured live from the B2 `projects/` tree
- Then stats, recent files, and upload activity load — all served from one shared bucket listing that the API warms at startup
- While stats load, the page states it in words above the cards rather than showing silent skeletons
- Stats cards show: total files, storage used, uploads today, total downloads
- Upload chart shows last 7 days of upload activity as bar chart
- Recent uploads table shows last 10 files with filename, size, type, date. Each filename links to that file's preview on `/files` — `/files` teaches "click a file to preview it", so the same gesture here has to answer rather than being inert text
- Empty state: "No files uploaded yet" messages
- See: [Dashboard](features/dashboard.md)

## Change Preferences

- User navigates to `/settings`
- A banner at the top states that the page is mostly a demonstration: only Theme is wired up for real, the rest showcases what a settings page can look like when you adapt the kit
- **Theme** (real): editing it and saving applies it immediately and persists it (`next-themes`), and the header's theme toggle drives the same state
- **Profile and preference fields** (demo): Display name, Bio, Default file view (Tree/List/Grid), Email me on every upload, Warn me when approaching quota + threshold. Each is labelled "Demo field", persists to `localStorage` only, and drives no behaviour — there is no account system, mailer, quota banner, activity log, or List/Grid view behind them yet
- Saving reports honestly: a success toast that separates the real theme change from the locally-stored demo values, or a warning toast if the browser blocked storage (theme still changes). It never claims a save that did not happen — the original page toasted "Settings saved" for fields that changed nothing
- Danger Zone actions are a demo — no real delete runs
- See: [Settings](features/settings.md)
