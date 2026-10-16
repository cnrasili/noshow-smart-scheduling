// A stand-in for the web backend: tests list the answers, nothing is sent over the network
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { vi } from 'vitest'
import App from '../App'
import { dayKey } from '../format'
import type { Me } from '../types'

export interface Reply {
  status?: number
  body?: unknown
}

type Handler = (body: unknown, url: URL) => Reply | unknown

export interface Call {
  method: string
  path: string
  search: string
  body: unknown
}

/** Answers requests by "METHOD /path"; a handler returns a Reply or a JSON body for 200. */
export function fakeBackend(routes: Record<string, Handler>) {
  const calls: Call[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string, init: RequestInit = {}) => {
      const url = new URL(input)
      const method = init.method ?? 'GET'
      const body = init.body ? JSON.parse(String(init.body)) : undefined
      calls.push({ method, path: url.pathname, search: url.search, body })
      const handler = routes[`${method} ${url.pathname}`]
      if (!handler) return json(404, { detail: 'Not Found' })
      const result = handler(body, url)
      const reply: Reply =
        result !== null && typeof result === 'object' && ('status' in result || 'body' in result)
          ? (result as Reply)
          : { body: result }
      return json(reply.status ?? 200, reply.body)
    }),
  )
  return calls
}

function json(status: number, body: unknown): Response {
  if (status === 204) return new Response(null, { status })
  return new Response(JSON.stringify(body ?? null), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

export const PATIENT: Me = {
  role: 'patient',
  name: 'Ayşe Kaya',
  email: 'ayse@demo.local',
  specialty: null,
}
export const DOCTOR: Me = {
  role: 'doctor',
  name: 'Dr. Deniz Yıldız',
  email: 'doktor@demo.local',
  specialty: 'Dahiliye',
}

/** Store a session token so the app restores the user from GET /auth/me. */
export function signIn(me: Me): Record<string, Handler> {
  localStorage.setItem('noshow.token', 'test-token')
  return { 'GET /auth/me': () => me }
}

export function renderApp(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}

/** A clinic-time instant some days from today, as the backend sends it (UTC). */
export function clinicTime(daysAhead: number, clock: string): string {
  const day = dayKey(new Date(Date.now() + daysAhead * 24 * 3600_000).toISOString())
  return new Date(`${day}T${clock}:00+03:00`).toISOString()
}

export function hoursFromNow(hours: number): string {
  return new Date(Date.now() + hours * 3600_000).toISOString()
}

export function plusMinutes(iso: string, minutes: number): string {
  return new Date(new Date(iso).getTime() + minutes * 60_000).toISOString()
}
