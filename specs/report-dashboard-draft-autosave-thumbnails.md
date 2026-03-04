## Feature: Report Dashboard, Draft Autosave, and Intake Photo Thumbnails

### Discovery Summary (Current Architecture)
- Backend is a FastAPI service (`src/reportr/app/web_api.py`) backed by a filesystem repository (`src/reportr/storage/report_repository.py`).
- Session metadata is stored in `data/sessions/<session_id>/session.json`; generated PDFs are in `data/reports/<session_id>/`.
- `ReportSession` currently tracks `id`, `created_at`, `status`, `form_fields`, `images`, and `generated_pdf_path`, but **does not** track last modified metadata or user emails.
- Current intake flow is route-based (`/` intake -> `/confirm` confirmation) but state is kept in a singleton in-memory composable (`use-report-intake-draft.ts`), so refresh/navigation can lose progress.
- Images are currently uploaded only during form submit; `ImageUploadField.vue` lists file names/status and does not render thumbnails.
- Completed generation currently deletes session images (`cleanup_session_images` after generate), which conflicts with reopening completed records and thumbnail preview requirements.

---

### Problem Statement
**Who:** Authenticated SBS users (all users, not admin-restricted).

**What:**
1. They need a dashboard showing all report files (in-progress, completed, archived) with created/modified timestamps and created/last-modified email addresses.
2. They need progress persistence so they can leave and resume without losing work (autosave + explicit save affordance).
3. They need image thumbnails in intake instead of filename-only rows, both for newly selected files and when reopening existing records.

**Why it matters:** Current all-or-nothing flow causes lost work and poor visibility across users, slowing operations and causing duplicate effort.

**Evidence:** Current implementation keeps draft state in frontend memory and only persists on the confirmation submit path.

---

### Proposed Solution (Recommended: Balanced)
Implement persistent server-backed draft editing with an all-user dashboard and Cloudflare Access identity plumbing.

1. **Lifecycle + metadata foundation**
   - Extend session metadata with `updated_at`, `created_by_email`, `updated_by_email`, plus archive metadata.
   - Add explicit archive lifecycle while keeping existing completion flow.

2. **Dashboard APIs + page**
   - Add list/read/status APIs and a new dashboard route as the app entry page.
   - Dashboard shows status, created/updated timestamps, and created/updated emails.
   - Dashboard actions: open/edit, download (if completed), archive, restore.

3. **Draft persistence and autosave**
   - Persist form drafts server-side as users edit.
   - Use debounced autosave with a visible save state (`Saving…`, `Saved at…`, `Save failed`).
   - Keep manual **Save Draft** button as explicit fallback/retry.

4. **Thumbnail-capable image handling**
   - Add image retrieval endpoint(s) for stored images.
   - Intake UI renders thumbnail previews for local selections and server-loaded images when resuming drafts/completed records.

5. **Cloudflare Access identity plumbing**
   - Validate `Cf-Access-Jwt-Assertion` when CF Access env vars are configured.
   - Extract email claim and stamp all mutating operations with user identity.

---

### Constraints Inventory
- Existing filesystem repository must remain primary storage.
- Existing data under `data/sessions` must remain readable (backward compatibility).
- Vue stack should stay Composition API + `<script setup lang="ts">`.
- No Docker/dev server changes implied in this spec.
- Keep implementation minimal; avoid introducing role-based permissions in this phase.

---

### Solution Space
| Option | Description | Pros | Cons |
|---|---|---|---|
| Simplest | LocalStorage autosave only + no backend dashboard metadata | Fastest | Fails all-user dashboard/audit requirements |
| **Balanced (Chosen)** | Server-backed drafts + dashboard + CF identity + thumbnail retrieval | Meets requirements with moderate complexity | Requires backend+frontend cross-cutting changes |
| Full engineering | Balanced + record version history + optimistic locking + role controls | Strong audit/concurrency model | Significant scope increase (XL+) |

---

### Scope & Deliverables
| Deliverable | Effort | Depends On |
|---|---|---|
| D1. Extend backend models/repository for audit + archive lifecycle | L | - |
| D2. Add API contracts for dashboard list/read, image preview, archive/restore, and draft-save identity stamping | L | D1 |
| D3. Implement Cloudflare Access email extraction/validation dependency | M | D1 |
| D4. Build Dashboard screen + routing + actions | M | D2 |
| D5. Implement intake autosave/manual save status + resume existing session loading | L | D2, D4 |
| D6. Add thumbnail rendering for local and persisted images in intake flow | M | D2, D5 |
| D7. Tests (backend + frontend) and backward-compatibility coverage | M | D1-D6 |

**Total effort:** XL (cross-cutting changes, >2 days)

---

### Non-Goals (Explicit Exclusions)
- Hard delete/permanent delete workflow (archive only in this phase).
- Role-based authorization (all authenticated users can view and act on records).
- Real-time collaborative editing conflict resolution (last-write-wins for now).
- PDF version history/diffing.

---

### Data Model

#### Backend model changes
1. `ReportStatus` (retain compatibility):
   - `draft` (display label: **In Progress**)
   - `generating`
   - `completed`
   - `archived` (new)

2. `ReportSession` additions:
   - `updated_at: datetime`
   - `created_by_email: str`
   - `updated_by_email: str`
   - `archived_at: datetime | None`
   - `archived_by_email: str | None`

3. `ImageMeta` additions:
   - `uploaded_at: datetime`
   - `uploaded_by_email: str`

4. Draft fields strategy:
   - Introduce `ReportDraftFields` (same shape as current form but tolerant of incomplete values).
   - `ReportSession.form_fields` stores draft-safe form state.
   - `generate` path validates/coerces `form_fields` into strict `ReportFormFields` before rendering.

#### Frontend type additions
- `ReportListItem` (dashboard summary)
- Save-state enum: `idle | saving | saved | error`
- `UploadItem` updated to support both local and persisted entries:
  - `file: File | null`
  - `previewUrl: string`
  - `source: 'local' | 'remote'`

#### Backward compatibility rules
- Existing `session.json` files lacking new fields should hydrate with defaults:
  - `updated_at = created_at`
  - `created_by_email = "unknown@legacy"`
  - `updated_by_email = "unknown@legacy"`
  - archive fields default `null`

---

### API / Interface Contract

#### Identity dependency
- New dependency (e.g., `get_cf_access_email`) resolves user email for mutating endpoints.
- When `CF_ACCESS_TEAM_DOMAIN` + `CF_ACCESS_AUD` are configured:
  - Require `Cf-Access-Jwt-Assertion` header.
  - Validate token with CF certs endpoint (`<team-domain>/cdn-cgi/access/certs`) and cache certs.
  - Extract `email` claim.
- When not configured (local/dev mode): allow request with fallback email (`local-dev@localhost`) for compatibility.

#### Endpoints
1. `GET /reports`
   - Query: `status` (optional, repeatable), `limit`, `offset`
   - Returns paginated report summaries for dashboard.

2. `GET /reports/{session_id}`
   - Returns full session for resume/edit.

3. `PUT /reports/{session_id}` (updated semantics)
   - Accepts `ReportDraftFields` snapshot.
   - Updates `form_fields`, `updated_at`, `updated_by_email`.
   - If current status is `completed`, transition to `draft` and clear stale `generated_pdf_path`.

4. `PUT /reports/{session_id}/images/{group_name}` (new/replace-group)
   - Accepts one-or-many files (group replacement semantics).
   - Replaces existing group images atomically.
   - Updates session `updated_*` metadata and image uploader metadata.
   - If status is `completed`, transition to `draft` and clear stale PDF reference.

5. `GET /reports/{session_id}/images/{group_name}/{image_id}`
   - Returns image bytes for thumbnail rendering.

6. `PATCH /reports/{session_id}/status`
   - Allowed transitions in this phase:
     - `draft|completed -> archived`
     - `archived -> draft`
   - Updates `updated_*`; archive actions set/clear archive metadata.

7. Existing `POST /reports/{session_id}/generate`
   - Validates strict completeness from stored draft.
   - Sets status `generating -> completed` on success.
   - **Do not delete session images on completion** (required for reopen + thumbnails).

---

### Lifecycle & Business Rules
1. **All users visibility:** Dashboard lists all records for authenticated users.
2. **Completed records editable:** Any edit to a completed record reopens it to `draft` and invalidates stale generated PDF path.
3. **Archive-only deletion policy:** Archive records instead of hard-deleting.
4. **Autosave behavior:**
   - Debounce at 1500ms after field changes.
   - One in-flight save at a time; coalesce pending changes.
   - Manual save button forces immediate flush.
5. **Save status UX:** show saving/saved/error with last-saved timestamp.

---

### Frontend Implementation Plan
1. **Routing**
   - `/` -> `DashboardScreen`
   - `/reports/new` -> `IntakeFormScreen`
   - `/reports/:sessionId/edit` -> `IntakeFormScreen` in resume mode
   - `/reports/:sessionId/confirm` -> `ConfirmationScreen`

2. **DashboardScreen**
   - Table/list with status chips and metadata columns:
     - Created at, Updated at, Created by email, Last modified by email
   - Actions by status:
     - In progress: Open, Archive
     - Completed: Open/Edit, Download, Archive
     - Archived: Open, Restore

3. **Intake autosave + manual save**
   - Deep watch form fields -> debounced API save.
   - Add `Save Draft` button + save-state indicator.
   - On load (edit route), fetch session and hydrate form + uploads.

4. **Thumbnails in `ImageUploadField.vue`**
   - Render thumbnail grid (small preview + filename + upload state).
   - Show local object URL for newly selected files.
   - Show server URL previews for persisted images.

---

### Acceptance Criteria
- [ ] Dashboard route exists and lists all records with status, created/updated timestamps, created-by email, and updated-by email.
- [ ] Dashboard supports archive and restore actions; archived records remain visible under archived status.
- [ ] Users can open any in-progress/completed record from dashboard and continue editing.
- [ ] Editing a completed record transitions it back to in-progress (`draft`) and requires regeneration for a fresh PDF.
- [ ] Intake form autosaves after changes (debounced), and a manual Save Draft button is available.
- [ ] Intake screen displays save state (`Saving…`, `Saved at…`, `Failed to save`).
- [ ] `ImageUploadField.vue` shows thumbnails for selected local files and persisted server files when reopening records.
- [ ] Cloudflare Access identity is validated (when configured), and mutating operations stamp created/updated emails accordingly.
- [ ] Existing pre-change session files are still readable without migration failure.

---

### Test Strategy
| Layer | What | How |
|---|---|---|
| Backend unit | Model compatibility defaults, lifecycle transitions, status update rules | Extend `test_report_repository.py` |
| Backend integration | New list/read/status/image endpoints; autosave semantics; completed->draft reopening | Extend `test_reports_api.py` |
| Backend auth | CF JWT validation + missing-token behavior when configured | Add/restore `tests/test_cf_access_auth.py` |
| Frontend unit | Dashboard rendering/actions; autosave state; thumbnail rendering | Add/update Vue test specs |
| End-to-end (optional) | Create -> autosave -> leave -> resume -> edit completed -> regenerate | Playwright flow |

---

### Risks & Mitigations
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Cloudflare cert fetch/JWT validation failures block writes | Medium | High | Cache certs, clear 503 errors, local-dev bypass when CF env not configured |
| Increased disk usage because completed images are retained | High | Medium | Keep file-size/group limits; add future archived-retention cleanup policy |
| Autosave race conditions overwrite recent changes | Medium | Medium | Debounce + single-flight request queue + last-write-wins behavior documented |
| Cross-user concurrent edits cause silent clobbering | Medium | Medium | Show `updated_at`/`updated_by` in UI; document non-goal for optimistic locking in phase 1 |

---

### Trade-offs Made
| Chose | Over | Because |
|---|---|---|
| Server-backed autosave + manual save fallback | Manual-save only | Prevents data loss and supports resume/dashboard consistency |
| Keep `draft` backend status value as in-progress label | Renaming to `in_progress` now | Minimizes migration impact for existing stored sessions/tests |
| Replace-group image API for edits | Only append-style upload API | Aligns with current UI behavior where users reselect full group and expect replacement |
| No hard delete in phase 1 | Add delete now | Meets archive requirement while keeping lifecycle safe and reversible |

---

### Open Questions
- [ ] None blocking for implementation in this phase.

---

### Success Metrics
- 0 user reports of lost intake progress after navigation/reload in first rollout window.
- >=90% of edits persist via autosave without manual retry (based on client logs/telemetry if added).
- Dashboard load p95 under 500ms for first page of records in expected dataset size.
- Completed records can be reopened and re-generated successfully end-to-end.
