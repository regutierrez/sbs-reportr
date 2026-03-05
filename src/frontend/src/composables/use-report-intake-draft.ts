import { reactive, ref } from 'vue'

import { ANNEX_GROUPS } from '@/constants/annex-groups'
import { PHOTO_GROUPS } from '@/constants/photo-groups'
import type {
  AnnexDocumentMeta,
  AnnexGroupName,
  ImageMeta,
  PhotoGroupName,
  ReportFormFields,
} from '@/types/report'

export type UploadState = 'pending' | 'compressing' | 'uploading' | 'uploaded' | 'error'
export type AnnexUploadState = 'pending' | 'uploading' | 'uploaded' | 'error'

export interface UploadItem {
  id: string
  name: string
  file: File
  previewUrl: string
  status: UploadState
  message: string
  uploadedImage: ImageMeta | null
}

export interface AnnexUploadItem {
  id: string
  name: string
  file: File
  status: AnnexUploadState
  message: string
  uploadedDocument: AnnexDocumentMeta | null
}

function createInitialForm(): ReportFormFields {
  return {
    building_details: {
      testing_date: '',
      building_name: '',
      building_location: '',
      number_of_storey: 0,
    },
    superstructure: {
      rebar_scanning: {
        number_of_rebar_scan_locations: 0,
      },
      rebound_hammer_test: {
        number_of_rebound_hammer_test_locations: 0,
      },
      concrete_core_extraction: {
        number_of_coring_locations: 0,
      },
      rebar_extraction: {
        number_of_rebar_samples_extracted: 0,
      },
      restoration_works: {
        non_shrink_grout_product_used: '',
        epoxy_ab_used: '',
      },
    },
    substructure: {
      concrete_core_extraction: {
        number_of_foundation_locations: 0,
        number_of_foundation_cores_extracted: 0,
      },
    },
    signature: {
      prepared_by: '',
      prepared_by_role: '',
    },
  }
}

function createUploadItemsMap(): Record<PhotoGroupName, UploadItem[]> {
  return PHOTO_GROUPS.reduce(
    (accumulator, group) => {
      accumulator[group.name] = []
      return accumulator
    },
    {} as Record<PhotoGroupName, UploadItem[]>,
  )
}

function createSelectionWarningsMap(): Record<PhotoGroupName, string> {
  return PHOTO_GROUPS.reduce(
    (accumulator, group) => {
      accumulator[group.name] = ''
      return accumulator
    },
    {} as Record<PhotoGroupName, string>,
  )
}

function createAnnexUploadItemsMap(): Record<AnnexGroupName, AnnexUploadItem[]> {
  return ANNEX_GROUPS.reduce(
    (accumulator, group) => {
      accumulator[group.name] = []
      return accumulator
    },
    {} as Record<AnnexGroupName, AnnexUploadItem[]>,
  )
}

function createAnnexSelectionWarningsMap(): Record<AnnexGroupName, string> {
  return ANNEX_GROUPS.reduce(
    (accumulator, group) => {
      accumulator[group.name] = ''
      return accumulator
    },
    {} as Record<AnnexGroupName, string>,
  )
}

const form = reactive<ReportFormFields>(createInitialForm())
const sessionId = ref<string | null>(null)
const uploads = reactive(createUploadItemsMap())
const selectionWarnings = reactive(createSelectionWarningsMap())
const annexUploads = reactive(createAnnexUploadItemsMap())
const annexSelectionWarnings = reactive(createAnnexSelectionWarningsMap())
const confirmationReady = ref(false)
const generatedDownloadUrl = ref<string | null>(null)

export function useReportIntakeDraft() {
  return {
    annexSelectionWarnings,
    annexUploads,
    confirmationReady,
    form,
    generatedDownloadUrl,
    selectionWarnings,
    sessionId,
    uploads,
  }
}
