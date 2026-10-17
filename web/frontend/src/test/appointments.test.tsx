import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import type { Appointment } from '../types'
import { PATIENT, clinicTime, fakeBackend, plusMinutes, renderApp, signIn } from './backend'

const START = clinicTime(3, '10:00')
const UPCOMING: Appointment = {
  id: 5,
  slot_id: 11,
  start_at: START,
  end_at: plusMinutes(START, 15),
  appointment_date: START.slice(0, 10),
  booking_date: new Date().toISOString().slice(0, 10),
  attended: null,
}

describe('my appointments', () => {
  it('cancels an appointment after confirmation', async () => {
    let appointments = [UPCOMING]
    const calls = fakeBackend({
      ...signIn(PATIENT),
      'GET /patients/me/appointments': () => appointments,
      'DELETE /appointments/5': () => {
        appointments = []
        return { status: 204 }
      },
    })
    renderApp('/randevularim')
    const user = userEvent.setup()

    expect(await screen.findByText('R-000005')).toBeInTheDocument()
    expect(screen.queryByRole('columnheader', { name: /Hekim|Branş/ })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'İptal et' }))
    expect(screen.getByText('İptal edilsin mi?')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Evet, iptal et' }))

    expect(
      await screen.findByText('R-000005 numaralı randevunuz iptal edildi.'),
    ).toBeInTheDocument()
    expect(await screen.findByText('Aktif randevunuz bulunmuyor.')).toBeInTheDocument()
    expect(calls.some((c) => c.method === 'DELETE' && c.path === '/appointments/5')).toBe(true)
  })

  it('keeps the appointment when the patient changes their mind', async () => {
    const calls = fakeBackend({
      ...signIn(PATIENT),
      'GET /patients/me/appointments': () => [UPCOMING],
    })
    renderApp('/randevularim')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'İptal et' }))
    await user.click(screen.getByRole('button', { name: 'Vazgeç' }))

    expect(screen.getByText('R-000005')).toBeInTheDocument()
    expect(calls.some((c) => c.method === 'DELETE')).toBe(false)
  })
})
