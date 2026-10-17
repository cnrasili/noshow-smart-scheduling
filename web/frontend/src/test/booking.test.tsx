import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { formatTime } from '../format'
import type { Appointment, Slot } from '../types'
import { PATIENT, clinicTime, fakeBackend, plusMinutes, renderApp, signIn } from './backend'

function slot(id: number, start: string, booked: number, extra: Partial<Slot> = {}): Slot {
  return {
    id,
    start_at: start,
    end_at: plusMinutes(start, 15),
    max_patients: 2,
    booked_count: booked,
    available: booked < 2,
    booked_by_me: false,
    ...extra,
  }
}

const FREE = slot(11, clinicTime(2, '09:00'), 0)
const EXTRA = slot(12, clinicTime(2, '09:15'), 1)
const TAKEN = slot(13, clinicTime(2, '09:30'), 2)
const SLOTS = [FREE, EXTRA, TAKEN]

function booked(slotId: number): Appointment {
  const chosen = SLOTS.find((s) => s.id === slotId)!
  return {
    id: 42,
    slot_id: slotId,
    start_at: chosen.start_at,
    end_at: chosen.end_at,
    appointment_date: chosen.start_at.slice(0, 10),
    booking_date: new Date().toISOString().slice(0, 10),
    attended: null,
  }
}

function backend(
  book: (body: unknown) => unknown = (body) => booked((body as { slot_id: number }).slot_id),
) {
  return fakeBackend({
    ...signIn(PATIENT),
    'GET /slots': () => SLOTS,
    'POST /appointments': book,
  })
}

async function openBooking() {
  const user = userEvent.setup()
  renderApp('/online-randevu')
  await screen.findByRole('listbox', { name: 'Gün seçimi' })
  return user
}

const timeButton = (iso: string) => screen.getByRole('button', { name: formatTime(iso) })

describe('booking', () => {
  it('books a free slot of the department after choosing day and time', async () => {
    const calls = backend()
    const user = await openBooking()

    // One department: nothing to choose but the day and the time
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
    expect(screen.queryByText(/\bHekim\b|Branş/)).not.toBeInTheDocument()

    await user.click(screen.getAllByRole('option')[0])
    await user.click(timeButton(FREE.start_at))
    expect(screen.getByText('Bilgileri kontrol edip randevunuzu onaylayın.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Randevuyu onayla' }))

    const slip = await screen.findByRole('heading', { name: 'Randevunuz oluşturuldu' })
    const section = within(slip.closest('section')!)
    expect(section.getByText('R-000042')).toBeInTheDocument()
    expect(section.getByText('Aile Hekimliği')).toBeInTheDocument()
    expect(calls.find((c) => c.method === 'POST' && c.path === '/appointments')?.body).toEqual({
      slot_id: FREE.id,
    })
    expect(calls.filter((c) => c.path === '/slots').map((c) => c.search)).toEqual(['', ''])
  })

  it('offers a partly booked slot as an extra appointment', async () => {
    backend()
    const user = await openBooking()

    const extra = timeButton(EXTRA.start_at)
    expect(extra).toHaveClass('time-extra')
    expect(extra).toHaveAttribute('title', 'Ek randevu')
    expect(timeButton(TAKEN.start_at)).toBeDisabled()

    await user.click(extra)

    expect(screen.getByText(/Bu saat için ek randevu talep ediyorsunuz/)).toBeInTheDocument()
  })

  it('shows a short message when the extra appointment is refused', async () => {
    backend(() => ({ status: 409, body: { detail: 'Slot is not available' } }))
    const user = await openBooking()

    await user.click(timeButton(EXTRA.start_at))
    await user.click(screen.getByRole('button', { name: 'Randevuyu onayla' }))

    expect(await screen.findByText('Bu saat dolu, başka bir saat seçin.')).toBeInTheDocument()
    expect(
      screen.queryByRole('heading', { name: 'Randevunuz oluşturuldu' }),
    ).not.toBeInTheDocument()
  })
})
