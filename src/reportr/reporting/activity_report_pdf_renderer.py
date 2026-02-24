from calendar import month_name
from html import escape
from pathlib import Path
from typing import Protocol

from weasyprint import HTML

from reportr.storage import PhotoGroupName, ReportFormFields, ReportSession


class ActivityReportPdfRenderer(Protocol):
    def render(self, session: ReportSession) -> bytes:
        """Render a report session into PDF bytes."""
        ...


class RendererNotReadyError(RuntimeError):
    pass


class UnconfiguredActivityReportPdfRenderer:
    def render(self, session: ReportSession) -> bytes:
        _ = session
        raise RendererNotReadyError(
            "Activity report renderer is not configured yet. "
            "Implement activity_report_pdf_renderer before calling generate."
        )


class WeasyPrintActivityReportPdfRenderer:
    def __init__(self, *, sessions_root: Path = Path("data/sessions")) -> None:
        self._sessions_root = sessions_root

    def render(self, session: ReportSession) -> bytes:
        if session.form_fields is None:
            raise RendererNotReadyError("Report session has no form fields to render.")

        html = self._build_html(session)
        pdf_bytes = HTML(string=html, base_url=self._sessions_root.resolve().as_uri()).write_pdf()
        if pdf_bytes is None:
            raise RendererNotReadyError("Activity report renderer returned no PDF bytes.")

        return pdf_bytes

    def _build_html(self, session: ReportSession) -> str:
        if session.form_fields is None:
            raise RendererNotReadyError("Report session has no form fields to render.")

        form: ReportFormFields = session.form_fields

        testing_month = _format_testing_month(form.building_details.testing_date)
        building_name = escape(form.building_details.building_name)
        building_location = escape(form.building_details.building_location)
        number_of_storey = form.building_details.number_of_storey

        intro_paragraph = (
            "This activity report documents site observations and field testing outputs for "
            f"{building_name}, located at {building_location}. The subject structure is a "
            f"{number_of_storey}-storey building assessed under the agreed superstructure and "
            "substructure scope."
        )

        b1_paragraph = (
            "Rebar scanning was completed at "
            f"{form.superstructure.rebar_scanning.number_of_rebar_scan_locations} location(s)."
        )
        b2_paragraph = (
            "Rebound hammer testing was conducted at "
            f"{form.superstructure.rebound_hammer_test.number_of_rebound_hammer_test_locations} "
            "location(s)."
        )
        b3_paragraph = (
            "Concrete core extraction activities were performed at "
            f"{form.superstructure.concrete_core_extraction.number_of_coring_locations} "
            "location(s)."
        )
        b4_paragraph = (
            "Rebar extraction works produced "
            f"{form.superstructure.rebar_extraction.number_of_rebar_samples_extracted} sample(s)."
        )
        b6_paragraph = (
            "Restoration works used "
            f"{escape(form.superstructure.restoration_works.non_shrink_grout_product_used)} "
            "for non-shrink grouting and "
            f"{escape(form.superstructure.restoration_works.epoxy_ab_used)} for epoxy bonding."
        )
        c1_paragraph = (
            "Substructure coring covered "
            f"{form.substructure.concrete_core_extraction.number_of_foundation_locations} "
            "foundation location(s) with "
            f"{form.substructure.concrete_core_extraction.number_of_foundation_cores_extracted} "
            "core(s) extracted."
        )

        cover_photo = self._first_image_uri(session, PhotoGroupName.BUILDING_DETAILS_BUILDING_PHOTO)

        return f"""
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <style>
      @page {{
        size: A4;
        margin: 20mm 16mm 20mm;
      }}

      :root {{
        --navy: #001760;
        --navy-deep: #000662;
        --orange: #f7550a;
        --ink: #1c2431;
        --muted: #5d6b80;
        --line: #d8dfeb;
        --panel: #f7f9fc;
        --paper: #ffffff;
      }}

      * {{ box-sizing: border-box; }}

      body {{
        margin: 0;
        color: var(--ink);
        font: 12px/1.5 Arial, Liberation Sans, Helvetica, sans-serif;
      }}

      .cover {{
        min-height: 250mm;
        border: 1px solid var(--line);
        background: linear-gradient(160deg, #f8faff 0%, #f2f6ff 100%);
        padding: 10mm;
      }}

      .cover__heading {{
        margin: 0;
        color: var(--navy);
        font: 700 18pt/1.1 Arial, Liberation Sans, Helvetica, sans-serif;
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }}

      .cover__subheading {{
        margin: 3mm 0 0;
        color: var(--orange);
        font: 700 13pt/1.2 Arial, Liberation Sans, Helvetica, sans-serif;
        text-transform: uppercase;
      }}

      .cover__date {{
        margin: 1.2mm 0 8mm;
        color: var(--muted);
        font: 700 10pt/1.2 Courier New, Liberation Mono, DejaVu Sans Mono, monospace;
      }}

      .cover__image-wrap {{
        border: 1px solid var(--line);
        background: var(--paper);
        padding: 3mm;
      }}

      .cover__image {{
        width: 100%;
        max-height: 170mm;
        object-fit: cover;
      }}

      .page-break {{
        break-before: page;
      }}

      .report__header {{
        border-bottom: 2px solid var(--navy);
        padding-bottom: 4mm;
        margin-bottom: 5mm;
      }}

      .report__title {{
        margin: 0;
        color: var(--navy);
        font: 700 14pt/1.2 Arial, Liberation Sans, Helvetica, sans-serif;
        text-transform: uppercase;
      }}

      .section {{
        margin: 0 0 5mm;
        border: 1px solid var(--line);
        background: var(--panel);
        padding: 4mm;
      }}

      .section__heading {{
        margin: 0;
        padding-left: 3mm;
        border-left: 3px solid var(--orange);
        color: var(--navy-deep);
        font: 700 10pt/1.2 Arial, Liberation Sans, Helvetica, sans-serif;
        text-transform: uppercase;
      }}

      .section__paragraph {{
        margin: 2.3mm 0 0;
      }}

      .figure {{
        margin-top: 3mm;
      }}

      .figure__grid {{
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 2mm;
      }}

      .figure__img {{
        width: 100%;
        max-height: 64mm;
        object-fit: cover;
        border: 1px solid var(--line);
        background: var(--paper);
      }}

      .figure__caption {{
        margin: 1.6mm 0 0;
        color: var(--muted);
        font: 700 8.7pt/1.2 Arial, Liberation Sans, Helvetica, sans-serif;
      }}

      .signature {{
        margin-top: 8mm;
        border-top: 1px solid var(--line);
        padding-top: 6mm;
      }}

      .signature__label {{
        margin: 0;
        color: var(--muted);
      }}

      .signature__name {{
        margin: 4mm 0 0;
        font-weight: 700;
      }}

      .signature__role {{
        margin: 1mm 0 0;
      }}
    </style>
  </head>
  <body>
    <section class="cover">
      <h1 class="cover__heading">{building_name}</h1>
      <p class="cover__subheading">Activity Report</p>
      <p class="cover__date">{testing_month}</p>
      <div class="cover__image-wrap">
        {self._cover_image_markup(cover_photo)}
      </div>
    </section>

    <section class="page-break">
      <header class="report__header">
        <h1 class="report__title">Activity Report - {building_name}</h1>
      </header>

      {
            self._section(
                "A. INTRODUCTION",
                intro_paragraph,
                [
                    self._figure(
                        "Figure A.1",
                        self._all_image_uris(
                            session, PhotoGroupName.BUILDING_DETAILS_BUILDING_PHOTO
                        ),
                    ),
                ],
            )
        }

      {self._section("B. DATA GATHERING FOR SUPERSTRUCTURE", "")}
      {
            self._section(
                "B.1. Rebar Scanning",
                b1_paragraph,
                [
                    self._figure(
                        "Figure B.1",
                        self._all_image_uris(
                            session, PhotoGroupName.SUPERSTRUCTURE_REBAR_SCANNING_PHOTOS
                        ),
                    ),
                ],
            )
        }
      {
            self._section(
                "B.2. Rebound Hammer Test",
                b2_paragraph,
                [
                    self._figure(
                        "Figure B.2",
                        self._all_image_uris(
                            session, PhotoGroupName.SUPERSTRUCTURE_REBOUND_HAMMER_TEST_PHOTOS
                        ),
                    ),
                ],
            )
        }
      {
            self._section(
                "B.3. Concrete Core Extraction",
                b3_paragraph,
                [
                    self._figure(
                        "Figure B.3.1",
                        self._all_image_uris(
                            session, PhotoGroupName.SUPERSTRUCTURE_CONCRETE_CORING_PHOTOS
                        ),
                    ),
                    self._figure(
                        "Figure B.3.2",
                        self._all_image_uris(
                            session, PhotoGroupName.SUPERSTRUCTURE_CORE_SAMPLES_FAMILY_PIC
                        ),
                    ),
                ],
            )
        }
      {
            self._section(
                "B.4. Rebar Extraction",
                b4_paragraph,
                [
                    self._figure(
                        "Figure B.4.1",
                        self._all_image_uris(
                            session, PhotoGroupName.SUPERSTRUCTURE_REBAR_EXTRACTION_PHOTOS
                        ),
                    ),
                    self._figure(
                        "Figure B.4.2",
                        self._all_image_uris(
                            session, PhotoGroupName.SUPERSTRUCTURE_REBAR_SAMPLES_FAMILY_PIC
                        ),
                    ),
                ],
            )
        }
      {
            self._section(
                "B.5. Chipping of Existing Slab",
                "Slab chipping activities were completed based on inspection scope.",
                [
                    self._figure(
                        "Figure B.5",
                        self._all_image_uris(
                            session, PhotoGroupName.SUPERSTRUCTURE_CHIPPING_OF_SLAB_PHOTOS
                        ),
                    ),
                ],
            )
        }
      {
            self._section(
                "B.6. Restoration Works",
                b6_paragraph,
                [
                    self._figure(
                        "Figure B.6",
                        self._all_image_uris(
                            session, PhotoGroupName.SUPERSTRUCTURE_RESTORATION_PHOTOS
                        ),
                    ),
                ],
            )
        }

      {self._section("C. DATA GATHERING FOR SUBSTRUCTURE", "")}
      {
            self._section(
                "C.1. Concrete Core Extraction",
                c1_paragraph,
                [
                    self._figure(
                        "Figure C.1",
                        self._all_image_uris(
                            session, PhotoGroupName.SUBSTRUCTURE_CORING_FOR_FOUNDATION_PHOTOS
                        ),
                    ),
                ],
            )
        }
      {
            self._section(
                "C.2. Rebar Scanning",
                "Rebar scanning for foundation elements was completed.",
                [
                    self._figure(
                        "Figure C.2",
                        self._all_image_uris(
                            session,
                            PhotoGroupName.SUBSTRUCTURE_REBAR_SCANNING_FOR_FOUNDATION_PHOTOS,
                        ),
                    ),
                ],
            )
        }
      {
            self._section(
                "C.3. Restoration for Coring Works, Backfilling, and Compaction",
                "Restoration, backfilling, and compaction activities were completed after substructure coring.",
                [
                    self._figure(
                        "Figure C.3",
                        self._all_image_uris(
                            session,
                            PhotoGroupName.SUBSTRUCTURE_RESTORATION_BACKFILLING_COMPACTION_PHOTOS,
                        ),
                    ),
                ],
            )
        }

      <section class="signature">
        <p class="signature__label">Prepared by:</p>
        <p class="signature__name">{escape(form.signature.prepared_by)}</p>
        <p class="signature__role">{escape(form.signature.prepared_by_role)}</p>
      </section>
    </section>
  </body>
</html>
"""

    def _cover_image_markup(self, image_uri: str | None) -> str:
        if image_uri is None:
            return "<p>No building photo uploaded.</p>"
        return f'<img class="cover__image" src="{image_uri}" alt="Building photo" />'

    def _section(self, heading: str, paragraph: str, figures: list[str] | None = None) -> str:
        paragraph_markup = (
            f'<p class="section__paragraph">{escape(paragraph)}</p>' if paragraph.strip() else ""
        )
        figures_markup = "".join(figures or [])

        return f"""
<section class="section">
  <h2 class="section__heading">{escape(heading)}</h2>
  {paragraph_markup}
  {figures_markup}
</section>
"""

    def _figure(self, caption: str, image_uris: list[str]) -> str:
        images_markup = "".join(
            f'<img class="figure__img" src="{uri}" alt="{escape(caption)}" />' for uri in image_uris
        )
        if not images_markup:
            images_markup = "<p>No images uploaded for this figure.</p>"

        return f"""
<section class="figure">
  <div class="figure__grid">{images_markup}</div>
  <p class="figure__caption">{escape(caption)}</p>
</section>
"""

    def _first_image_uri(self, session: ReportSession, group_name: PhotoGroupName) -> str | None:
        uris = self._all_image_uris(session, group_name)
        if uris:
            return uris[0]
        return None

    def _all_image_uris(self, session: ReportSession, group_name: PhotoGroupName) -> list[str]:
        image_metadata = session.images.get(group_name.value, [])
        image_uris: list[str] = []

        for image in image_metadata:
            image_path = (
                self._sessions_root
                / str(session.id)
                / "images"
                / group_name.value
                / image.stored_filename
            )
            if image_path.exists():
                image_uris.append(image_path.resolve().as_uri())

        return image_uris


def _format_testing_month(testing_date: str) -> str:
    parts = testing_date.split("-")
    if len(parts) != 2:
        return testing_date

    year, month = parts
    try:
        month_number = int(month)
        if month_number < 1 or month_number > 12:
            return testing_date
        return f"{month_name[month_number].upper()} {year}"
    except ValueError:
        return testing_date
