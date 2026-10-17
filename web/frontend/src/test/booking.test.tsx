import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { addDays, formatLongDate, todayKey, weekStart } from '../format'
import type { Appointment, Slot } from '../types'
import { PATIENT, PATIENT_NUMBER, fakeBackend, renderApp, signIn } from './backend'

// The week the booking opens with: this week, or the next one on a weekend
const MONDAY = (() => {
  const monday = weekStart(todayKey())
  return todayKey() >= addDays(monday, 5) ? addDays(monday, 7) : monday
})()
const TUESDAY = addDays(MONDAY, 1)

const at = (day: string, clock: string) => new Date(`${day}T${clock}:00+03:00`).toISOString()

function slot(id: number, day: string, clock: string, extra: Partial<Slot> = {}): Slot {
  const start = at(day, clock)
  return {
    id,
    start_at: start,
    end_at: new Date(new Date(start).getTime() + 15 * 60_000).toISOString(),
    available: true,
    booked_by_me: false,
    ...extra,
  }
}

const FREE = slot(11, MONDAY, '08:00')
const FULL = slot(12, MONDAY, '08:15', { available: false })
const MINE = slot(13, TUESDAY, '08:00', { available: false, booked_by_me: true })
const SLOTS = [FREE, FULL, MINE]

function booked(slotId: number): Appointment {
  const chosen = SLOTS.find((s) => s.id === slotId)!
  return {
    id: 42,
    slot_id: slotId,
    start_at: chosen.start_at,
    end_at: chosen.end_at,
    appointment_date: MONDAY,
    booking_date: todayKey(),
    attended: null,
  }
}

function backend(
  book: (body: unknown) => unknown = (body) => booked((body as { slot_id: number }).slot_id),
) {
  return fakeBackend({
    ...signIn(PATIENT),
    'GET /slots': (_, url) => (url.searchParams.get('date_from') === MONDAY ? SLOTS : []),
    'POST /appointments': book,
  })
}

const cell = (day: string, clock: string) =>
  screen.getByRole('button', { name: new RegExp(`^${formatLongDate(day)} ${clock}:`) })

async function openBooking() {
  const user = userEvent.setup()
  renderApp('/randevu-al')
  await screen.findByRole('group', { name: 'Haftalık takvim' })
  return user
}

describe('booking', () => {
  it('shows the week of the department with free, full, own and closed times only', async () => {
    const calls = backend()
    await openBooking()

    expect(cell(MONDAY, '08:00')).toHaveAccessibleName(`${formatLongDate(MONDAY)} 08:00: Müsait`)
    expect(cell(MONDAY, '08:00')).toBeEnabled()
    expect(cell(MONDAY, '08:15')).toHaveAccessibleName(`${formatLongDate(MONDAY)} 08:15: Dolu`)
    expect(cell(MONDAY, '08:15')).toBeDisabled()
    expect(cell(TUESDAY, '08:00')).toHaveTextContent('Randevum')
    expect(cell(TUESDAY, '08:15')).toHaveAccessibleName(`${formatLongDate(TUESDAY)} 08:15: Kapalı`)
    // Nothing about extra appointments, risks or doctors reaches the patient
    expect(document.body.textContent).not.toMatch(/Ek randevu|risk|\bHekim\b|Branş/i)
    expect(calls.find((c) => c.path === '/slots')?.search).toBe(
      `?date_from=${MONDAY}&date_to=${addDays(MONDAY, 4)}`,
    )
  })

  it('books a free time after confirming the summary', async () => {
    const calls = backend()
    const user = await openBooking()

    await user.click(cell(MONDAY, '08:00'))
    const side = screen.getByRole('complementary', { name: 'Randevu özeti' })
    expect(within(side).getByText(`Hasta ${PATIENT_NUMBER}`)).toBeVisible()
    expect(within(side).getByText(/Aile Hekimliği/)).toBeVisible()
    await user.click(within(side).getByRole('button', { name: 'Randevuyu onayla' }))

    expect(await within(side).findByRole('heading', { name: 'Randevunuz alındı ✓' })).toBeVisible()
    expect(within(side).getByText('R-000042')).toBeVisible()
    expect(calls.find((c) => c.method === 'POST' && c.path === '/appointments')?.body).toEqual({
      slot_id: FREE.id,
    })
    // The week is read again after booking
    expect(calls.filter((c) => c.path === '/slots')).toHaveLength(2)
  })

  it('shows a short message when the time is no longer free', async () => {
    backend(() => ({ status: 409, body: { detail: 'Slot is not available' } }))
    const user = await openBooking()

    await user.click(cell(MONDAY, '08:00'))
    await user.click(screen.getByRole('button', { name: 'Randevuyu onayla' }))

    expect(await screen.findByText('Bu saat dolu, başka bir saat seçin.')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Randevunuz alındı ✓' })).not.toBeInTheDocument()
  })

  it('browses the following weeks but not the past', async () => {
    const calls = backend()
    const user = await openBooking()

    expect(screen.getByRole('button', { name: '‹ Önceki hafta' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Sonraki hafta ›' }))

    expect(await screen.findByText('Bu hafta için açık saat yok.')).toBeVisible()
    expect(calls.at(-1)?.search).toBe(
      `?date_from=${addDays(MONDAY, 7)}&date_to=${addDays(MONDAY, 11)}`,
    )
  })
})
