import { afterEach, describe, expect, it, vi } from 'vitest'

import { downloadReportPdf } from '@/api'

function mockDownloadRequest(contentDisposition: string | null) {
  const headers = new Headers()
  if (contentDisposition) {
    headers.set('content-disposition', contentDisposition)
  }

  const response = new Response(new Blob(['%PDF-1.7'], { type: 'application/pdf' }), {
    status: 200,
    headers,
  })

  const fetchMock = vi.fn().mockResolvedValue(response)
  vi.stubGlobal('fetch', fetchMock)

  vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:report-url')
  vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

  let link: HTMLAnchorElement | null = null
  vi.spyOn(document.body, 'append').mockImplementation((...nodes: (Node | string)[]) => {
    const foundLink = nodes.find((node): node is HTMLAnchorElement => node instanceof HTMLAnchorElement)
    if (foundLink) {
      link = foundLink
    }
  })

  return {
    fetchMock,
    getLink: () => link,
  }
}

describe('downloadReportPdf', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('uses filename from response content-disposition header', async () => {
    const { fetchMock, getLink } = mockDownloadRequest(
      'attachment; filename="acacia-residences-activity-report.pdf"',
    )

    await downloadReportPdf('/reports/session-1/download')

    expect(fetchMock).toHaveBeenCalledWith('/api/reports/session-1/download', {
      method: 'GET',
    })
    expect(getLink()?.download).toBe('acacia-residences-activity-report.pdf')
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:report-url')
  })

  it('falls back to activity-report.pdf when filename header is missing', async () => {
    const { getLink } = mockDownloadRequest(null)

    await downloadReportPdf('/reports/session-1/download')

    expect(getLink()?.download).toBe('activity-report.pdf')
  })

  it('throws ApiError when download request fails', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: 'missing' }), {
        status: 404,
        statusText: 'Not Found',
        headers: {
          'content-type': 'application/json',
        },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(downloadReportPdf('/reports/missing/download')).rejects.toMatchObject({
      status: 404,
      detail: 'missing',
    })
  })
})
