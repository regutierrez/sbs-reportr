# SBS Reportr Plan

## Goal
Build a Vue + FastAPI reporting app that captures project intake details and photos, then generates a template-faithful Activity Report PDF with the same visual language used in `sbs-reboundr`.

## Locked Decisions
- Intake UX is a single scrollable form (not a stepper).
- Generate action is blocked until all required inputs are valid and all required photo groups are present.
- Confirmation page is required before generation, with:
  - `Revert` => return to editable form with values preserved
  - `Continue` => generate/download PDF
- Required fields:
  - `Prepared by` (string)
  - `Role` (string)
- PDF cover page containing:
  - Building Name
  - Testing Date (`MONTH YYYY`)
  - Building Photo
- Keep the rest of the Activity Report narrative text fixed; only annotated values/photos are replaced.
- Frontend scaffolding starts with `bun create vue@latest`.
- No placeholder PDF phase; implement the full template renderer directly.
- Image compression is mandatory.
- Form and photo models use **section + subsection** namespaces (for example: `superstructure.rebar_scanning`, `substructure.rebar_scanning`).

## Reference Assets
- Expected canonical template file path:
  - `docs/reference/Testing Report Template_v0.pdf`
- Optional source companion:
  - `docs/reference/activity-report-template.docx`
- Keep extraction notes/versioning in:
  - `docs/reference/template-notes.md`
- Narrative text blocks are extracted verbatim from the template PDF and hardcoded into the renderer. The template PDF is the single source of truth for all fixed copy.

## PDF Template Details Extracted From Template

### Headings and Subheadings
- `A. INTRODUCTION`
- `B. DATA GATHERING FOR SUPERSTRUCTURE`
- `B.1. Rebar Scanning`
- `B.2. Rebound Hammer Test`
- `B.3. Concrete Core Extraction`
- `B.4. Rebar Extraction`
- `B.5. Chipping of Existing Slab`
- `B.6. Restoration Works`
- `C. DATA GATHERING FOR SUBSTRUCTURE`
- `C.1. Concrete Core Extraction`
- `C.2. Rebar Scanning`
- `C.3. Restoration for Coring Works, Backfilling, and Compaction`
- `Prepared by:`

### Default Texts (Non-changing)
- Preserve all report narrative text blocks exactly as template copy.
- Preserve section ordering and caption numbering scheme (`Figure B.1`, `Figure B.3.1`, etc.).
- Preserve page-level structure and branded header/footer treatment.
- Replace only annotated variables and annotated image blocks.

### Mapping of Form Values to Resulting PDF

#### Text/number mapping
- `building_details.testing_date` => cover page `MONTH YYYY` display
- `building_details.building_name` => cover page title + introduction mentions
- `building_details.building_location` => introduction location mention
- `building_details.number_of_storey` => introduction building descriptor
- `superstructure.rebar_scanning.number_of_rebar_scan_locations` => section `B.1` count
- `superstructure.rebound_hammer_test.number_of_rebound_hammer_test_locations` => section `B.2` count
- `superstructure.concrete_core_extraction.number_of_coring_locations` => section `B.3` count
- `superstructure.rebar_extraction.number_of_rebar_samples_extracted` => section `B.4` count
- `superstructure.restoration_works.non_shrink_grout_product_used` => section `B.6` product mention
- `superstructure.restoration_works.epoxy_ab_used` => section `B.6` adhesive/epoxy mention
- `substructure.concrete_core_extraction.number_of_foundation_locations` => section `C.1` location count
- `substructure.concrete_core_extraction.number_of_foundation_cores_extracted` => section `C.1` core count
- `signature.prepared_by` => final page signature name
- `signature.prepared_by_role` => final page signature role

#### Photo mapping
- `building_details.building_photo` => cover page hero + intro page building image
- `superstructure.rebar_scanning.photos` => `Figure B.1`
- `superstructure.rebound_hammer_test.photos` => `Figure B.2`
- `superstructure.concrete_core_extraction.concrete_coring_photos` => `Figure B.3.1`
- `superstructure.concrete_core_extraction.core_samples_family_pic` => `Figure B.3.2`
- `superstructure.rebar_extraction.rebar_extraction_photos` => `Figure B.4.1`
- `superstructure.rebar_extraction.rebar_samples_family_pic` => `Figure B.4.2`
- `superstructure.chipping_existing_slab.photos` => `Figure B.5`
- `superstructure.restoration_works.photos` => `Figure B.6`
- `substructure.concrete_core_extraction.coring_for_foundation_photos` => `Figure C.1`
- `substructure.rebar_scanning.photos` => `Figure C.2`
- `substructure.restoration_backfilling_compaction.photos` => `Figure C.3`

## Form Schema (Required)

### Inputs (section + subsection)
- `building_details.testing_date` (month picker)
- `building_details.building_name` (max 200 chars)
- `building_details.building_location` (max 500 chars)
- `building_details.number_of_storey` (int, min 1)
- `superstructure.rebar_scanning.number_of_rebar_scan_locations` (int, min 1)
- `superstructure.rebound_hammer_test.number_of_rebound_hammer_test_locations` (int, min 1)
- `superstructure.concrete_core_extraction.number_of_coring_locations` (int, min 1)
- `superstructure.rebar_extraction.number_of_rebar_samples_extracted` (int, min 1)
- `superstructure.restoration_works.non_shrink_grout_product_used` (max 200 chars)
- `superstructure.restoration_works.epoxy_ab_used` (max 200 chars)
- `substructure.concrete_core_extraction.number_of_foundation_locations` (int, min 1)
- `substructure.concrete_core_extraction.number_of_foundation_cores_extracted` (int, min 1)
- `signature.prepared_by` (max 100 chars)
- `signature.prepared_by_role` (max 100 chars)

### Photos and limits (all required, min 1; section + subsection)
- `building_details.building_photo` (min 1, max 1)
- `superstructure.rebar_scanning.photos` (min 1, max 5)
- `superstructure.rebound_hammer_test.photos` (min 1, max 5)
- `superstructure.concrete_core_extraction.concrete_coring_photos` (min 1, max 5)
- `superstructure.concrete_core_extraction.core_samples_family_pic` (min 1, max 2)
- `superstructure.rebar_extraction.rebar_extraction_photos` (min 1, max 5)
- `superstructure.rebar_extraction.rebar_samples_family_pic` (min 1, max 2)
- `superstructure.chipping_existing_slab.photos` (min 1, max 2)
- `superstructure.restoration_works.photos` (min 1, max 5)
- `substructure.concrete_core_extraction.coring_for_foundation_photos` (min 1, max 3)
- `substructure.rebar_scanning.photos` (min 1, max 3)
- `substructure.restoration_backfilling_compaction.photos` (min 1, max 5)

## Data Models

### Backend (Pydantic)
- `ReportSession` — session metadata: `id` (UUID4), `created_at` (datetime), `status` (enum: `draft`, `generating`, `completed`), `form_fields` (optional `ReportFormFields`).
- `ReportFormFields` — nested section/subsection object used as the request body for `PUT /reports/{session_id}` and stored as session state:
  - `building_details`
  - `superstructure.rebar_scanning`
  - `superstructure.rebound_hammer_test`
  - `superstructure.concrete_core_extraction`
  - `superstructure.rebar_extraction`
  - `superstructure.restoration_works`
  - `substructure.concrete_core_extraction`
  - `signature`
- `PhotoGroupName` — enum-style identifier for upload groups, namespaced by section/subsection (e.g. `superstructure_rebar_scanning_photos`, `substructure_rebar_scanning_for_foundation_photos`).
- `ImageMeta` — per-image metadata: `id` (UUID4), `group_name` (`PhotoGroupName`), `original_filename` (str), `stored_filename` (str, e.g. `{uuid}.jpg`), `size_bytes` (int), `width` (int), `height` (int).
- `ImageUploadResponse` — returned by the image upload endpoint: `image` (ImageMeta).
- `SessionStatusResponse` — returned by `POST /reports`: `session_id` (UUID4), `status` (str).
- `GenerateReportResponse` — returned by the generate endpoint: `session_id` (UUID4), `download_url` (str).

### Frontend (TypeScript)
- `ReportSession` — mirrors backend `ReportSession`.
- `ReportFormFields` — mirrors backend nested section/subsection `ReportFormFields`. Used as form state and request body.
- `PhotoGroupName` — mirrors backend photo-group identifier set.
- `ImageMeta` — mirrors backend `ImageMeta`. Used to track uploaded images per group.
- `ImageUploadResult` — mirrors backend `ImageUploadResponse`.
- `PhotoGroup` — UI helper: `name` (string), `label` (string), `min` (number), `max` (number), `images` (ImageMeta[]).

## Architecture
- Frontend: Vue 3 + Vite + TypeScript + Tailwind CSS.
- Backend: FastAPI + Pydantic + WeasyPrint.
- Screen flow: `IntakeFormScreen -> ConfirmationScreen -> Generate PDF`.
- API:
  - `POST /reports` — create an empty report session, returns `session_id` (UUID4).
  - `PUT /reports/{session_id}` — submit or update text form fields for the session.
  - `POST /reports/{session_id}/images/{group_name}` — upload a single image to a photo group (e.g. `superstructure_rebar_scanning_photos`); streamed to disk. For groups requiring multiple images, the frontend fires parallel requests and tracks per-image upload progress.
  - `POST /reports/{session_id}/generate` — validate completeness, render PDF, persist output, return download.
- Identifiers:
  - Session IDs: UUID4. Not guessable, collision-safe.
  - Image filenames on disk: UUID4 with original extension preserved (e.g. `a1b2c3d4.jpg`). Avoids collisions when multiple uploads share the same original filename.
  - PDF output path: `data/reports/{session_id}/report.pdf` — inherits uniqueness from the session UUID.

## Frontend Implementation Plan
- Scaffold with `bun create vue@latest src/frontend`.
- Build reusable components aligned with reboundr style:
  - `SectionHeader.vue`
  - `ImageUploadField.vue`
  - `IntakeFormScreen.vue`
  - `ConfirmationScreen.vue`
- Enforce full validation before enabling generate action.
- Keep service layer in `src/frontend/src/api.ts` using `fetch`.

## Backend Implementation Plan
- Create `src/reportr/app/web_api.py` with session-based endpoints:
  - `POST /reports` — create empty session, returns `session_id`.
  - `PUT /reports/{session_id}` — submit or update text form fields.
  - `POST /reports/{session_id}/images/{group_name}` — accept a single image per request for a section/subsection namespaced photo group; stream to session directory; validate MIME type and dimensions with Pillow on save. Frontend fires parallel requests for multi-image groups.
  - `POST /reports/{session_id}/generate` — validate all required fields and photo groups are present, acquire render semaphore, render PDF, persist to output directory, return download.
- Guard PDF generation with `asyncio.Semaphore(3)` to limit concurrent renders.
- Implement a **storage repository layer** (`src/reportr/storage/report_repository.py`):
  - Abstract interface for all storage operations: create session, save images, save form fields, persist generated PDF, retrieve report metadata.
  - v1 implementation: filesystem-backed (temp directories for sessions, output directory for generated PDFs).
  - All endpoints and the renderer interact with storage only through this interface — never touch the filesystem directly.
  - This makes a future migration to Postgres a swap of the repository implementation without touching endpoints or renderer.
- Implement final renderer at `src/reportr/reporting/activity_report_pdf_renderer.py`:
  - Reference images from disk via `file://` URIs (no base64 data URIs).
  - Cover page first
  - Fixed narrative text blocks from template
  - Dynamic value substitution and photo block rendering per mapping
  - Reboundr design tokens and layout language adapted for WeasyPrint-safe fonts (see Design Reference section)
- **Generated PDF lifecycle**:
  - After rendering, persist the PDF to a reports output directory (e.g. `data/reports/{session_id}/report.pdf`).
  - PDFs remain available for re-download until explicitly deleted.
  - Session image directories are cleaned up after successful PDF generation.
  - Periodic cleanup job for abandoned sessions (no generate within configurable TTL).

## Design Reference (from `sbs-reboundr`)
- Color tokens (must match):
  - `--navy: #001760`
  - `--navy-deep: #000662`
  - `--orange: #f7550a`
  - `--ink: #1c2431`
  - `--muted: #5d6b80`
  - `--line: #d8dfeb`
  - `--panel: #f7f9fc`
  - `--paper: #ffffff`
- Frontend typography:
  - Display: `Barlow Condensed`
  - Body: `Manrope`
  - Mono/data: `JetBrains Mono`
- PDF typography fallback:
  - Body/display fallback: `Arial`, `Liberation Sans`, `Helvetica`, `sans-serif`
  - Mono fallback: `Courier New`, `Liberation Mono`, `DejaVu Sans Mono`, `monospace`
- UI patterns to preserve:
  - Orange left-accent section bars (`border-left: 3px solid var(--orange)`).
  - Upload zones with dashed borders and orange hover/focus emphasis.
  - BEM-style class naming (`section-bar`, `field__label`, `btn--primary`, etc.).
  - Subtle entrance animation (`fadeUp`: opacity + translateY).
  - Strong uppercase display headings; monospaced data/counters.
- PDF layout conventions to preserve:
  - A4 portrait with tight engineering-report margins.
  - Branded header with logo + navy title treatment.
  - Consistent figure captions and spacing rhythm.
  - Light gray paper background accents and orange highlight accents.

## Image Compression Strategy
- Frontend pre-upload compression:
  - Resize images to max **1000px** longest side.
  - Convert/compress to JPEG at quality **75**.
  - Upload compressed files only.
- Backend safety checks:
  - Max **15MB** per file.
  - Max **300MB** total per session.
  - Validate MIME types (accept `image/jpeg`, `image/png`, `image/webp` only).
  - Validate image dimensions with Pillow; reject images exceeding 1200px longest side.

## Memory Management Strategy
- **Disk persistence**: uploaded images are streamed to a temp directory on disk, not held in memory. Each report session gets a unique directory under a configurable temp root. Cleanup happens after PDF generation completes (or on session expiry for abandoned uploads).
- **Render concurrency limit**: use `asyncio.Semaphore(3)` (or configurable) to cap concurrent WeasyPrint renders. Requests beyond the limit queue until a slot opens. This caps peak render memory to ~3 concurrent renders worth of bitmaps.
- **Why this matters**: WeasyPrint decompresses every image to a raw bitmap regardless of file size. At 1000px longest side, each bitmap is ~2.3MB. 43 images × 2.3MB = ~100MB per render. With a semaphore of 3, peak render memory stays under ~300MB.

## Validation Commands
- If Python files changed:
  - `uv run ruff format . && uv run basedpyright && uv run pytest`
- If frontend files changed:
  - `bun run lint && bun run build`

## Future Improvements
- Projects index view listing all ingested/generated reports.
- Persistent progress/save draft and resume later.
- In-app PDF preview that matches WeasyPrint styling as closely as possible.
- Batch processing endpoint accepting CSV input to generate multiple reports.
- Structured backend logging for ingestion/render lifecycle (session create/save, per-image upload start+finish with size/dimensions/group, generate start/finish duration, and clear error events with session_id).

## Proposed Backend Logging Schema (for implementation)

### Format
- Structured JSON logs emitted from backend app handlers.
- UTC ISO8601 timestamps.
- Namespaced event IDs (example: `report.generate.completed`).
- Request correlation via `request_id` (use `X-Request-ID` when present; otherwise generate UUID4).

### Common fields
- `ts`, `level`, `event`, `request_id`
- `session_id` (when available)
- `route`, `method`, `status_code`, `duration_ms`
- `error_type`, `error_detail` (errors only)

### Event catalog
- `app.startup.storage_config` (INFO): `sessions_root`, `reports_root`, `session_ttl_seconds`, `cleanup_interval_seconds`
- `report.session.created` (INFO): `session_id`
- `report.form.saved` (INFO): `session_id`
- `report.image.upload.started` (DEBUG): `session_id`, `group_name`, `original_filename`, `content_type`, `size_bytes`
- `report.image.upload.completed` (INFO): `session_id`, `group_name`, `image_id`, `stored_filename`, `size_bytes`, `width`, `height`, `duration_ms`
- `report.image.upload.failed` (WARNING/ERROR): `session_id`, `group_name`, `status_code`, `error_type`
- `report.generate.started` (INFO): `session_id`
- `report.generate.skipped_existing_pdf` (INFO): `session_id`, `download_url`
- `report.generate.completed` (INFO): `session_id`, `pdf_size_bytes`, `duration_ms`
- `report.generate.conflict` (WARNING): `session_id`, `reason`
- `report.generate.failed` (ERROR): `session_id`, `error_type`, `duration_ms`
- `report.download.sent` (INFO): `session_id`, `filename`
- `report.download.missing` (WARNING): `session_id`
- `report.cleanup.completed` (INFO): `removed_count`, `max_age_seconds`, `duration_ms`

### Redaction / safety
- Do not log raw form values, binary image payloads, or full uploaded file contents.
- Prefer metadata only (counts, dimensions, MIME type, IDs).

### Log levels
- `DEBUG`: high-volume start/internal diagnostics (disabled by default in production).
- `INFO`: successful lifecycle events.
- `WARNING`: expected/recoverable issues (`409`, `422`, missing resources).
- `ERROR`: unexpected failures / unhandled exceptions.

## Execution Phases
1. Scaffold frontend with `bun create vue@latest`; setup backend package skeleton.
2. Implement storage repository layer (filesystem-backed v1).
3. Implement session-based API endpoints (`POST /reports`, `PUT /reports/{id}`, `POST /reports/{id}/images/{group}`, `POST /reports/{id}/generate`) with Pillow validation and render semaphore.
4. Implement frontend form + validation + client-side image compression (1000px, JPEG 75) + per-image upload to session endpoint.
5. Implement confirmation page with editable revert flow.
6. Implement final WeasyPrint template renderer (cover page + narrative sections + photo blocks via `file://` URIs).
7. Implement PDF persistence and session cleanup.
8. End-to-end integration and PDF download + re-download.
9. Run lint/type/test/build checks.
