import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { PHOTO_GROUPS } from '@/constants/photo-groups'
import { useReportIntakeDraft, type UploadItem } from '@/composables/use-report-intake-draft'
import type { PhotoGroupName, ReportFormFields } from '@/types/report'
import IntakeFormScreen from '@/screens/IntakeFormScreen.vue'

const {
  compressImageForUploadMock,
  createReportSessionMock,
  routerPushMock,
  saveReportFormFieldsMock,
  uploadReportImageMock,
} = vi.hoisted(() => {
  return {
    compressImageForUploadMock: vi.fn(),
    createReportSessionMock: vi.fn(),
    routerPushMock: vi.fn(),
    saveReportFormFieldsMock: vi.fn(),
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

  return draft
}

function fillRequiredForm(form: ReportFormFields): void {
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
          SectionHeader: true,
        },
      },
    })

    const submitButton = wrapper.get('button[type="submit"]').element as HTMLButtonElement

    expect(submitButton.disabled).toBe(true)
    expect(wrapper.text()).toContain('Continue to Confirmation')
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
          SectionHeader: true,
        },
      },
    })

    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    expect(createReportSessionMock).toHaveBeenCalledTimes(1)
    expect(saveReportFormFieldsMock).toHaveBeenCalledTimes(1)
    expect(uploadReportImageMock).not.toHaveBeenCalled()
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
          SectionHeader: true,
        },
      },
    })

    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    expect(createReportSessionMock).not.toHaveBeenCalled()
    expect(compressImageForUploadMock).toHaveBeenCalledTimes(1)
    expect(uploadReportImageMock).toHaveBeenCalledWith('session-2', pendingGroup, compressedFile)

    const pendingItem = draft.uploads[pendingGroup][0]
    if (!pendingItem) {
      throw new Error('Expected pending upload item to be present.')
    }

    expect(pendingItem.status).toBe('uploaded')
    expect(pendingItem.uploadedImage).not.toBeNull()
    expect(routerPushMock).toHaveBeenCalledWith({ name: 'confirmation' })
  })
})
