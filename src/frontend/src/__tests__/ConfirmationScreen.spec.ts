import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { PHOTO_GROUPS } from '@/constants/photo-groups'
import { useReportIntakeDraft, type UploadItem } from '@/composables/use-report-intake-draft'
import type { PhotoGroupName, ReportFormFields } from '@/types/report'
import ConfirmationScreen from '@/screens/ConfirmationScreen.vue'

const { generateReportMock, resolveApiUrlMock, routerPushMock, routerReplaceMock } = vi.hoisted(() => {
  return {
    generateReportMock: vi.fn(),
    resolveApiUrlMock: vi.fn(),
    routerPushMock: vi.fn(),
    routerReplaceMock: vi.fn(),
  }
})

vi.mock('vue-router', () => {
  return {
    useRouter: () => ({
      push: routerPushMock,
      replace: routerReplaceMock,
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
    generateReport: generateReportMock,
    resolveApiUrl: resolveApiUrlMock,
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

function fillSummaryData(form: ReportFormFields): void {
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

function createUploadItem(groupName: PhotoGroupName): UploadItem {
  const file = new File(['image'], `${groupName}.jpg`, { type: 'image/jpeg' })

  return {
    id: `item-${groupName}`,
    name: file.name,
    file,
    previewUrl: `blob:${groupName}`,
    status: 'uploaded',
    message: 'Uploaded',
    uploadedImage: {
      id: `image-${groupName}`,
      group_name: groupName,
      original_filename: file.name,
      stored_filename: `stored-${groupName}.jpg`,
      size_bytes: 1234,
      width: 900,
      height: 600,
    },
  }
}

describe('ConfirmationScreen', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    resetDraftStore()
  })

  it('redirects to intake when draft is not ready', async () => {
    mount(ConfirmationScreen, {
      global: {
        stubs: {
          SectionHeader: true,
        },
      },
    })

    await flushPromises()

    expect(routerReplaceMock).toHaveBeenCalledWith({ name: 'intake' })
  })

  it('generates report, opens download, and supports re-download and revert', async () => {
    const draft = resetDraftStore()
    draft.confirmationReady.value = true
    draft.sessionId.value = 'session-1'
    fillSummaryData(draft.form)

    for (const group of PHOTO_GROUPS) {
      draft.uploads[group.name] = [createUploadItem(group.name)]
    }

    generateReportMock.mockResolvedValue({
      session_id: 'session-1',
      download_url: '/reports/session-1/download',
    })
    resolveApiUrlMock.mockImplementation((path: string) => `http://localhost:8000${path}`)

    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)

    const wrapper = mount(ConfirmationScreen, {
      global: {
        stubs: {
          SectionHeader: true,
        },
      },
    })

    await wrapper.get('.btn--primary').trigger('click')
    await flushPromises()

    expect(generateReportMock).toHaveBeenCalledWith('session-1')
    expect(openSpy).toHaveBeenCalledWith(
      'http://localhost:8000/reports/session-1/download',
      '_blank',
      'noopener',
    )
    expect(wrapper.text()).toContain('Report generated. A new tab was opened for download.')

    const buttons = wrapper.findAll('button')
    const downloadAgainButton = buttons.find((button) => button.text().includes('Download Again'))
    const revertButton = buttons.find((button) => button.text().includes('Revert'))

    if (!downloadAgainButton || !revertButton) {
      throw new Error('Expected confirmation actions to be available.')
    }

    await downloadAgainButton.trigger('click')
    await revertButton.trigger('click')

    expect(openSpy).toHaveBeenCalledTimes(2)
    expect(routerPushMock).toHaveBeenCalledWith({ name: 'intake' })
  })
})
