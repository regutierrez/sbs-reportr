import type {
  GenerateReportResponse,
  ImageUploadResult,
  PhotoGroupName,
  ReportFormFields,
  ReportSession,
  SessionStatusResponse,
} from '@/types/report'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:9999'

export function resolveApiUrl(path: string): string {
  if (/^https?:\/\//.test(path)) {
    return path
  }

  return `${API_BASE_URL}${path}`
}

function parseDownloadFilename(contentDisposition: string | null): string | null {
  if (!contentDisposition) {
    return null
  }

  const encodedFilenameMatch = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (encodedFilenameMatch?.[1]) {
    const encodedFilename = encodedFilenameMatch[1].trim().replace(/^"|"$/g, '')

    try {
      return decodeURIComponent(encodedFilename)
    } catch {
      return encodedFilename
    }
  }

  const plainFilenameMatch = contentDisposition.match(/filename="?([^";]+)"?/i)
  return plainFilenameMatch?.[1] ?? null
}

async function extractErrorDetail(response: Response): Promise<unknown> {
  let detail: unknown = response.statusText

  try {
    const payload = (await response.json()) as { detail?: unknown }
    detail = payload.detail ?? detail
  } catch {
    detail = response.statusText
  }

  return detail
}

export class ApiError extends Error {
  status: number
  detail: unknown

  constructor(status: number, detail: unknown) {
    super(typeof detail === 'string' ? detail : 'Request failed')
    this.status = status
    this.detail = detail
  }
}

async function requestJson<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(resolveApiUrl(path), init)

  if (!response.ok) {
    throw new ApiError(response.status, await extractErrorDetail(response))
  }

  return (await response.json()) as T
}

export async function downloadReportPdf(path: string): Promise<void> {
  const response = await fetch(resolveApiUrl(path), {
    method: 'GET',
  })

  if (!response.ok) {
    throw new ApiError(response.status, await extractErrorDetail(response))
  }

  const pdfBlob = await response.blob()
  const filename = parseDownloadFilename(response.headers.get('content-disposition')) ?? 'activity-report.pdf'
  const objectUrl = URL.createObjectURL(pdfBlob)
  const downloadLink = document.createElement('a')

  downloadLink.href = objectUrl
  downloadLink.download = filename
  downloadLink.style.display = 'none'

  document.body.append(downloadLink)
  downloadLink.click()
  downloadLink.remove()
  URL.revokeObjectURL(objectUrl)
}

export function createReportSession(): Promise<SessionStatusResponse> {
  return requestJson<SessionStatusResponse>('/reports', {
    method: 'POST',
  })
}

export function saveReportFormFields(
  sessionId: string,
  formFields: ReportFormFields,
): Promise<ReportSession> {
  return requestJson<ReportSession>(`/reports/${sessionId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(formFields),
  })
}

export function uploadReportImage(
  sessionId: string,
  groupName: PhotoGroupName,
  imageFile: File,
): Promise<ImageUploadResult> {
  const formData = new FormData()
  formData.append('image', imageFile)

  return requestJson<ImageUploadResult>(`/reports/${sessionId}/images/${groupName}`, {
    method: 'POST',
    body: formData,
  })
}

export function generateReport(sessionId: string): Promise<GenerateReportResponse> {
  return requestJson<GenerateReportResponse>(`/reports/${sessionId}/generate`, {
    method: 'POST',
  })
}
