import type {
  Appointment,
  CalendarAppointment,
  CalendarSlot,
  Doctor,
  LoginCredentials,
  LoginResponse,
  Me,
  ScheduleDay,
  Slot,
} from './types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const TOKEN_KEY = 'noshow.token'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

// Storage can be unavailable (private mode, blocked site data); the session then lasts one page load
let memoryToken: string | null = null

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return memoryToken
  }
}

function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    // Keep the token in memory only
    memoryToken = token
  }
}

export const errorText = (error: unknown) =>
  error instanceof Error ? error.message : 'Beklenmeyen bir hata oluştu'

let unauthorizedHandler: () => void = () => {}

export function onUnauthorized(handler: () => void) {
  unauthorizedHandler = handler
}

function errorMessage(body: unknown, status: number): string {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return 'Geçersiz istek'
  return `İstek başarısız (${status})`
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.body) headers.set('Content-Type', 'application/json')

  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, { ...init, headers })
  } catch {
    throw new ApiError(0, 'Sunucuya ulaşılamıyor')
  }
  if (response.status === 204) return undefined as T

  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    if (response.status === 401 && token) {
      setToken(null)
      unauthorizedHandler()
    }
    throw new ApiError(response.status, errorMessage(body, response.status))
  }
  return body as T
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  body: JSON.stringify(body),
})

export const api = {
  async login(credentials: LoginCredentials): Promise<Me> {
    const { token, ...me } = await request<LoginResponse>('/auth/login', json('POST', credentials))
    setToken(token)
    return me
  },
  async logout(): Promise<void> {
    try {
      await request<void>('/auth/logout', { method: 'POST' })
    } finally {
      setToken(null)
    }
  },
  me: () => request<Me>('/auth/me'),
  doctors: () => request<Doctor[]>('/doctors'),
  slots: (doctorId: number) => request<Slot[]>(`/slots?doctor_id=${doctorId}`),
  myAppointments: () => request<Appointment[]>('/patients/me/appointments'),
  book: (slotId: number) =>
    request<Appointment>('/appointments', json('POST', { slot_id: slotId })),
  cancel: (appointmentId: number) =>
    request<void>(`/appointments/${appointmentId}`, { method: 'DELETE' }),
  calendar: (day: string) =>
    request<CalendarSlot[]>(`/doctors/me/calendar?date=${encodeURIComponent(day)}`),
  markAttendance: (appointmentId: number, attended: boolean) =>
    request<CalendarAppointment>(
      `/appointments/${appointmentId}/attendance`,
      json('PATCH', { attended }),
    ),
  schedule: () => request<ScheduleDay[]>('/doctors/me/schedule'),
  generateSlots: (dateFrom: string, dateTo: string) =>
    request<{ created: number }>(
      '/doctors/me/slots/generate',
      json('POST', { date_from: dateFrom, date_to: dateTo }),
    ),
}
