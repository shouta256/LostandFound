export type Item = {
  id: string
  type: 'lost' | 'found'
  name: string
  description: string
  category: string
  date: string
  location: string
  status: 'available' | 'claimed' | 'returned'
  created_by: string
  created_at: string
  updated_at: string
}

export type Claim = {
  id: string
  item_id: string
  claimant_id: string
  ownership_information: string
  status: 'pending' | 'approved' | 'rejected'
  reviewed_by: string | null
  reviewed_at: string | null
  created_at: string
  updated_at: string
}

export type Pickup = {
  location: string
  status: 'not_ready' | 'ready'
  ready_at: string | null
}

export type ClaimDetail = Claim & { pickup: Pickup | null }
export type ClaimPage = { data: Claim[]; limit: number; offset: number; total: number }

export class ApiError extends Error {
  status: number
  code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

export async function apiRequest<T>(path: string, token: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Authorization', `Bearer ${token}`)
  if (init.body != null) headers.set('Content-Type', 'application/json')
  const response = await fetch(`/api/v1${path}`, { ...init, headers })
  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    if (body && typeof body === 'object' && 'error' in body) {
      const error = body.error
      if (error && typeof error === 'object' && 'code' in error && 'message' in error &&
          'details' in error && Array.isArray(error.details) &&
          typeof error.code === 'string' && typeof error.message === 'string') {
        throw new ApiError(response.status, error.code, error.message)
      }
    }
    throw new ApiError(response.status, '', `Request failed (HTTP ${response.status}). Please try again later.`)
  }
  return body as T
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Unable to complete the request. Please try again.'
}
