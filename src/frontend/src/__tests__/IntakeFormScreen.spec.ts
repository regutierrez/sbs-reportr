import { flushPromises, mount, type DOMWrapper } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ANNEX_GROUPS } from '@/constants/annex-groups'
import { PHOTO_GROUPS } from '@/constants/photo-groups'
import {
  useReportIntakeDraft,
  type AnnexUploadItem,
  type UploadItem,
} from '@/composables/use-report-intake-draft'
import type { AnnexGroupName, PhotoGroupName, ReportFormFields } from '@/types/report'
import IntakeFormScreen from '@/screens/IntakeFormScreen.vue'

const {
  compressImageForUploadMock,
  createReportSessionMock,
  routerPushMock,
  saveReportFormFieldsMock,
  uploadReportAnnexPdfMock,
  uploadReportImageMock,
} = vi.hoisted(() => {
  return {
    compressImageForUploadMock: vi.fn(),
    createReportSessionMock: vi.fn(),
    routerPushMock: vi.fn(),
    saveReportFormFieldsMock: vi.fn(),
    uploadReportAnnexPdfMock: vi.fn(),
    uploadReportImageMock: vi.fn(),
  }
})

vi.mock('vue-router', () => {
  return {
    useRouter: () => ({
      push: routerPushMock,
    }),
  }
})

vi.mock('@/api', () => {
  class ApiError extends Error {
    status: number
    detail: unknown

    constructor(status: number, detail: unknown) {
      super(typeof detail === 'string' ? detail : 'Request failed')
      this.status = status
      this.detail = detail
    }
  }

  return {
    ApiError,
    createReportSession: createReportSessionMock,
    saveReportFormFields: saveReportFormFieldsMock,
    uploadReportAnnexPdf: uploadReportAnnexPdfMock,
    uploadReportImage: uploadReportImageMock,
  }
})

vi.mock('@/utils/image-compression', () => {
  return {
    compressImageForUpload: compressImageForUploadMock,
  }
})

function resetDraftStore() {
  const draft = useReportIntakeDraft()

  Object.assign(draft.form.building_details, {
    testing_date: '',
    building_name: '',
    building_location: '',
    number_of_storey: 0,
  })
  Object.assign(draft.form.superstructure.rebar_scanning, {
    number_of_rebar_scan_locations: 0,
  })
  Object.assign(draft.form.superstructure.rebound_hammer_test, {
    number_of_rebound_hammer_test_locations: 0,
  })
  Object.assign(draft.form.superstructure.concrete_core_extraction, {
    number_of_coring_locations: 0,
  })
  Object.assign(draft.form.superstructure.rebar_extraction, {
    number_of_rebar_samples_extracted: 0,
  })
  Object.assign(draft.form.superstructure.restoration_works, {
    non_shrink_grout_product_used: '',
    epoxy_ab_used: '',
  })
  Object.assign(draft.form.substructure.concrete_core_extraction, {
    number_of_foundation_locations: 0,
    number_of_foundation_cores_extracted: 0,
  })
  Object.assign(draft.form.signature, {
    prepared_by: '',
    prepared_by_role: '',
  })

  draft.confirmationReady.value = false
  draft.generatedDownloadUrl.value = null
  draft.sessionId.value = null

  for (const group of PHOTO_GROUPS) {
    draft.selectionWarnings[group.name] = ''
    draft.uploads[group.name] = []
  }
  for (const group of ANNEX_GROUPS) {
    draft.annexSelectionWarnings[group.name] = ''
    draft.annexUploads[group.name] = []
  }

  return draft
}

function fillRequiredForm(form: Required<ReportFormFields>): void {
  Object.assign(form.building_details, {
    testing_date: '2026-02',
    building_name: 'Acacia Residences',
    building_location: 'Makati City',
    number_of_storey: 12,
  })
  Object.assign(form.superstructure.rebar_scanning, {
    number_of_rebar_scan_locations: 3,
  })
  Object.assign(form.superstructure.rebound_hammer_test, {
    number_of_rebound_hammer_test_locations: 4,
  })
  Object.assign(form.superstructure.concrete_core_extraction, {
    number_of_coring_locations: 2,
  })
  Object.assign(form.superstructure.rebar_extraction, {
    number_of_rebar_samples_extracted: 2,
  })
  Object.assign(form.superstructure.restoration_works, {
    non_shrink_grout_product_used: 'SikaGrout 214',
    epoxy_ab_used: 'Sikadur-31',
  })
  Object.assign(form.substructure.concrete_core_extraction, {
    number_of_foundation_locations: 3,
    number_of_foundation_cores_extracted: 3,
  })
  Object.assign(form.signature, {
    prepared_by: 'Jane Dela Cruz',
    prepared_by_role: 'Structural Engineer',
  })
}

function createUploadItem(groupName: PhotoGroupName, uploaded: boolean): UploadItem {
  const file = new File(['image'], `${groupName}.jpg`, { type: 'image/jpeg' })

  return {
    id: `item-${groupName}`,
    name: file.name,
    file,
    previewUrl: `blob:${groupName}`,
    status: uploaded ? 'uploaded' : 'pending',
    message: uploaded ? 'Uploaded' : 'Queued',
    uploadedImage: uploaded
      ? {
          id: `image-${groupName}`,
          group_name: groupName,
          original_filename: file.name,
          stored_filename: `stored-${groupName}.jpg`,
          size_bytes: 1234,
          width: 900,
          height: 600,
        }
      : null,
  }
}

function createAnnexUploadItem(groupName: AnnexGroupName, uploaded: boolean): AnnexUploadItem {
  const file = new File(['pdf'], `${groupName}.pdf`, { type: 'application/pdf' })

  return {
    id: `annex-${groupName}`,
    name: file.name,
    file,
    status: uploaded ? 'uploaded' : 'pending',
    message: uploaded ? 'Uploaded' : 'Queued',
    uploadedDocument: uploaded
      ? {
          id: `document-${groupName}`,
          group_name: groupName,
          original_filename: file.name,
          stored_filename: `stored-${groupName}.pdf`,
          size_bytes: 4096,
        }
      : null,
  }
}

async function triggerFileSelection(input: DOMWrapper<Element>, files: File[]): Promise<void> {
  const element = input.element as HTMLInputElement
  Object.defineProperty(element, 'files', {
    value: files,
    configurable: true,
  })

  await input.trigger('change')
}

describe('IntakeFormScreen', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    resetDraftStore()
  })

  it('keeps Continue disabled while required data is missing', () => {
    const wrapper = mount(IntakeFormScreen, {
      global: {
        stubs: {
          ImageUploadField: true,
          PdfUploadField: true,
          SectionHeader: true,
        },
      },
    })

    const submitButton = wrapper.get('button[type="submit"]').element as HTMLButtonElement

    expect(submitButton.disabled).toBe(true)
    expect(wrapper.text()).toContain('Continue to Confirmation')
  })

  it('prevents duplicate uploads within the same photo group', async () => {
    const draft = resetDraftStore()

    const wrapper = mount(IntakeFormScreen, {
      global: {
        stubs: {
          PdfUploadField: true,
          SectionHeader: true,
        },
      },
    })

    const libraryInputs = wrapper.findAll('input.upload-dropzone__input')
    const rebarScanningInput = libraryInputs[1]

    if (!rebarScanningInput) {
      throw new Error('Expected a rebar scanning upload input.')
    }

    const firstSelection = new File(['same-photo'], 'same-photo.jpg', {
      type: 'image/jpeg',
      lastModified: 1,
    })
    const duplicateSelection = new File(['same-photo'], 'same-photo.jpg', {
      type: 'image/jpeg',
      lastModified: 1,
    })
    const uniqueSelection = new File(['different-photo'], 'different-photo.jpg', {
      type: 'image/jpeg',
      lastModified: 2,
    })

    await triggerFileSelection(rebarScanningInput, [firstSelection])
    await triggerFileSelection(rebarScanningInput, [duplicateSelection, uniqueSelection])

    const groupName: PhotoGroupName = 'superstructure_rebar_scanning_photos'
    expect(draft.uploads[groupName]).toHaveLength(2)
    expect(draft.uploads[groupName].map((item) => item.name)).toEqual([
      'same-photo.jpg',
      'different-photo.jpg',
    ])
    expect(draft.selectionWarnings[groupName]).toContain('duplicate')
  })

  it('allows the same photo file across different photo groups', async () => {
    const draft = resetDraftStore()

    const wrapper = mount(IntakeFormScreen, {
      global: {
        stubs: {
          PdfUploadField: true,
          SectionHeader: true,
        },
      },
    })

    const libraryInputs = wrapper.findAll('input.upload-dropzone__input')
    const rebarScanningInput = libraryInputs[1]
    const reboundHammerInput = libraryInputs[2]

    if (!rebarScanningInput || !reboundHammerInput) {
      throw new Error('Expected upload inputs for rebar scanning and rebound hammer groups.')
    }

    const sharedPhotoForRebar = new File(['shared-photo'], 'shared-photo.jpg', {
      type: 'image/jpeg',
      lastModified: 9,
    })
    const sharedPhotoForRebound = new File(['shared-photo'], 'shared-photo.jpg', {
      type: 'image/jpeg',
      lastModified: 9,
    })

    await triggerFileSelection(rebarScanningInput, [sharedPhotoForRebar])
    await triggerFileSelection(reboundHammerInput, [sharedPhotoForRebound])

    expect(draft.uploads.superstructure_rebar_scanning_photos).toHaveLength(1)
    expect(draft.uploads.superstructure_rebound_hammer_test_photos).toHaveLength(1)
    expect(draft.selectionWarnings.superstructure_rebar_scanning_photos).toBe('')
    expect(draft.selectionWarnings.superstructure_rebound_hammer_test_photos).toBe('')
  })

  it('saves completed draft and moves to confirmation', async () => {
    const draft = resetDraftStore()
    fillRequiredForm(draft.form)
    for (const group of PHOTO_GROUPS) {
      draft.uploads[group.name] = [createUploadItem(group.name, true)]
    }

    createReportSessionMock.mockResolvedValue({
      session_id: 'session-1',
      status: 'draft',
    })
    saveReportFormFieldsMock.mockResolvedValue({})

    const wrapper = mount(IntakeFormScreen, {
      global: {
        stubs: {
          ImageUploadField: true,
          PdfUploadField: true,
          SectionHeader: true,
        },
      },
    })

    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    expect(createReportSessionMock).toHaveBeenCalledTimes(1)
    expect(saveReportFormFieldsMock).toHaveBeenCalledTimes(1)
    expect(uploadReportImageMock).not.toHaveBeenCalled()
    expect(uploadReportAnnexPdfMock).not.toHaveBeenCalled()
    expect(routerPushMock).toHaveBeenCalledWith({ name: 'confirmation' })
    expect(draft.sessionId.value).toBe('session-1')
    expect(draft.confirmationReady.value).toBe(true)
  })

  it('compresses and uploads pending photo items before confirmation', async () => {
    const draft = resetDraftStore()
    fillRequiredForm(draft.form)
    draft.sessionId.value = 'session-2'

    const pendingGroup = PHOTO_GROUPS[0]?.name
    if (!pendingGroup) {
      throw new Error('Expected at least one photo group config.')
    }
    for (const group of PHOTO_GROUPS) {
      draft.uploads[group.name] = [createUploadItem(group.name, group.name !== pendingGroup)]
    }

    const compressedFile = new File(['compressed'], 'compressed.jpg', { type: 'image/jpeg' })
    compressImageForUploadMock.mockResolvedValue(compressedFile)
    uploadReportImageMock.mockResolvedValue({
      image: {
        id: 'uploaded-image',
        group_name: pendingGroup,
        original_filename: compressedFile.name,
        stored_filename: 'uploaded.jpg',
        size_bytes: 777,
        width: 800,
        height: 600,
      },
    })
    saveReportFormFieldsMock.mockResolvedValue({})

    const wrapper = mount(IntakeFormScreen, {
      global: {
        stubs: {
          ImageUploadField: true,
          PdfUploadField: true,
          SectionHeader: true,
        },
      },
    })

    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    expect(createReportSessionMock).not.toHaveBeenCalled()
    expect(compressImageForUploadMock).toHaveBeenCalledTimes(1)
    expect(uploadReportImageMock).toHaveBeenCalledWith('session-2', pendingGroup, compressedFile)
    expect(uploadReportAnnexPdfMock).not.toHaveBeenCalled()

    const pendingItem = draft.uploads[pendingGroup][0]
    if (!pendingItem) {
      throw new Error('Expected pending upload item to be present.')
    }

    expect(pendingItem.status).toBe('uploaded')
    expect(pendingItem.uploadedImage).not.toBeNull()
    expect(routerPushMock).toHaveBeenCalledWith({ name: 'confirmation' })
  })

  it('enables submit when substructure fields are empty', async () => {
    const draft = resetDraftStore()

    Object.assign(draft.form.building_details, {
      testing_date: '2026-02',
      building_name: 'Acacia Residences',
      building_location: 'Makati City',
      number_of_storey: 12,
    })
    Object.assign(draft.form.superstructure.rebar_scanning, {
      number_of_rebar_scan_locations: 3,
    })
    Object.assign(draft.form.superstructure.rebound_hammer_test, {
      number_of_rebound_hammer_test_locations: 4,
    })
    Object.assign(draft.form.superstructure.concrete_core_extraction, {
      number_of_coring_locations: 2,
    })
    Object.assign(draft.form.superstructure.rebar_extraction, {
      number_of_rebar_samples_extracted: 2,
    })
    Object.assign(draft.form.superstructure.restoration_works, {
      non_shrink_grout_product_used: 'SikaGrout 214',
      epoxy_ab_used: 'Sikadur-31',
    })
    Object.assign(draft.form.signature, {
      prepared_by: 'Jane Dela Cruz',
      prepared_by_role: 'Structural Engineer',
    })

    // substructure fields intentionally left at defaults (0)

    for (const group of PHOTO_GROUPS) {
      draft.uploads[group.name] = [createUploadItem(group.name, true)]
    }

    createReportSessionMock.mockResolvedValue({
      session_id: 'session-no-sub',
      status: 'draft',
    })
    saveReportFormFieldsMock.mockResolvedValue({})

    const wrapper = mount(IntakeFormScreen, {
      global: {
        stubs: {
          ImageUploadField: true,
          PdfUploadField: true,
          SectionHeader: true,
        },
      },
    })

    const submitButton = wrapper.get('button[type="submit"]').element as HTMLButtonElement
    expect(submitButton.disabled).toBe(false)

    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    expect(createReportSessionMock).toHaveBeenCalledTimes(1)
    expect(saveReportFormFieldsMock).toHaveBeenCalledTimes(1)
    expect(routerPushMock).toHaveBeenCalledWith({ name: 'confirmation' })
    expect(draft.sessionId.value).toBe('session-no-sub')
    expect(draft.confirmationReady.value).toBe(true)
  })

  it('uploads selected annex PDFs when provided', async () => {
    const draft = resetDraftStore()
    fillRequiredForm(draft.form)
    draft.sessionId.value = 'session-3'

    for (const group of PHOTO_GROUPS) {
      draft.uploads[group.name] = [createUploadItem(group.name, true)]
    }

    const annexGroup = ANNEX_GROUPS[0]?.name
    if (!annexGroup) {
      throw new Error('Expected at least one annex group config.')
    }

    for (const group of ANNEX_GROUPS) {
      draft.annexUploads[group.name] = [createAnnexUploadItem(group.name, group.name !== annexGroup)]
    }

    uploadReportAnnexPdfMock.mockResolvedValue({
      document: {
        id: 'uploaded-document',
        group_name: annexGroup,
        original_filename: `${annexGroup}.pdf`,
        stored_filename: 'uploaded-annex.pdf',
        size_bytes: 2048,
      },
    })
    saveReportFormFieldsMock.mockResolvedValue({})

    const wrapper = mount(IntakeFormScreen, {
      global: {
        stubs: {
          ImageUploadField: true,
          PdfUploadField: true,
          SectionHeader: true,
        },
      },
    })

    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    const pendingAnnex = draft.annexUploads[annexGroup][0]
    if (!pendingAnnex) {
      throw new Error('Expected pending annex upload item to be present.')
    }

    expect(uploadReportAnnexPdfMock).toHaveBeenCalledWith('session-3', annexGroup, pendingAnnex.file)
    expect(pendingAnnex.status).toBe('uploaded')
    expect(pendingAnnex.uploadedDocument).not.toBeNull()
    expect(routerPushMock).toHaveBeenCalledWith({ name: 'confirmation' })
  })
})
