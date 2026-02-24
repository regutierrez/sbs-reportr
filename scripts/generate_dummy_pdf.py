import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image

# Add the src directory to the python path so we can import reportr modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reportr.storage.models import (
    ReportSession,
    ReportFormFields,
    BuildingDetailsFormFields,
    SuperstructureFormFields,
    SubstructureFormFields,
    SignatureFormFields,
    SuperstructureRebarScanningFormFields,
    SuperstructureReboundHammerTestFormFields,
    SuperstructureConcreteCoreExtractionFormFields,
    SuperstructureRebarExtractionFormFields,
    SuperstructureRestorationWorksFormFields,
    SubstructureConcreteCoreExtractionFormFields,
    PhotoGroupName,
    ImageMeta,
    ReportStatus,
)
from reportr.reporting.activity_report_pdf_renderer import WeasyPrintActivityReportPdfRenderer


def copy_dummy_images(session_id: uuid.UUID, sessions_root: Path):
    """Copy extracted images into the session folder to simulate uploaded photos."""
    import shutil
    import glob

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

    images_metadata = {}

    for group_name, pattern in mappings.items():
        group_dir = session_images_dir / group_name.value
        os.makedirs(group_dir, exist_ok=True)

        matched_files = glob.glob(str(extracted_dir / pattern))

        group_metadata = []
        for i, filepath in enumerate(matched_files):
            # We'll just take up to 4 images per group to keep the PDF a reasonable size
            if i >= 4:
                break

            src = Path(filepath)
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


def create_dummy_session():
    # Setup directories
    sessions_root = Path("data/dummy_sessions")
    session_id = uuid.uuid4()
    os.makedirs(sessions_root / str(session_id), exist_ok=True)

    images_metadata = copy_dummy_images(session_id, sessions_root)

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
    )

    return session, sessions_root


def main():
    print("Setting up dummy session and copying images...")
    session, sessions_root = create_dummy_session()

    print("Initializing PDF Renderer...")
    renderer = WeasyPrintActivityReportPdfRenderer(sessions_root=sessions_root)

    output_pdf = "dummy_report.pdf"
    print(f"Rendering PDF to {output_pdf}...")

    try:
        pdf_bytes = renderer.render(session)
        with open(output_pdf, "wb") as f:
            f.write(pdf_bytes)
        print(f"Success! Created {output_pdf}")
    except Exception as e:
        print(f"Error rendering PDF: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
