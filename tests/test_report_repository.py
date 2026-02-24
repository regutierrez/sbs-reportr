from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from reportr.storage import (
    FileSystemReportRepository,
    PhotoGroupName,
    ReportFormFields,
    ReportStatus,
    SessionNotFoundError,
)


def build_form_fields() -> ReportFormFields:
    return ReportFormFields.model_validate(
        {
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
    )


def make_repository(tmp_path: Path) -> FileSystemReportRepository:
    return FileSystemReportRepository(
        sessions_root=tmp_path / "sessions",
        reports_root=tmp_path / "reports",
    )


def test_create_session_persists_metadata(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)

    created = repository.create_session()
    loaded = repository.get_session(created.id)

    assert loaded is not None
    assert loaded.id == created.id
    assert loaded.status == ReportStatus.DRAFT
    assert loaded.form_fields is None
    assert loaded.images == {}


def test_save_form_fields_updates_existing_session(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    session = repository.create_session()
    form_fields = build_form_fields()

    updated = repository.save_form_fields(session.id, form_fields)
    loaded = repository.get_session(session.id)

    assert updated.form_fields == form_fields
    assert loaded is not None
    assert loaded.form_fields == form_fields


def test_save_image_writes_file_and_records_metadata(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    session = repository.create_session()

    image = repository.save_image(
        session.id,
        group_name=PhotoGroupName.BUILDING_DETAILS_BUILDING_PHOTO,
        source=BytesIO(b"compressed image bytes"),
        original_filename="building.JPG",
        size_bytes=22,
        width=1000,
        height=750,
    )
    loaded = repository.get_session(session.id)

    assert image.group_name == PhotoGroupName.BUILDING_DETAILS_BUILDING_PHOTO
    assert image.stored_filename.endswith(".jpg")
    assert loaded is not None
    assert loaded.images[PhotoGroupName.BUILDING_DETAILS_BUILDING_PHOTO.value][0] == image

    stored_path = (
        tmp_path
        / "sessions"
        / str(session.id)
        / "images"
        / PhotoGroupName.BUILDING_DETAILS_BUILDING_PHOTO.value
        / image.stored_filename
    )
    assert stored_path.read_bytes() == b"compressed image bytes"


def test_persist_generated_pdf_writes_output_and_updates_status(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    session = repository.create_session()

    report_path = repository.persist_generated_pdf(session.id, b"%PDF-1.7")
    loaded = repository.get_session(session.id)

    assert report_path == tmp_path / "reports" / str(session.id) / "report.pdf"
    assert report_path.read_bytes() == b"%PDF-1.7"
    assert loaded is not None
    assert loaded.status == ReportStatus.COMPLETED
    assert loaded.generated_pdf_path == report_path.as_posix()


def test_set_status_updates_session_status(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    session = repository.create_session()

    updated = repository.set_status(session.id, ReportStatus.GENERATING)

    assert updated.status == ReportStatus.GENERATING


def test_missing_session_raises_for_mutations(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    missing_session_id = uuid4()

    with pytest.raises(SessionNotFoundError) as save_fields_error:
        repository.save_form_fields(missing_session_id, build_form_fields())
    with pytest.raises(SessionNotFoundError) as save_image_error:
        repository.save_image(
            missing_session_id,
            group_name=PhotoGroupName.BUILDING_DETAILS_BUILDING_PHOTO,
            source=BytesIO(b"x"),
            original_filename="photo.jpg",
            size_bytes=1,
            width=1,
            height=1,
        )
    with pytest.raises(SessionNotFoundError) as persist_pdf_error:
        repository.persist_generated_pdf(missing_session_id, b"pdf")

    assert save_fields_error.value.session_id == missing_session_id
    assert save_image_error.value.session_id == missing_session_id
    assert persist_pdf_error.value.session_id == missing_session_id


def test_get_session_returns_none_when_missing(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)

    missing = repository.get_session(UUID("11111111-1111-4111-8111-111111111111"))

    assert missing is None
