from pathlib import Path
from uuid import uuid4

from io import BytesIO

import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter

from reportr.reporting import RendererNotReadyError, WeasyPrintActivityReportPdfRenderer
from reportr.storage import (
    AnnexDocumentMeta,
    AnnexGroupName,
    ImageMeta,
    PhotoGroupName,
    ReportSession,
)


def _build_form_fields_payload() -> dict[str, object]:
    return {
        "building_details": {
            "testing_date": "2026-02",
            "building_name": "Acacia Residences",
            "building_location": "Makati City",
            "number_of_storey": 12,
        },
        "superstructure": {
            "rebar_scanning": {"number_of_rebar_scan_locations": 3},
            "rebound_hammer_test": {"number_of_rebound_hammer_test_locations": 4},
            "concrete_core_extraction": {"number_of_coring_locations": 2},
            "rebar_extraction": {"number_of_rebar_samples_extracted": 2},
            "restoration_works": {
                "non_shrink_grout_product_used": "SikaGrout 214",
                "epoxy_ab_used": "Sikadur-31",
            },
        },
        "substructure": {
            "concrete_core_extraction": {
                "number_of_foundation_locations": 3,
                "number_of_foundation_cores_extracted": 3,
            }
        },
        "signature": {
            "prepared_by": "Jane Dela Cruz",
            "prepared_by_role": "Structural Engineer",
        },
    }


def _create_test_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (300, 220), color=(10, 80, 200))
    image.save(path, format="JPEG")


def _build_pdf_bytes(*, page_count: int) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=595, height=842)

    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_renderer_uses_file_uris_and_dynamic_content(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, str] = {}

    class FakeHTML:
        def __init__(self, *, string: str, base_url: str) -> None:
            captured["string"] = string
            captured["base_url"] = base_url

        def write_pdf(self) -> bytes:
            return b"%PDF-1.7\nfake"

    import reportr.reporting.activity_report_pdf_renderer as renderer_module

    monkeypatch.setattr(renderer_module, "HTML", FakeHTML)

    session_id = uuid4()
    image_path = (
        tmp_path
        / str(session_id)
        / "images"
        / PhotoGroupName.BUILDING_DETAILS_BUILDING_PHOTO.value
        / "cover.jpg"
    )
    _create_test_image(image_path)

    session = ReportSession.model_validate(
        {
            "id": str(session_id),
            "form_fields": _build_form_fields_payload(),
            "images": {
                PhotoGroupName.BUILDING_DETAILS_BUILDING_PHOTO.value: [
                    ImageMeta(
                        id=uuid4(),
                        group_name=PhotoGroupName.BUILDING_DETAILS_BUILDING_PHOTO,
                        original_filename="cover.jpg",
                        stored_filename="cover.jpg",
                        size_bytes=image_path.stat().st_size,
                        width=300,
                        height=220,
                    )
                ]
            },
        }
    )

    renderer = WeasyPrintActivityReportPdfRenderer(sessions_root=tmp_path)
    output = renderer.render(session)

    assert output.startswith(b"%PDF-1.7")
    assert "MATERIAL TESTING WORKS" in captured["string"]
    assert "A. INTRODUCTION" in captured["string"]
    assert "Figure B.3.2 Extracted Core Samples" in captured["string"]
    assert "figure__img--contain" in captured["string"]
    assert "FEBRUARY 2026" in captured["string"]
    assert image_path.resolve().as_uri() in captured["string"]
    assert captured["base_url"] == tmp_path.resolve().as_uri()


def test_renderer_appends_annex_cover_and_uploaded_pdf(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured_strings: list[str] = []

    class FakeHTML:
        def __init__(self, *, string: str, base_url: str) -> None:
            _ = base_url
            captured_strings.append(string)

        def write_pdf(self) -> bytes:
            return _build_pdf_bytes(page_count=1)

    import reportr.reporting.activity_report_pdf_renderer as renderer_module

    monkeypatch.setattr(renderer_module, "HTML", FakeHTML)

    session_id = uuid4()
    annex_path = (
        tmp_path
        / str(session_id)
        / "annexes"
        / AnnexGroupName.REBAR_SCANNING_OUTPUT.value
        / "annex-i.pdf"
    )
    annex_path.parent.mkdir(parents=True, exist_ok=True)
    annex_path.write_bytes(_build_pdf_bytes(page_count=2))

    session = ReportSession.model_validate(
        {
            "id": str(session_id),
            "form_fields": _build_form_fields_payload(),
            "annex_documents": {
                AnnexGroupName.REBAR_SCANNING_OUTPUT.value: AnnexDocumentMeta(
                    id=uuid4(),
                    group_name=AnnexGroupName.REBAR_SCANNING_OUTPUT,
                    original_filename="annex-i.pdf",
                    stored_filename="annex-i.pdf",
                    size_bytes=annex_path.stat().st_size,
                )
            },
        }
    )

    renderer = WeasyPrintActivityReportPdfRenderer(sessions_root=tmp_path)
    output = renderer.render(session)

    merged_reader = PdfReader(BytesIO(output))
    assert len(merged_reader.pages) == 4

    annex_cover_markup = next(html for html in captured_strings if "ANNEX I" in html)
    assert "Activity Report" not in annex_cover_markup
    assert "Page <span" not in annex_cover_markup


def test_renderer_requires_form_fields(tmp_path: Path) -> None:
    renderer = WeasyPrintActivityReportPdfRenderer(sessions_root=tmp_path)
    session = ReportSession(id=uuid4())

    with pytest.raises(RendererNotReadyError):
        renderer.render(session)


def test_renderer_incomplete_skips_empty_subsections(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, str] = {}

    class FakeHTML:
        def __init__(self, *, string: str, base_url: str) -> None:
            _ = base_url
            captured["string"] = string

        def write_pdf(self) -> bytes:
            return b"%PDF-1.7\nfake"

    import reportr.reporting.activity_report_pdf_renderer as renderer_module

    monkeypatch.setattr(renderer_module, "HTML", FakeHTML)

    session_id = uuid4()

    # Only create images for rebar scanning (B) and rebar scanning for foundation (C)
    rebar_scan_image_path = (
        tmp_path
        / str(session_id)
        / "images"
        / PhotoGroupName.SUPERSTRUCTURE_REBAR_SCANNING_PHOTOS.value
        / "scan.jpg"
    )
    _create_test_image(rebar_scan_image_path)

    sub_rebar_scan_image_path = (
        tmp_path
        / str(session_id)
        / "images"
        / PhotoGroupName.SUBSTRUCTURE_REBAR_SCANNING_FOR_FOUNDATION_PHOTOS.value
        / "foundation.jpg"
    )
    _create_test_image(sub_rebar_scan_image_path)

    session = ReportSession.model_validate(
        {
            "id": str(session_id),
            "form_fields": _build_form_fields_payload(),
            "images": {
                PhotoGroupName.SUPERSTRUCTURE_REBAR_SCANNING_PHOTOS.value: [
                    ImageMeta(
                        id=uuid4(),
                        group_name=PhotoGroupName.SUPERSTRUCTURE_REBAR_SCANNING_PHOTOS,
                        original_filename="scan.jpg",
                        stored_filename="scan.jpg",
                        size_bytes=rebar_scan_image_path.stat().st_size,
                        width=300,
                        height=220,
                    )
                ],
                PhotoGroupName.SUBSTRUCTURE_REBAR_SCANNING_FOR_FOUNDATION_PHOTOS.value: [
                    ImageMeta(
                        id=uuid4(),
                        group_name=PhotoGroupName.SUBSTRUCTURE_REBAR_SCANNING_FOR_FOUNDATION_PHOTOS,
                        original_filename="foundation.jpg",
                        stored_filename="foundation.jpg",
                        size_bytes=sub_rebar_scan_image_path.stat().st_size,
                        width=300,
                        height=220,
                    )
                ],
            },
        }
    )

    renderer = WeasyPrintActivityReportPdfRenderer(sessions_root=tmp_path)
    renderer.render(session, allow_incomplete=True)

    html = captured["string"]

    # B: Only rebar scanning has photos → it becomes B.1
    assert "B.1. Rebar Scanning" in html
    assert "Figure B.1. REBAR SCANNING" in html

    # Other B subsections should be absent entirely
    assert "Rebound Hammer Test" not in html
    assert "Concrete Core Extraction" not in html
    assert "Rebar Extraction" not in html
    assert "Chipping of Existing Slab" not in html
    assert "Restoration Works" not in html

    # B.2 through B.6 labels should not appear
    assert "B.2." not in html

    # C: Only rebar scanning for foundation has photos → it becomes C.1
    assert "C.1. Rebar Scanning" in html
    assert "Figure C.1. Rebar Scanning for Foundation" in html

    # Other C subsections should be absent
    assert "Backfilling" not in html
    assert "C.2." not in html


def test_renderer_incomplete_no_photos_omits_chapters(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, str] = {}

    class FakeHTML:
        def __init__(self, *, string: str, base_url: str) -> None:
            _ = base_url
            captured["string"] = string

        def write_pdf(self) -> bytes:
            return b"%PDF-1.7\nfake"

    import reportr.reporting.activity_report_pdf_renderer as renderer_module

    monkeypatch.setattr(renderer_module, "HTML", FakeHTML)

    session = ReportSession.model_validate(
        {
            "id": str(uuid4()),
            "form_fields": _build_form_fields_payload(),
        }
    )

    renderer = WeasyPrintActivityReportPdfRenderer(sessions_root=tmp_path)
    renderer.render(session, allow_incomplete=True)

    html = captured["string"]

    # Introduction should still appear
    assert "A. INTRODUCTION" in html

    # Chapters with no subsections should be entirely absent
    assert "DATA GATHERING FOR SUPERSTRUCTURE" not in html
    assert "DATA GATHERING FOR SUBSTRUCTURE" not in html
