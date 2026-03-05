# SBS Reportr — User Instructions

SBS Reportr is a web-based tool for generating **Structural Activity Report PDFs**. You fill in project details, upload site photos, and the app produces a branded, template-faithful report ready for submission.

> **Good to know:** The **Substructure** section (C.1–C.3) is entirely optional. You can generate a complete report without filling it out — any skipped substructure sections are simply omitted from the final PDF.

---

## Getting Started

Open the application in your browser. You will land on the **Activity Report Intake** form — a single scrollable page where all information is entered before generating the final PDF.

---

## Step 1 — Fill Out the Intake Form

The form is organized into sections that mirror the final report structure. Complete every section from top to bottom.

### Building Details (Cover Page)

| Field                 | Description                                                                                            |
| --------------------- | ------------------------------------------------------------------------------------------------------ |
| **Testing Date**      | Month and year of the structural testing activity (month picker).                                      |
| **Building Name**     | Name of the building under inspection (max 200 characters).                                            |
| **Building Location** | Full address or description of the building location (max 500 characters).                             |
| **Number of Storey**  | Total number of storeys of the building (minimum 1).                                                   |
| **Building Photo**    | A photo of the building exterior. This appears on the report cover page. **Exactly 1 photo required.** |

### Superstructure Sections

#### B.1 — Rebar Scanning

- **Number of rebar scan locations** — integer, minimum 1.
- **Rebar Scanning Photos** — 1 to 5 photos of rebar scanning activity.

#### B.2 — Rebound Hammer Test

- **Number of rebound hammer test locations** — integer, minimum 1.
- **Rebound Hammer Test Photos** — 1 to 5 photos.

#### B.3 — Concrete Core Extraction

- **Number of coring locations** — integer, minimum 1.
- **Concrete Coring Photos** — 1 to 5 photos of the coring process.
- **Core Samples Family Photo** — 1 to 2 photos showing all core samples together.

#### B.4 — Rebar Extraction

- **Number of rebar samples extracted** — integer, minimum 1.
- **Rebar Extraction Photos** — 1 to 5 photos.
- **Rebar Samples Family Photo** — 1 to 2 photos showing all rebar samples together.

#### B.5 — Chipping of Existing Slab

- **Chipping of Slab Photos** — 1 to 2 photos.

#### B.6 — Restoration Works

- **Non-shrink grout product used** — product name (max 200 characters).
- **Epoxy A&B used** — product name (max 200 characters).
- **Restoration Photos** — 1 to 5 photos.

### Substructure Sections (Optional)

All substructure fields and photos below are **optional**. If you leave this entire section blank, the report will be generated without the substructure portion. Any subsection you _do_ fill out will appear in the final PDF.

#### C.1 — Concrete Core Extraction _(optional)_

- **Number of selected foundation locations** — integer, minimum 1 (if provided).
- **Number of extracted cores** — integer, minimum 1 (if provided).
- **Foundation Coring Photos** — 1 to 3 photos.

#### C.2 — Rebar Scanning _(optional)_

- **Foundation Rebar Scanning Photos** — 1 to 3 photos.

#### C.3 — Restoration, Backfilling, and Compaction _(optional)_

- **Restoration, Backfilling, and Compaction Photos** — 1 to 5 photos.

### ANNEX (Optional)

You may optionally upload **PDF documents** for any of the following annex subsections. Leave a subsection blank to skip it in the generated report.

| Annex     | Description                                        |
| --------- | -------------------------------------------------- |
| ANNEX I   | Rebar Scanning Output                              |
| ANNEX II  | Rebound Number Test Results                        |
| ANNEX III | Compressive Strength Test Results (Superstructure) |
| ANNEX IV  | Tensile Strength Test Results                      |
| ANNEX V   | Compressive Strength Test Results (Substructure)   |
| ANNEX VI  | Rebar Scanning Results for Foundation              |
| ANNEX VII | Material Tests Mapping                             |

> **Note:** Only PDF files are accepted for annex uploads. One PDF per annex subsection.

### Signature

| Field           | Description                                                           |
| --------------- | --------------------------------------------------------------------- |
| **Prepared by** | Full name of the person who prepared the report (max 100 characters). |
| **Role**        | Title or role of the preparer (max 100 characters).                   |

---

## Step 2 — Upload Photos

Each section has a photo upload zone. To add photos:

1. Click the upload area or drag and drop image files. On mobile devices, you can also **capture a photo directly from your camera** when the file picker opens.
2. Accepted formats: **JPEG**, **PNG**, and **WebP**.
3. Images are automatically compressed before upload (resized to max 1000 px longest side, JPEG quality 75).
4. Each image must be under **15 MB**; the total per session is capped at **300 MB**.
5. A thumbnail preview appears for each uploaded photo.

To remove a photo, click the remove button on its thumbnail.

> **Tip:** The **Continue to Confirmation** button stays disabled until all required text fields are filled and every photo group has at least its minimum number of photos uploaded.

---

## Step 3 — Review on the Confirmation Page

After clicking **Continue to Confirmation**, you are taken to a review page that summarizes all entered data:

- **Building Snapshot** — testing date, building name, location, and number of storeys.
- **Key Counts** — all numeric values for superstructure and substructure sections, plus the preparer signature details.
- **Photo Coverage** — a checklist of all photo groups with uploaded counts and thumbnail previews.

### What you can do here

| Action                        | Effect                                                                                               |
| ----------------------------- | ---------------------------------------------------------------------------------------------------- |
| **Revert**                    | Returns you to the editable intake form with all values preserved. Make corrections, then re-submit. |
| **Continue and Generate PDF** | Begins PDF generation. The report is rendered server-side and a download starts automatically.       |

---

## Step 4 — Download Your Report

Once generation completes, the PDF downloads automatically to your browser. The status message confirms: _"Report generated. Download started."_

If you need the file again later, you can re-trigger the download from the confirmation page as long as the session is still active.

---

## Image Requirements Summary

| Constraint                               | Limit                         |
| ---------------------------------------- | ----------------------------- |
| Accepted formats                         | JPEG, PNG, WebP               |
| Max single image size                    | 15 MB                         |
| Max total upload per session             | 300 MB                        |
| Max image longest side (server enforced) | 1200 px                       |
| Client-side compression target           | 1000 px longest side, JPEG 75 |

---

## Troubleshooting

| Issue                             | Solution                                                                                                                                                                                                    |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **"Continue" button is disabled** | Ensure all required text fields are filled and every **superstructure** photo group has at least its minimum number of photos. Substructure fields are optional. Check for red error messages on any field. |
| **Upload fails**                  | Verify the image is JPEG, PNG, or WebP and under 15 MB. Try a different image or reduce its size.                                                                                                           |
| **PDF generation fails**          | Check that all sections are completed. If the error persists, try reverting to the form, verifying your inputs, and re-submitting.                                                                          |
| **Session expired**               | Sessions are automatically cleaned up after 24 hours of inactivity. Reload the page and start a new report.                                                                                                 |
