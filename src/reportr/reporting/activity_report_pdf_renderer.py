from calendar import month_name
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Protocol

from weasyprint import HTML

from reportr.storage import PhotoGroupName, ReportFormFields, ReportSession


@dataclass(frozen=True, slots=True)
class _ImageInfo:
    uri: str
    is_landscape: bool


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
        logo_uri = self._company_logo_uri()

        cover_photo = self._first_image_uri(session, PhotoGroupName.BUILDING_DETAILS_BUILDING_PHOTO)
        building_photos = self._all_image_info(
            session, PhotoGroupName.BUILDING_DETAILS_BUILDING_PHOTO
        )

        storey_count = _number_to_words(form.building_details.number_of_storey)
        rebar_scan_locations = _words_with_digits(
            form.superstructure.rebar_scanning.number_of_rebar_scan_locations
        )
        rebound_test_locations = _words_with_digits(
            form.superstructure.rebound_hammer_test.number_of_rebound_hammer_test_locations
        )
        core_extraction_locations = _words_with_digits(
            form.superstructure.concrete_core_extraction.number_of_coring_locations
        )
        rebar_samples = _words_with_digits(
            form.superstructure.rebar_extraction.number_of_rebar_samples_extracted
        )
        foundation_locations = _words_with_digits(
            form.substructure.concrete_core_extraction.number_of_foundation_locations
        )
        foundation_cores = _words_with_digits(
            form.substructure.concrete_core_extraction.number_of_foundation_cores_extracted
        )
        grout_product = escape(form.superstructure.restoration_works.non_shrink_grout_product_used)
        epoxy_product = escape(form.superstructure.restoration_works.epoxy_ab_used)

        introduction_opening_paragraph = (
            "SBStruc Engineering conducted destructive testing, non-destructive testing, and "
            "foundation excavation on the existing "
            f"<strong>{storey_count}-storey building, {building_name}</strong>, located in "
            f"<strong>{building_location}</strong>."
        )
        introduction_closing_paragraph = (
            "This work was undertaken solely to gather data and information on the existing "
            "building. Concrete core extraction and rebar extraction were performed to obtain "
            "samples for the determination of concrete and reinforcing steel properties, "
            "respectively. Non-destructive testing, including rebar scanning and rebound hammer "
            "testing, was also carried out to collect additional data on concrete characteristics, "
            "identify rebar sizes, and document the probable quantity and layout of reinforcement "
            "within the building's structural components. Chipping of selected portions of the "
            "existing slab was conducted to verify the existing reinforcement. Excavation works "
            "were conducted to gather data on the existing foundation."
        )
        b1_paragraph = (
            "Rebar scanning was performed using non-destructive testing methods to determine the "
            "quantity, spacing, and approximate diameter of reinforcing steel bars embedded within "
            "the concrete elements. This activity was carried out to verify reinforcement detailing "
            "and support the structural assessment without causing damage to the members. A total "
            f"of <strong>{rebar_scan_locations} rebar scan locations</strong> were evaluated, "
            "and initial rebar data were recorded on site during the scanning process. The "
            "compiled results for the selected structural members are presented in "
            "<strong>Annex I</strong>."
        )
        b2_paragraph = (
            "Non-destructive testing using the Rebound Hammer Test was conducted on selected "
            "structural members to assess the uniformity and relative quality of the in-situ "
            "concrete strength, as indicated by the measured Q-values. A total of "
            f"<strong>{rebound_test_locations} test locations</strong> were evaluated and "
            "distributed across the structure. At each test location, ten (10) rebound hammer "
            "impacts were applied in accordance with standard testing procedures consistent with "
            "ASTM C805. The rebound numbers obtained were statistically analyzed, with mean "
            "values calculated for each structural member. A summary of the rebound number test "
            "results is presented in <strong>Annex II</strong>."
        )
        b3_paragraph = (
            "Concrete core extraction was conducted on selected structural members to obtain "
            "representative samples of the building's in-situ concrete. A total of "
            f"<strong>{core_extraction_locations} cores</strong> were extracted. The specimens "
            "were used to assess concrete quality, including compressive strength and overall "
            "material condition. Compressive strength testing was performed in accordance with "
            "ASTM C42/C42M, and the corresponding results are presented in <strong>Annex "
            "III</strong>."
        )
        b4_paragraph_intro = (
            "Rebar extraction was carried out on selected structural members to obtain "
            "representative reinforcement samples from the building's structural system. A total "
            f"of <strong>{rebar_samples} rebar samples</strong> were extracted."
        )
        b4_paragraph_close = (
            "The extracted rebars were evaluated to determine their material properties, including "
            "tensile strength. The tensile test results are presented in <strong>Annex IV</strong>."
        )
        b5_paragraph = (
            "Chipping of the existing slab at one selected location was conducted to verify the "
            "reinforcement size."
        )
        b6_paragraph = (
            "Following the completion of concrete coring, rebar extraction, and chipping of slab, "
            "reinstatement works were carried out to restore the affected structural elements and "
            "ensure continuity of structural performance. Structural components from which samples "
            "were extracted were restored to their original condition. Removed reinforcement was "
            "replaced with new rebars of equivalent diameter and grade to maintain structural "
            "capacity. Concrete that was chipped or removed during the verification and extraction "
            f"process was reinstated using <strong>{grout_product}</strong> non-shrink grout, "
            "with proper bonding between existing and new concrete ensured through the application "
            f"of <strong>{epoxy_product}</strong> structural adhesive."
        )
        c1_paragraph = (
            "Concrete core extraction was conducted at "
            f"<strong>{foundation_locations} selected foundation locations</strong> to obtain "
            "representative samples of the building's in-situ concrete. A total of "
            f"<strong>{foundation_cores} cores</strong> were extracted. The specimens were used "
            "to determine concrete properties, including compressive strength. Compressive strength "
            "testing was performed in accordance with ASTM C42/C42M, and the results are "
            "presented in <strong>Annex V</strong>."
        )
        c2_paragraph = (
            "Rebar scanning was performed using non-destructive testing methods to determine the "
            "quantity, spacing, and approximate diameter of reinforcing steel bars embedded within "
            "the concrete foundation. The initial rebar data were recorded on site during the "
            "scanning process. The compiled results for the foundation are presented in "
            "<strong>Annex VI</strong>."
        )
        c3_paragraph = (
            "Following the concrete core extraction, the excavated foundation areas were "
            "backfilled using the previously removed soils and compacted to restore the "
            "foundation to its original profile."
        )

        header_logo_markup = (
            '<p class="report-header__logo-fallback">Company Logo</p>'
            if logo_uri is None
            else f'<img class="report-header__logo" src="{logo_uri}" alt="Company logo" />'
        )
        cover_logo_markup = (
            '<p class="cover__logo-fallback">Company Logo</p>'
            if logo_uri is None
            else f'<img class="cover__logo" src="{logo_uri}" alt="Company logo" />'
        )

        report_body = "".join(
            [
                self._chapter_section(
                    "A. INTRODUCTION",
                    "".join(
                        [
                            self._paragraph(introduction_opening_paragraph),
                            self._figure(
                                form.building_details.building_name,
                                building_photos,
                                contain_images=True,
                                large=True,
                            ),
                            self._paragraph(introduction_closing_paragraph),
                        ]
                    ),
                ),
                self._chapter_heading("B. DATA GATHERING FOR SUPERSTRUCTURE"),
                self._subsection(
                    "B.1. Rebar Scanning",
                    self._paragraph(b1_paragraph)
                    + self._figure(
                        "Figure B.1. REBAR SCANNING",
                        self._all_image_info(
                            session, PhotoGroupName.SUPERSTRUCTURE_REBAR_SCANNING_PHOTOS
                        ),
                    ),
                ),
                self._subsection(
                    "B.2. Rebound Hammer Test",
                    self._paragraph(b2_paragraph)
                    + self._figure(
                        "Figure B.2. REBOUND HAMMER TESTS",
                        self._all_image_info(
                            session, PhotoGroupName.SUPERSTRUCTURE_REBOUND_HAMMER_TEST_PHOTOS
                        ),
                    ),
                ),
                self._subsection(
                    "B.3. Concrete Core Extraction",
                    self._paragraph(b3_paragraph)
                    + self._figure(
                        "Figure B.3.1 Concrete Core Extraction",
                        self._all_image_info(
                            session, PhotoGroupName.SUPERSTRUCTURE_CONCRETE_CORING_PHOTOS
                        ),
                    )
                    + self._figure(
                        "Figure B.3.2 Extracted Core Samples",
                        self._all_image_info(
                            session, PhotoGroupName.SUPERSTRUCTURE_CORE_SAMPLES_FAMILY_PIC
                        ),
                        contain_images=True,
                    ),
                ),
                self._subsection(
                    "B.4. Rebar Extraction",
                    self._paragraph(b4_paragraph_intro)
                    + self._figure(
                        "Figure B.4.1 Rebar Extraction",
                        self._all_image_info(
                            session, PhotoGroupName.SUPERSTRUCTURE_REBAR_EXTRACTION_PHOTOS
                        ),
                    )
                    + self._figure(
                        "Figure B.4.2 Extracted Rebar Samples",
                        self._all_image_info(
                            session, PhotoGroupName.SUPERSTRUCTURE_REBAR_SAMPLES_FAMILY_PIC
                        ),
                    )
                    + self._paragraph(b4_paragraph_close),
                ),
                self._subsection(
                    "B.5. Chipping of Existing Slab",
                    self._paragraph(b5_paragraph)
                    + self._figure(
                        "Figure B.5. Chipping of Existing Slab",
                        self._all_image_info(
                            session, PhotoGroupName.SUPERSTRUCTURE_CHIPPING_OF_SLAB_PHOTOS
                        ),
                    ),
                ),
                self._subsection(
                    "B.6. Restoration Works",
                    self._paragraph(b6_paragraph)
                    + self._figure(
                        "Figure B.6. Restoration Works",
                        self._all_image_info(
                            session, PhotoGroupName.SUPERSTRUCTURE_RESTORATION_PHOTOS
                        ),
                    ),
                ),
                self._chapter_heading("C. DATA GATHERING FOR SUBSTRUCTURE"),
                self._subsection(
                    "C.1. Concrete Core Extraction",
                    self._paragraph(c1_paragraph)
                    + self._figure(
                        "Figure C.1. Concrete Core Extraction for Foundation",
                        self._all_image_info(
                            session, PhotoGroupName.SUBSTRUCTURE_CORING_FOR_FOUNDATION_PHOTOS
                        ),
                    ),
                ),
                self._subsection(
                    "C.2. Rebar Scanning",
                    self._paragraph(c2_paragraph)
                    + self._figure(
                        "Figure C.2. Rebar Scanning for Foundation",
                        self._all_image_info(
                            session,
                            PhotoGroupName.SUBSTRUCTURE_REBAR_SCANNING_FOR_FOUNDATION_PHOTOS,
                        ),
                    ),
                ),
                self._subsection(
                    "C.3. Restoration for Coring Works, Backfilling, and Compaction",
                    self._paragraph(c3_paragraph)
                    + self._figure(
                        "Figure C.3. Restoration for Coring Works, Backfilling, and Compaction",
                        self._all_image_info(
                            session,
                            PhotoGroupName.SUBSTRUCTURE_RESTORATION_BACKFILLING_COMPACTION_PHOTOS,
                        ),
                    ),
                ),
            ]
        )

        return f"""
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <style>
      @page {{
        size: A4;
        margin: 16mm;
      }}

      @page cover {{
        margin: 16mm;
      }}

      @page report {{
        margin: 40mm 16mm 20mm;
        @top-center {{
          content: element(report-header);
          width: 100%;
        }}
      }}

      @page report:first {{
        counter-reset: page 1;
      }}

      * {{
        box-sizing: border-box;
      }}

      body {{
        margin: 0;
        color: #1b1b1b;
        font: 12px/1.6 "Times New Roman", Times, serif;
        background: #ffffff;
      }}

      strong {{
        font-weight: 700;
      }}

      .cover {{
        page: cover;
        height: 265mm;
        border: 1px solid #cbcbcb;
        background: #ffffff;
        padding: 10mm;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        gap: 6mm;
      }}

      .cover__title {{
        margin: 0;
        font: 700 28pt/1.1 "Times New Roman", Times, serif;
        letter-spacing: 0.04em;
        text-transform: uppercase;
      }}

      .cover__image-wrap {{
        width: 100%;
        border: 1px solid #cbcbcb;
        background: #e9eef5;
        padding: 3.5mm;
        display: flex;
        justify-content: center;
      }}

      .cover__image {{
        width: 100%;
        max-height: 125mm;
        object-fit: contain;
      }}

      .cover__building {{
        margin: 0;
        font: 700 16pt/1.35 "Times New Roman", Times, serif;
      }}

      .cover__date {{
        margin: 0;
        font: 700 13pt/1.2 "Times New Roman", Times, serif;
      }}

      .cover__spacer {{
        flex: 1 1 auto;
      }}

      .cover__logo-wrap {{
        width: 120mm;
        display: flex;
        justify-content: center;
      }}

      .cover__logo {{
        width: 100%;
        height: auto;
      }}

      .cover__logo-fallback {{
        margin: 0;
        font-weight: 700;
      }}

      .report {{
        page: report;
        break-before: page;
      }}

      .report-header {{
        position: running(report-header);
        border-bottom: 1px solid #1f1f1f;
        padding-bottom: 2.5mm;
        font: 11px/1.2 "Times New Roman", Times, serif;
      }}

      .report-header__logo-wrap {{
        margin-bottom: 1.2mm;
      }}

      .report-header__meta {{
      }}

      .report-header__row + .report-header__row {{
        margin-top: 0.4mm;
      }}

      .report-header__row {{
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        column-gap: 5mm;
        align-items: baseline;
      }}

      .report-header__logo {{
        width: 30mm;
        height: auto;
      }}

      .report-header__logo-fallback {{
        margin: 0;
        font-weight: 700;
      }}

      .report-header__line {{
        margin: 0;
        font-size: 11px;
      }}

      .report-header__line--title,
      .report-header__line--report {{
        font-weight: 700;
      }}

      .report-header__line--building,
      .report-header__line--page {{
        font-size: 11px;
      }}

      .report-header__line--building {{
        white-space: normal;
      }}

      .report-header__page-number::after {{
        content: counter(page);
      }}

      .section {{
        margin: 0 0 3mm;
      }}

      .chapter-heading {{
        margin: 5mm 0 4mm;
        padding-left: 3mm;
        border-left: 1mm solid #f7550a;
        font: 700 18pt/1.2 "Times New Roman", Times, serif;
        text-transform: uppercase;
      }}

      .chapter-heading--standalone {{
        margin-top: 8mm;
      }}

      .subsection-heading {{
        margin: 4mm 0 3mm;
        font: 700 13.5pt/1.2 "Times New Roman", Times, serif;
        break-after: avoid;
        page-break-after: avoid;
      }}

      .section__paragraph {{
        margin: 0 0 3mm;
        text-align: justify;
      }}

      .figure {{
        margin: 2.4mm 0 3mm;
        break-inside: avoid;
        page-break-inside: avoid;
      }}

      .figure__grid {{
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 2.4mm;
        align-items: start;
        break-inside: avoid;
        page-break-inside: avoid;
      }}

      .figure__grid + .figure__grid {{
        margin-top: 2.4mm;
      }}

      .figure__grid--single {{
        grid-template-columns: minmax(0, 1fr);
      }}

      .figure__grid--three {{
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }}

      .figure__grid--portrait-pair {{
        grid-template-columns: repeat(2, minmax(0, 60mm));
        justify-content: center;
        column-gap: 1.8mm;
      }}

      .figure__item {{
        break-inside: avoid;
        page-break-inside: avoid;
      }}

      .figure__img {{
        display: block;
        width: 100%;
        object-fit: contain;
      }}

      .figure__img--landscape {{
        height: 55mm;
      }}

      .figure__img--portrait {{
        height: 75mm;
      }}

      .figure__grid--three .figure__img--landscape {{
        height: 45mm;
      }}

      .figure__grid--three .figure__img--portrait {{
        height: 60mm;
      }}

      .figure__img--contain {{
        height: auto;
        max-height: 82mm;
      }}

      .figure__img--large {{
        width: 100%;
        max-height: 96mm;
      }}

      .figure__caption {{
        margin: 1.8mm 0 0;
        text-align: center;
        font: 700 10pt/1.2 "Times New Roman", Times, serif;
        break-inside: avoid;
        page-break-inside: avoid;
      }}

      .figure__missing {{
        margin: 0;
        text-align: center;
        font-style: italic;
      }}

      .signature {{
        margin-top: 12mm;
        border-top: 1px solid #1f1f1f;
        padding-top: 6mm;
      }}

      .signature__label,
      .signature__role {{
        margin: 0;
      }}

      .signature__name {{
        margin: 4mm 0 0;
        font-weight: 700;
      }}
    </style>
  </head>
  <body>
    <section class="cover">
      <h1 class="cover__title">MATERIAL TESTING WORKS</h1>
      <div class="cover__image-wrap">{self._cover_image_markup(cover_photo)}</div>
      <h2 class="cover__building">{building_name}<br />{building_location}</h2>
      <h3 class="cover__date">{testing_month}</h3>
      <div class="cover__spacer"></div>
      <div class="cover__logo-wrap">{cover_logo_markup}</div>
    </section>

    <section class="report">
      <header class="report-header">
        <div class="report-header__logo-wrap">
          {header_logo_markup}
        </div>
        <div class="report-header__meta">
          <div class="report-header__row">
            <p class="report-header__line report-header__line--title">Material Testing Works</p>
            <p class="report-header__line report-header__line--report">Activity Report</p>
          </div>
          <div class="report-header__row">
            <p class="report-header__line report-header__line--building">{building_name}</p>
            <p class="report-header__line report-header__line--page">
              Page <span class="report-header__page-number"></span>
            </p>
          </div>
        </div>
      </header>

      {report_body}

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
            return '<p class="figure__missing">No building photo uploaded.</p>'
        return f'<img class="cover__image" src="{image_uri}" alt="Building photo" />'

    def _chapter_heading(self, heading: str) -> str:
        return f'<h2 class="chapter-heading chapter-heading--standalone">{escape(heading)}</h2>'

    def _chapter_section(self, heading: str, body_markup: str) -> str:
        return f"""
<section class="section">
  <h2 class="chapter-heading">{escape(heading)}</h2>
  {body_markup}
</section>
"""

    def _subsection(self, heading: str, body_markup: str) -> str:
        return f"""
<section class="section">
  <h3 class="subsection-heading">{escape(heading)}</h3>
  {body_markup}
</section>
"""

    def _paragraph(self, markup: str) -> str:
        return f'<p class="section__paragraph">{markup}</p>'

    def _figure(
        self,
        caption: str,
        images: list[_ImageInfo],
        *,
        contain_images: bool = False,
        large: bool = False,
    ) -> str:
        if not images:
            return f"""
<section class="figure">
  <p class="figure__missing">No images uploaded for this figure.</p>
  <p class="figure__caption">{escape(caption)}</p>
</section>
"""

        if large:
            grids_markup = self._build_image_grid(
                images, caption, contain_images=contain_images, large=True
            )
        else:
            landscape = [img for img in images if img.is_landscape]
            portrait = [img for img in images if not img.is_landscape]
            grids_markup = ""
            if landscape:
                grids_markup += self._build_image_grid(
                    landscape, caption, contain_images=contain_images
                )
            if portrait:
                grids_markup += self._build_image_grid(
                    portrait, caption, contain_images=contain_images
                )

        return f"""
<section class="figure">
  {grids_markup}
  <p class="figure__caption">{escape(caption)}</p>
</section>
"""

    def _build_image_grid(
        self,
        images: list[_ImageInfo],
        caption: str,
        *,
        contain_images: bool = False,
        large: bool = False,
    ) -> str:
        grid_classes = ["figure__grid"]
        base_classes = ["figure__img"]

        all_portrait = all(not img.is_landscape for img in images)

        if large:
            base_classes.append("figure__img--large")
            grid_classes.append("figure__grid--single")
        elif len(images) == 1:
            grid_classes.append("figure__grid--single")
        elif len(images) == 2 or len(images) == 4:
            if all_portrait:
                grid_classes.append("figure__grid--portrait-pair")
        else:
            grid_classes.append("figure__grid--three")

        if contain_images:
            base_classes.append("figure__img--contain")

        base_class_markup = " ".join(base_classes)
        grid_class_markup = " ".join(grid_classes)
        items: list[str] = []
        for img in images:
            orientation = "figure__img--landscape" if img.is_landscape else "figure__img--portrait"
            cls = f"{base_class_markup} {orientation}"
            items.append(
                '<div class="figure__item">'
                f'<img class="{cls}" src="{img.uri}" alt="{escape(caption)}" />'
                "</div>"
            )
        return f'<div class="{grid_class_markup}">{"".join(items)}</div>'

    def _company_logo_uri(self) -> str | None:
        logo_path = Path(__file__).resolve().parents[2] / "frontend" / "public" / "asset-80.svg"
        if not logo_path.exists():
            return None
        return logo_path.resolve().as_uri()

    def _first_image_uri(self, session: ReportSession, group_name: PhotoGroupName) -> str | None:
        infos = self._all_image_info(session, group_name)
        if infos:
            return infos[0].uri
        return None

    def _all_image_info(
        self, session: ReportSession, group_name: PhotoGroupName
    ) -> list[_ImageInfo]:
        image_metadata = session.images.get(group_name.value, [])
        result: list[_ImageInfo] = []

        for image in image_metadata:
            image_path = (
                self._sessions_root
                / str(session.id)
                / "images"
                / group_name.value
                / image.stored_filename
            )
            if image_path.exists():
                result.append(
                    _ImageInfo(
                        uri=image_path.resolve().as_uri(),
                        is_landscape=image.width >= image.height,
                    )
                )

        return result


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


_UNITS = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
]
_TENS = [
    "",
    "",
    "twenty",
    "thirty",
    "forty",
    "fifty",
    "sixty",
    "seventy",
    "eighty",
    "ninety",
]


def _words_with_digits(value: int) -> str:
    return f"{_number_to_words(value)} ({value})"


def _number_to_words(value: int) -> str:
    if value < 20:
        return _UNITS[value]

    if value < 100:
        tens = _TENS[value // 10]
        remainder = value % 10
        if remainder == 0:
            return tens
        return f"{tens}-{_UNITS[remainder]}"

    if value < 1000:
        hundreds = f"{_UNITS[value // 100]} hundred"
        remainder = value % 100
        if remainder == 0:
            return hundreds
        return f"{hundreds} {_number_to_words(remainder)}"

    if value < 1_000_000:
        thousands = f"{_number_to_words(value // 1000)} thousand"
        remainder = value % 1000
        if remainder == 0:
            return thousands
        return f"{thousands} {_number_to_words(remainder)}"

    return str(value)
