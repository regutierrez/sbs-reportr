from io import BytesIO
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from PIL import Image

from reportr.app.web_api import create_app
from reportr.storage import FileSystemReportRepository, PhotoGroupName, ReportSession, ReportStatus


class StubRenderer:
    def __init__(self, output: bytes = b"%PDF-1.7\nphase-3") -> None:
        self.output = output
        self.render_call_count = 0

    def render(self, session: ReportSession) -> bytes:
        _ = session
        self.render_call_count += 1
        return self.output


def build_form_payload() -> dict[str, object]:
    return {
        "building_details": {
            "testing_date": "2026-02",
            "building_name": "Acacia Residences",
            "building_location": "Makati City",
            "number_of_storey": 12,
        },
        "superstructure": {
            "rebar_scanning": {
                "number_of_rebar_scan_locations": 3,
            },
            "rebound_hammer_test": {
                "number_of_rebound_hammer_test_locations": 4,
            },
            "concrete_core_extraction": {
                "number_of_coring_locations": 2,
            },
            "rebar_extraction": {
                "number_of_rebar_samples_extracted": 2,
            },
            "restoration_works": {
                "non_shrink_grout_product_used": "SikaGrout 214",
                "epoxy_ab_used": "Sikadur-31",
            },
        },
        "substructure": {
            "concrete_core_extraction": {
                "number_of_foundation_locations": 3,
                "number_of_foundation_cores_extracted": 3,
            },
        },
        "signature": {
            "prepared_by": "Jane Dela Cruz",
            "prepared_by_role": "Structural Engineer",
        },
    }


def build_png_bytes(*, width: int = 320, height: int = 240) -> bytes:
    image = Image.new("RGB", (width, height), color=(0, 81, 255))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def make_client(
    tmp_path: Path,
    *,
    renderer: StubRenderer | None = None,
) -> tuple[TestClient, FileSystemReportRepository]:
    repository = FileSystemReportRepository(
        sessions_root=tmp_path / "sessions",
        reports_root=tmp_path / "reports",
    )
    app = create_app(repository=repository, renderer=renderer, cleanup_interval_seconds=0)
    return TestClient(app), repository


def create_complete_session(client: TestClient) -> UUID:
    create_response = client.post("/reports")
    session_id = UUID(create_response.json()["session_id"])

    form_response = client.put(f"/reports/{session_id}", json=build_form_payload())
    assert form_response.status_code == 200

    image_bytes = build_png_bytes()
    for group_name in PhotoGroupName:
        upload_response = client.post(
            f"/reports/{session_id}/images/{group_name.value}",
            files={"image": ("photo.png", image_bytes, "image/png")},
        )
        assert upload_response.status_code == 201

    return session_id


def test_create_report_session_returns_new_session(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)

    response = client.post("/reports")

    assert response.status_code == 201
    response_payload = response.json()
    assert UUID(response_payload["session_id"])
    assert response_payload["status"] == ReportStatus.DRAFT


def test_update_form_fields_returns_updated_session(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    create_response = client.post("/reports")
    session_id = create_response.json()["session_id"]

    response = client.put(f"/reports/{session_id}", json=build_form_payload())

    assert response.status_code == 200
    response_payload = response.json()
    assert response_payload["id"] == session_id
    assert (
        response_payload["form_fields"]["building_details"]["building_name"] == "Acacia Residences"
    )


def test_upload_image_saves_metadata(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    create_response = client.post("/reports")
    session_id = create_response.json()["session_id"]

    response = client.post(
        f"/reports/{session_id}/images/{PhotoGroupName.BUILDING_DETAILS_BUILDING_PHOTO.value}",
        files={"image": ("building.png", build_png_bytes(), "image/png")},
    )

    assert response.status_code == 201
    response_payload = response.json()["image"]
    assert response_payload["group_name"] == PhotoGroupName.BUILDING_DETAILS_BUILDING_PHOTO.value
    assert response_payload["width"] == 320
    assert response_payload["height"] == 240


def test_upload_image_rejects_unsupported_mime_type(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    create_response = client.post("/reports")
    session_id = create_response.json()["session_id"]

    response = client.post(
        f"/reports/{session_id}/images/{PhotoGroupName.BUILDING_DETAILS_BUILDING_PHOTO.value}",
        files={"image": ("notes.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 415


def test_upload_image_rejects_oversized_dimensions(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    create_response = client.post("/reports")
    session_id = create_response.json()["session_id"]

    response = client.post(
        f"/reports/{session_id}/images/{PhotoGroupName.BUILDING_DETAILS_BUILDING_PHOTO.value}",
        files={"image": ("building.png", build_png_bytes(width=1301, height=500), "image/png")},
    )

    assert response.status_code == 422


def test_upload_image_rejects_when_group_hits_max_limit(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    create_response = client.post("/reports")
    session_id = create_response.json()["session_id"]
    image_bytes = build_png_bytes()

    first_upload = client.post(
        f"/reports/{session_id}/images/{PhotoGroupName.BUILDING_DETAILS_BUILDING_PHOTO.value}",
        files={"image": ("building.png", image_bytes, "image/png")},
    )
    second_upload = client.post(
        f"/reports/{session_id}/images/{PhotoGroupName.BUILDING_DETAILS_BUILDING_PHOTO.value}",
        files={"image": ("building.png", image_bytes, "image/png")},
    )

    assert first_upload.status_code == 201
    assert second_upload.status_code == 409


def test_generate_report_rejects_incomplete_session(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    create_response = client.post("/reports")
    session_id = create_response.json()["session_id"]

    response = client.post(f"/reports/{session_id}/generate")

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["missing"]["form_fields"] is True
    assert PhotoGroupName.BUILDING_DETAILS_BUILDING_PHOTO.value in detail["missing"]["photo_groups"]


def test_download_report_returns_not_found_when_not_generated(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    session_id = create_complete_session(client)

    response = client.get(f"/reports/{session_id}/download")

    assert response.status_code == 404


def test_generate_report_persists_pdf_after_validation(tmp_path: Path) -> None:
    renderer = StubRenderer(output=b"%PDF-1.7\nrendered")
    client, repository = make_client(tmp_path, renderer=renderer)
    session_id = create_complete_session(client)

    response = client.post(f"/reports/{session_id}/generate")

    assert response.status_code == 200
    response_payload = response.json()
    assert response_payload["session_id"] == str(session_id)
    assert response_payload["download_url"] == f"/reports/{session_id}/download"

    stored_session = repository.get_session(session_id)
    assert stored_session is not None
    assert stored_session.status == ReportStatus.COMPLETED
    assert stored_session.generated_pdf_path is not None
    assert Path(stored_session.generated_pdf_path).read_bytes() == b"%PDF-1.7\nrendered"
    assert renderer.render_call_count == 1

    images_root = tmp_path / "sessions" / str(session_id) / "images"
    assert not images_root.exists()

    first_download = client.get(f"/reports/{session_id}/download")
    second_download = client.get(f"/reports/{session_id}/download")

    assert first_download.status_code == 200
    assert second_download.status_code == 200
    assert first_download.content == b"%PDF-1.7\nrendered"
    assert second_download.content == b"%PDF-1.7\nrendered"

    content_disposition = first_download.headers.get("content-disposition")
    assert content_disposition is not None
    assert "acacia-residences-activity-report.pdf" in content_disposition


def test_generate_report_returns_existing_download_when_already_completed(tmp_path: Path) -> None:
    renderer = StubRenderer(output=b"%PDF-1.7\nrendered")
    client, repository = make_client(tmp_path, renderer=renderer)
    session_id = create_complete_session(client)

    first_response = client.post(f"/reports/{session_id}/generate")
    second_response = client.post(f"/reports/{session_id}/generate")

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    assert first_response.json()["download_url"] == f"/reports/{session_id}/download"
    assert second_response.json()["download_url"] == f"/reports/{session_id}/download"

    stored_session = repository.get_session(session_id)
    assert stored_session is not None
    assert stored_session.generated_pdf_path is not None
    assert Path(stored_session.generated_pdf_path).read_bytes() == b"%PDF-1.7\nrendered"
    assert renderer.render_call_count == 1


def test_generate_report_returns_existing_download_when_pdf_exists_but_status_is_not_completed(
    tmp_path: Path,
) -> None:
    renderer = StubRenderer(output=b"%PDF-1.7\nrendered")
    client, repository = make_client(tmp_path, renderer=renderer)
    session_id = create_complete_session(client)

    generate_response = client.post(f"/reports/{session_id}/generate")
    assert generate_response.status_code == 200

    repository.set_status(session_id, ReportStatus.DRAFT)

    regenerate_response = client.post(f"/reports/{session_id}/generate")

    assert regenerate_response.status_code == 200
    assert regenerate_response.json()["download_url"] == f"/reports/{session_id}/download"
    assert renderer.render_call_count == 1

    refreshed_session = repository.get_session(session_id)
    assert refreshed_session is not None
    assert refreshed_session.status == ReportStatus.COMPLETED


def test_generate_report_returns_conflict_when_generation_is_already_in_progress(
    tmp_path: Path,
) -> None:
    renderer = StubRenderer(output=b"%PDF-1.7\nrendered")
    client, repository = make_client(tmp_path, renderer=renderer)
    session_id = create_complete_session(client)

    repository.set_status(session_id, ReportStatus.GENERATING)

    response = client.post(f"/reports/{session_id}/generate")

    assert response.status_code == 409
    assert response.json()["detail"] == "Report generation is already in progress."
    assert renderer.render_call_count == 0


def test_generate_report_returns_conflict_when_completed_pdf_is_missing(tmp_path: Path) -> None:
    renderer = StubRenderer(output=b"%PDF-1.7\nrendered")
    client, repository = make_client(tmp_path, renderer=renderer)
    session_id = create_complete_session(client)

    generate_response = client.post(f"/reports/{session_id}/generate")
    assert generate_response.status_code == 200

    generated_pdf_path = repository.get_generated_pdf_path(session_id)
    assert generated_pdf_path is not None
    generated_pdf_path.unlink()

    regenerate_response = client.post(f"/reports/{session_id}/generate")

    assert regenerate_response.status_code == 409
    assert regenerate_response.json()["detail"] == (
        "Report was already generated, but the generated PDF is no longer available."
    )
    assert renderer.render_call_count == 1
