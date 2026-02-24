# Frontend Bugfix Plan

## Scope
- Align the intake UI with the expected report flow from the reference PDF.
- Reuse the branded SVG assets from `sbs-reboundr` and restore a clear header/footer shell.
- Keep existing backend payload shape and upload endpoints unchanged.

## Reported Issues
1. Brand SVG assets from `sbs-reboundr` are missing in the frontend.
2. The page shell is missing the expected header/footer treatment.
3. Form flow does not match the required section-by-section sequence.

## Implementation Plan
1. Copy `asset-79.svg` and `asset-80.svg` into `src/frontend/public/` and wire them into the app shell.
2. Update `src/frontend/src/App.vue` to include a consistent header and footer around routed screens.
3. Refactor `src/frontend/src/screens/IntakeFormScreen.vue` to follow this exact order:
   - Building Details (fields + building photo)
   - Superstructure sections in order (rebar scanning, rebound hammer, concrete core extraction, rebar extraction, chipping, restoration)
   - Substructure sections in order (concrete core extraction, rebar scanning, restoration/backfilling/compaction)
   - Signature
4. Keep photo upload limits per group as configured and display each image group within its corresponding section.
5. Update affected frontend tests and run `bun run lint && bun run build`.

## Acceptance Checks
- Header/footer branding appears on intake and confirmation screens.
- All required fields appear in the expected sequence.
- Each photo uploader is shown under the matching section with the correct max count.
- Form submission, confirmation flow, and generation actions still work.
