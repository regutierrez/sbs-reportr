from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class ReportStatus(StrEnum):
    DRAFT = "draft"
    GENERATING = "generating"
    COMPLETED = "completed"


class PhotoGroupName(StrEnum):
    BUILDING_DETAILS_BUILDING_PHOTO = "building_details_building_photo"
    SUPERSTRUCTURE_REBAR_SCANNING_PHOTOS = "superstructure_rebar_scanning_photos"
    SUPERSTRUCTURE_REBOUND_HAMMER_TEST_PHOTOS = "superstructure_rebound_hammer_test_photos"
    SUPERSTRUCTURE_CONCRETE_CORING_PHOTOS = "superstructure_concrete_coring_photos"
    SUPERSTRUCTURE_CORE_SAMPLES_FAMILY_PIC = "superstructure_core_samples_family_pic"
    SUPERSTRUCTURE_REBAR_EXTRACTION_PHOTOS = "superstructure_rebar_extraction_photos"
    SUPERSTRUCTURE_REBAR_SAMPLES_FAMILY_PIC = "superstructure_rebar_samples_family_pic"
    SUPERSTRUCTURE_CHIPPING_OF_SLAB_PHOTOS = "superstructure_chipping_of_slab_photos"
    SUPERSTRUCTURE_RESTORATION_PHOTOS = "superstructure_restoration_photos"
    SUBSTRUCTURE_CORING_FOR_FOUNDATION_PHOTOS = "substructure_coring_for_foundation_photos"
    SUBSTRUCTURE_REBAR_SCANNING_FOR_FOUNDATION_PHOTOS = (
        "substructure_rebar_scanning_for_foundation_photos"
    )
    SUBSTRUCTURE_RESTORATION_BACKFILLING_COMPACTION_PHOTOS = (
        "substructure_restoration_backfilling_compaction_photos"
    )


class AnnexGroupName(StrEnum):
    REBAR_SCANNING_OUTPUT = "rebar_scanning_output"
    REBOUND_NUMBER_TEST_RESULTS = "rebound_number_test_results"
    COMPRESSIVE_STRENGTH_TEST_RESULTS_SUPERSTRUCTURE = (
        "compressive_strength_test_results_superstructure"
    )
    TENSILE_STRENGTH_TEST_RESULTS = "tensile_strength_test_results"
    COMPRESSIVE_STRENGTH_TEST_RESULTS_SUBSTRUCTURE = (
        "compressive_strength_test_results_substructure"
    )
    REBAR_SCANNING_RESULTS_FOR_FOUNDATION = "rebar_scanning_results_for_foundation"
    MATERIAL_TESTS_MAPPING = "material_tests_mapping"


PHOTO_GROUP_LIMITS: dict[PhotoGroupName, tuple[int, int]] = {
    PhotoGroupName.BUILDING_DETAILS_BUILDING_PHOTO: (1, 1),
    PhotoGroupName.SUPERSTRUCTURE_REBAR_SCANNING_PHOTOS: (1, 5),
    PhotoGroupName.SUPERSTRUCTURE_REBOUND_HAMMER_TEST_PHOTOS: (1, 5),
    PhotoGroupName.SUPERSTRUCTURE_CONCRETE_CORING_PHOTOS: (1, 5),
    PhotoGroupName.SUPERSTRUCTURE_CORE_SAMPLES_FAMILY_PIC: (1, 5),
    PhotoGroupName.SUPERSTRUCTURE_REBAR_EXTRACTION_PHOTOS: (1, 5),
    PhotoGroupName.SUPERSTRUCTURE_REBAR_SAMPLES_FAMILY_PIC: (1, 5),
    PhotoGroupName.SUPERSTRUCTURE_CHIPPING_OF_SLAB_PHOTOS: (1, 5),
    PhotoGroupName.SUPERSTRUCTURE_RESTORATION_PHOTOS: (1, 5),
    PhotoGroupName.SUBSTRUCTURE_CORING_FOR_FOUNDATION_PHOTOS: (0, 5),
    PhotoGroupName.SUBSTRUCTURE_REBAR_SCANNING_FOR_FOUNDATION_PHOTOS: (0, 5),
    PhotoGroupName.SUBSTRUCTURE_RESTORATION_BACKFILLING_COMPACTION_PHOTOS: (0, 5),
}

ANNEX_GROUP_LIMITS: dict[AnnexGroupName, tuple[int, int]] = {
    AnnexGroupName.REBAR_SCANNING_OUTPUT: (0, 1),
    AnnexGroupName.REBOUND_NUMBER_TEST_RESULTS: (0, 1),
    AnnexGroupName.COMPRESSIVE_STRENGTH_TEST_RESULTS_SUPERSTRUCTURE: (0, 1),
    AnnexGroupName.TENSILE_STRENGTH_TEST_RESULTS: (0, 1),
    AnnexGroupName.COMPRESSIVE_STRENGTH_TEST_RESULTS_SUBSTRUCTURE: (0, 1),
    AnnexGroupName.REBAR_SCANNING_RESULTS_FOR_FOUNDATION: (0, 1),
    AnnexGroupName.MATERIAL_TESTS_MAPPING: (0, 1),
}


class BuildingDetailsFormFields(BaseModel):
    testing_date: str = Field(min_length=7, max_length=7)
    building_name: str = Field(max_length=200)
    building_location: str = Field(max_length=500)
    number_of_storey: int = Field(ge=1)


class SuperstructureRebarScanningFormFields(BaseModel):
    number_of_rebar_scan_locations: int = Field(ge=1)


class SuperstructureReboundHammerTestFormFields(BaseModel):
    number_of_rebound_hammer_test_locations: int = Field(ge=1)


class SuperstructureConcreteCoreExtractionFormFields(BaseModel):
    number_of_coring_locations: int = Field(ge=1)


class SuperstructureRebarExtractionFormFields(BaseModel):
    number_of_rebar_samples_extracted: int = Field(ge=1)


class SuperstructureRestorationWorksFormFields(BaseModel):
    non_shrink_grout_product_used: str = Field(max_length=200)
    epoxy_ab_used: str = Field(max_length=200)


class SuperstructureFormFields(BaseModel):
    rebar_scanning: SuperstructureRebarScanningFormFields
    rebound_hammer_test: SuperstructureReboundHammerTestFormFields
    concrete_core_extraction: SuperstructureConcreteCoreExtractionFormFields
    rebar_extraction: SuperstructureRebarExtractionFormFields
    restoration_works: SuperstructureRestorationWorksFormFields


class SubstructureConcreteCoreExtractionFormFields(BaseModel):
    number_of_foundation_locations: int = Field(ge=1)
    number_of_foundation_cores_extracted: int = Field(ge=1)


class SubstructureFormFields(BaseModel):
    concrete_core_extraction: SubstructureConcreteCoreExtractionFormFields


class SignatureFormFields(BaseModel):
    prepared_by: str = Field(max_length=100)
    prepared_by_role: str = Field(max_length=100)


class ReportFormFields(BaseModel):
    building_details: BuildingDetailsFormFields
    superstructure: SuperstructureFormFields
    substructure: SubstructureFormFields | None = None
    signature: SignatureFormFields


class ImageMeta(BaseModel):
    id: UUID
    group_name: PhotoGroupName
    original_filename: str
    stored_filename: str
    size_bytes: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class AnnexDocumentMeta(BaseModel):
    id: UUID
    group_name: AnnexGroupName
    original_filename: str
    stored_filename: str
    size_bytes: int = Field(ge=0)


class ReportSession(BaseModel):
    id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: ReportStatus = ReportStatus.DRAFT
    form_fields: ReportFormFields | None = None
    images: dict[str, list[ImageMeta]] = Field(default_factory=dict)
    annex_documents: dict[str, AnnexDocumentMeta] = Field(default_factory=dict)
    generated_pdf_path: str | None = None
