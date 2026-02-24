export type ReportStatus = 'draft' | 'generating' | 'completed'

export interface BuildingDetailsFormFields {
  testing_date: string
  building_name: string
  building_location: string
  number_of_storey: number
}

export interface SuperstructureRebarScanningFormFields {
  number_of_rebar_scan_locations: number
}

export interface SuperstructureReboundHammerTestFormFields {
  number_of_rebound_hammer_test_locations: number
}

export interface SuperstructureConcreteCoreExtractionFormFields {
  number_of_coring_locations: number
}

export interface SuperstructureRebarExtractionFormFields {
  number_of_rebar_samples_extracted: number
}

export interface SuperstructureRestorationWorksFormFields {
  non_shrink_grout_product_used: string
  epoxy_ab_used: string
}

export interface SuperstructureFormFields {
  rebar_scanning: SuperstructureRebarScanningFormFields
  rebound_hammer_test: SuperstructureReboundHammerTestFormFields
  concrete_core_extraction: SuperstructureConcreteCoreExtractionFormFields
  rebar_extraction: SuperstructureRebarExtractionFormFields
  restoration_works: SuperstructureRestorationWorksFormFields
}

export interface SubstructureConcreteCoreExtractionFormFields {
  number_of_foundation_locations: number
  number_of_foundation_cores_extracted: number
}

export interface SubstructureFormFields {
  concrete_core_extraction: SubstructureConcreteCoreExtractionFormFields
}

export interface SignatureFormFields {
  prepared_by: string
  prepared_by_role: string
}

export interface ReportFormFields {
  building_details: BuildingDetailsFormFields
  superstructure: SuperstructureFormFields
  substructure: SubstructureFormFields
  signature: SignatureFormFields
}

export type PhotoGroupName =
  | 'building_details_building_photo'
  | 'superstructure_rebar_scanning_photos'
  | 'superstructure_rebound_hammer_test_photos'
  | 'superstructure_concrete_coring_photos'
  | 'superstructure_core_samples_family_pic'
  | 'superstructure_rebar_extraction_photos'
  | 'superstructure_rebar_samples_family_pic'
  | 'superstructure_chipping_of_slab_photos'
  | 'superstructure_restoration_photos'
  | 'substructure_coring_for_foundation_photos'
  | 'substructure_rebar_scanning_for_foundation_photos'
  | 'substructure_restoration_backfilling_compaction_photos'

export interface ImageMeta {
  id: string
  group_name: PhotoGroupName
  original_filename: string
  stored_filename: string
  size_bytes: number
  width: number
  height: number
}

export interface ReportSession {
  id: string
  created_at: string
  status: ReportStatus
  form_fields: ReportFormFields | null
  images: Record<string, ImageMeta[]>
  generated_pdf_path: string | null
}

export interface SessionStatusResponse {
  session_id: string
  status: ReportStatus
}

export interface ImageUploadResult {
  image: ImageMeta
}
