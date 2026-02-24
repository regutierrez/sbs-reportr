from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image

from reportr.reporting import RendererNotReadyError, WeasyPrintActivityReportPdfRenderer
from reportr.storage import ImageMeta, PhotoGroupName, ReportSession


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


def test_renderer_requires_form_fields(tmp_path: Path) -> None:
    renderer = WeasyPrintActivityReportPdfRenderer(sessions_root=tmp_path)
    session = ReportSession(id=uuid4())

    with pytest.raises(RendererNotReadyError):
        renderer.render(session)
