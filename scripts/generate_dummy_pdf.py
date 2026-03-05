import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image
from pypdf import PdfWriter

# Add the src directory to the python path so we can import reportr modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reportr.reporting.activity_report_pdf_renderer import WeasyPrintActivityReportPdfRenderer
from reportr.storage.models import (
    PHOTO_GROUP_LIMITS,
    AnnexDocumentMeta,
    AnnexGroupName,
    BuildingDetailsFormFields,
    ImageMeta,
    PhotoGroupName,
    ReportFormFields,
    ReportSession,
    ReportStatus,
    SignatureFormFields,
    SubstructureConcreteCoreExtractionFormFields,
    SubstructureFormFields,
    SuperstructureConcreteCoreExtractionFormFields,
    SuperstructureFormFields,
    SuperstructureRebarExtractionFormFields,
    SuperstructureRebarScanningFormFields,
    SuperstructureReboundHammerTestFormFields,
    SuperstructureRestorationWorksFormFields,
)

DUMMY_ROOT = Path("/tmp/reportr/dummy")

PageSize = tuple[float, float]
A4_PORTRAIT: PageSize = (595.0, 842.0)
A4_LANDSCAPE: PageSize = (842.0, 595.0)
LETTER_PORTRAIT: PageSize = (612.0, 792.0)
LETTER_LANDSCAPE: PageSize = (792.0, 612.0)

ANNEX_PAGE_LAYOUTS: dict[AnnexGroupName, tuple[PageSize, ...]] = {
    AnnexGroupName.REBAR_SCANNING_OUTPUT: (A4_LANDSCAPE,),
    AnnexGroupName.REBOUND_NUMBER_TEST_RESULTS: (A4_PORTRAIT,),
    AnnexGroupName.COMPRESSIVE_STRENGTH_TEST_RESULTS_SUPERSTRUCTURE: (
        A4_PORTRAIT,
        A4_LANDSCAPE,
    ),
    AnnexGroupName.TENSILE_STRENGTH_TEST_RESULTS: (LETTER_LANDSCAPE,),
    AnnexGroupName.COMPRESSIVE_STRENGTH_TEST_RESULTS_SUBSTRUCTURE: (
        LETTER_PORTRAIT,
        A4_PORTRAIT,
    ),
    AnnexGroupName.REBAR_SCANNING_RESULTS_FOR_FOUNDATION: (
        A4_LANDSCAPE,
        LETTER_LANDSCAPE,
    ),
    AnnexGroupName.MATERIAL_TESTS_MAPPING: (
        A4_PORTRAIT,
        A4_LANDSCAPE,
        A4_PORTRAIT,
    ),
}


def copy_dummy_images(session_id: uuid.UUID, sessions_root: Path) -> dict[str, list[ImageMeta]]:
    """Copy extracted images into the session folder to simulate uploaded photos."""
    import glob
    import shutil

    extracted_dir = Path("extracted_images")
    if not extracted_dir.exists():
        print("extracted_images directory not found. Please run extract_images.py first.")
        return {}

    session_images_dir = sessions_root / str(session_id) / "images"
    os.makedirs(session_images_dir, exist_ok=True)

    # Map PhotoGroupNames to patterns from our extracted images
    mappings = {
        PhotoGroupName.BUILDING_DETAILS_BUILDING_PHOTO: "A. INTRODUCTION*.jpeg",
        PhotoGroupName.SUPERSTRUCTURE_REBAR_SCANNING_PHOTOS: "*B.1. Rebar Scanning*.jpeg",
        PhotoGroupName.SUPERSTRUCTURE_REBOUND_HAMMER_TEST_PHOTOS: "*B.2. Rebound Hammer Test*.jpeg",
        PhotoGroupName.SUPERSTRUCTURE_CONCRETE_CORING_PHOTOS: "*B.3. Concrete Core Extraction*.jpeg",
        # Just use some coring photos for family pic if we don't have specific ones
        PhotoGroupName.SUPERSTRUCTURE_CORE_SAMPLES_FAMILY_PIC: "*B.3. Concrete Core Extraction - 1*.jpeg",
        PhotoGroupName.SUPERSTRUCTURE_REBAR_EXTRACTION_PHOTOS: "*B.4. Rebar Extraction*.jpeg",
        PhotoGroupName.SUPERSTRUCTURE_REBAR_SAMPLES_FAMILY_PIC: "*B.4. Rebar Extraction - 1*.jpeg",
        PhotoGroupName.SUPERSTRUCTURE_CHIPPING_OF_SLAB_PHOTOS: "*B.5. Chipping of Existing Slab*.jpeg",
        PhotoGroupName.SUPERSTRUCTURE_RESTORATION_PHOTOS: "*B.6. Restoration Works*.jpeg",
        PhotoGroupName.SUBSTRUCTURE_CORING_FOR_FOUNDATION_PHOTOS: "*C.1. Concrete Core Extraction*.jpeg",
        PhotoGroupName.SUBSTRUCTURE_REBAR_SCANNING_FOR_FOUNDATION_PHOTOS: "*C.2. Rebar Scanning*.jpeg",
        PhotoGroupName.SUBSTRUCTURE_RESTORATION_BACKFILLING_COMPACTION_PHOTOS: "*C.3. Restoration*.jpeg",
    }

    images_metadata: dict[str, list[ImageMeta]] = {}

    for group_name, pattern in mappings.items():
        group_dir = session_images_dir / group_name.value
        os.makedirs(group_dir, exist_ok=True)

        if group_name == PhotoGroupName.SUPERSTRUCTURE_REBAR_SCANNING_PHOTOS:
            candidate_files = [
                extracted_dir
                / "C. DATA GATHERING FOR SUBSTRUCTURE - C.3. Restoration for Coring Works, Backfilling, and Compaction - 4.jpeg",
                extracted_dir
                / "C. DATA GATHERING FOR SUBSTRUCTURE - C.3. Restoration for Coring Works, Backfilling, and Compaction - 5.jpeg",
                extracted_dir
                / "C. DATA GATHERING FOR SUBSTRUCTURE - C.3. Restoration for Coring Works, Backfilling, and Compaction - 6.jpeg",
                extracted_dir
                / "B. DATA GATHERING FOR SUPERSTRUCTURE - B.1. Rebar Scanning - 1.jpeg",
                extracted_dir
                / "B. DATA GATHERING FOR SUPERSTRUCTURE - B.1. Rebar Scanning - 2.jpeg",
            ]
            matched_files = [str(path) for path in candidate_files if path.exists()]
        else:
            matched_files = glob.glob(str(extracted_dir / pattern))

        # Limit the number of photos to the maximum defined by the model
        _, max_images = PHOTO_GROUP_LIMITS.get(group_name, (1, 4))

        group_metadata: list[ImageMeta] = []
        for i, filepath in enumerate(matched_files):
            if i >= max_images:
                break

            src = Path(filepath)
            if not src.exists():
                continue

            dest_filename = f"{uuid.uuid4()}.jpeg"
            dest = group_dir / dest_filename
            shutil.copy2(src, dest)

            with Image.open(src) as img:
                width, height = img.size

            img_id = uuid.uuid4()
            group_metadata.append(
                ImageMeta(
                    id=img_id,
                    group_name=group_name,
                    original_filename=src.name,
                    stored_filename=dest_filename,
                    size_bytes=src.stat().st_size,
                    width=width,
                    height=height,
                )
            )

        if group_metadata:
            images_metadata[group_name.value] = group_metadata

    return images_metadata


def _page_orientation(width: float, height: float) -> str:
    if width > height:
        return "landscape"
    if height > width:
        return "portrait"
    return "square"


def _write_dummy_pdf(path: Path, page_sizes: tuple[PageSize, ...]) -> None:
    writer = PdfWriter()
    for width, height in page_sizes:
        writer.add_blank_page(width=width, height=height)

    with path.open("wb") as output_file:
        writer.write(output_file)


def create_dummy_annex_documents(
    session_id: uuid.UUID, sessions_root: Path
) -> dict[str, AnnexDocumentMeta]:
    """Create one annex PDF per group with varied page orientations."""
    annex_documents: dict[str, AnnexDocumentMeta] = {}
    session_annexes_dir = sessions_root / str(session_id) / "annexes"
    os.makedirs(session_annexes_dir, exist_ok=True)

    for group_name, page_sizes in ANNEX_PAGE_LAYOUTS.items():
        group_dir = session_annexes_dir / group_name.value
        os.makedirs(group_dir, exist_ok=True)

        document_id = uuid.uuid4()
        stored_filename = f"{document_id}.pdf"
        annex_path = group_dir / stored_filename

        _write_dummy_pdf(annex_path, page_sizes)

        orientations = ", ".join(_page_orientation(width, height) for width, height in page_sizes)
        print(f"Created annex {group_name.value}: {stored_filename} ({orientations})")

        annex_documents[group_name.value] = AnnexDocumentMeta(
            id=document_id,
            group_name=group_name,
            original_filename=f"{group_name.value}.pdf",
            stored_filename=stored_filename,
            size_bytes=annex_path.stat().st_size,
        )

    return annex_documents


def create_dummy_session() -> tuple[ReportSession, Path]:
    # Setup directories
    sessions_root = DUMMY_ROOT / "sessions"
    session_id = uuid.uuid4()
    os.makedirs(sessions_root / str(session_id), exist_ok=True)

    images_metadata = copy_dummy_images(session_id, sessions_root)
    annex_documents = create_dummy_annex_documents(session_id, sessions_root)

    # Create mock form fields
    form_fields = ReportFormFields(
        building_details=BuildingDetailsFormFields(
            building_name="Kapitan Eddie T. Reyes Integrated School - Phase 2",
            building_location="Brgy. Pinagsama, Taguig City",
            testing_date="2023-10",
            number_of_storey=3,
        ),
        superstructure=SuperstructureFormFields(
            rebar_scanning=SuperstructureRebarScanningFormFields(number_of_rebar_scan_locations=11),
            rebound_hammer_test=SuperstructureReboundHammerTestFormFields(
                number_of_rebound_hammer_test_locations=18
            ),
            concrete_core_extraction=SuperstructureConcreteCoreExtractionFormFields(
                number_of_coring_locations=8
            ),
            rebar_extraction=SuperstructureRebarExtractionFormFields(
                number_of_rebar_samples_extracted=5
            ),
            restoration_works=SuperstructureRestorationWorksFormFields(
                non_shrink_grout_product_used="SikaGrout 214-11", epoxy_ab_used="Sikadur-732"
            ),
        ),
        substructure=SubstructureFormFields(
            concrete_core_extraction=SubstructureConcreteCoreExtractionFormFields(
                number_of_foundation_locations=3, number_of_foundation_cores_extracted=3
            )
        ),
        signature=SignatureFormFields(
            prepared_by="Juan Dela Cruz", prepared_by_role="Materials Engineer"
        ),
    )

    session = ReportSession(
        id=session_id,
        created_at=datetime.now(timezone.utc),
        status=ReportStatus.DRAFT,
        form_fields=form_fields,
        images=images_metadata,
        annex_documents=annex_documents,
    )

    return session, sessions_root


def main() -> None:
    print("Setting up dummy session and copying images...")
    session, sessions_root = create_dummy_session()

    print("Initializing PDF renderer...")
    renderer = WeasyPrintActivityReportPdfRenderer(sessions_root=sessions_root)

    output_pdf = DUMMY_ROOT / "dummy_report.pdf"
    print(f"Rendering merged report + annexes PDF to {output_pdf}...")

    try:
        pdf_bytes = renderer.render(session)
        output_pdf.write_bytes(pdf_bytes)
        print(f"Success! Created {output_pdf}")
        print(f"Session fixtures created under {(sessions_root / str(session.id)).resolve()}")
    except Exception as e:
        print(f"Error rendering PDF: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
