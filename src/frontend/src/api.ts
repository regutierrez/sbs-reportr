import type {
  GenerateReportResponse,
  ImageUploadResult,
  PhotoGroupName,
  ReportFormFields,
  ReportSession,
  SessionStatusResponse,
} from '@/types/report'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export function resolveApiUrl(path: string): string {
  if (/^https?:\/\//.test(path)) {
    return path
  }

  return `${API_BASE_URL}${path}`
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
  const response = await fetch(`${API_BASE_URL}${path}`, init)

  if (!response.ok) {
    let detail: unknown = response.statusText

    try {
      const payload = (await response.json()) as { detail?: unknown }
      detail = payload.detail ?? detail
    } catch {
      detail = response.statusText
    }

    throw new ApiError(response.status, detail)
  }

  return (await response.json()) as T
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
