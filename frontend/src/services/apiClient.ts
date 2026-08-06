import type {
  ApiErrorResponse,
  HealthResponse,
  ReadinessResponse,
} from '../types/api.ts'

const DEFAULT_TIMEOUT_MS = 75_000

export class ApiClientError extends Error {
  readonly code: string
  readonly requestId?: string

  constructor(message: string, code = 'API_REQUEST_FAILED', requestId?: string) {
    super(message)
    this.name = 'ApiClientError'
    this.code = code
    this.requestId = requestId
  }
}

export const requestApi = async <T>(
  path: string,
  init?: RequestInit,
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<T> => {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetch(path, { ...init, signal: controller.signal })
    const payload = (await response.json().catch(() => null)) as
      | T
      | ApiErrorResponse
      | null
    if (!response.ok) {
      const error =
        payload && typeof payload === 'object' && 'error' in payload
          ? payload.error
          : null
      throw new ApiClientError(
        error?.message ?? '서버 요청을 처리하지 못했습니다.',
        error?.code,
        error?.requestId,
      )
    }
    if (payload === null) throw new ApiClientError('서버 응답이 비어 있습니다.')
    return payload as T
  } catch (error) {
    if (error instanceof ApiClientError) throw error
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiClientError('서버 응답 시간이 초과되었습니다.', 'API_TIMEOUT')
    }
    throw new ApiClientError('백엔드 서버에 연결하지 못했습니다.', 'API_UNREACHABLE')
  } finally {
    window.clearTimeout(timer)
  }
}

export interface BackendConnectionCheck {
  status: 'ready' | 'unconfigured' | 'unreachable'
  readiness?: ReadinessResponse
}

export const checkBackendConnection = async (): Promise<BackendConnectionCheck> => {
  try {
    await requestApi<HealthResponse>('/api/health', undefined, 5_000)
    const readiness = await requestApi<ReadinessResponse>(
      '/api/readiness',
      undefined,
      5_000,
    )
    return {
      status: readiness.ready ? 'ready' : 'unconfigured',
      readiness,
    }
  } catch {
    return { status: 'unreachable' }
  }
}
