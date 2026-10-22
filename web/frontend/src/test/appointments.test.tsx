import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import type { Appointment, SmsMessage } from '../types'
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
const PAST: Appointment = {
  ...UPCOMING,
  id: 4,
  start_at: clinicTime(-3, '10:00'),
  end_at: clinicTime(-3, '10:15'),
}

const MESSAGES: SmsMessage[] = [
  { kind: 'reminder', sent_at: '2026-10-19T06:00:00Z', body: 'Randevunuz yarın.' },
  { kind: 'confirmation', sent_at: '2026-10-17T06:00:00Z', body: 'Randevunuz alındı.' },
]

describe('my appointments', () => {
  it('lists the upcoming appointments and the sent SMS messages', async () => {
    fakeBackend({
      ...signIn(PATIENT),
      'GET /patients/me/appointments': () => [PAST, UPCOMING],
      'GET /patients/me/messages': () => MESSAGES,
    })
    renderApp('/randevularim')

    const appointments = await screen.findByRole('region', { name: 'Randevular' })
    expect(await within(appointments).findByText('R-000005')).toBeVisible()
    expect(within(appointments).queryByText('R-000004')).not.toBeInTheDocument()
    const sms = screen.getByRole('region', { name: 'SMS mesajları' })
    const items = await within(sms).findAllByRole('listitem')
    expect(items.map((item) => item.textContent)).toEqual([
      expect.stringMatching(/^SMS · Randevu hatırlatması.*“Randevunuz yarın\.”$/),
      expect.stringMatching(/^SMS · Randevu onayı.*“Randevunuz alındı\.”$/),
    ])
  })

  it('cancels an appointment after confirmation', async () => {
    let appointments = [UPCOMING]
    const calls = fakeBackend({
      ...signIn(PATIENT),
      'GET /patients/me/appointments': () => appointments,
      'GET /patients/me/messages': () => [],
      'DELETE /appointments/5': () => {
        appointments = []
        return { status: 204 }
      },
    })
    renderApp('/randevularim')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'İptal' }))
    expect(screen.getByText('İptal edilsin mi?')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Evet, iptal et' }))

    expect(
      await screen.findByText('R-000005 numaralı randevunuz iptal edildi.'),
    ).toBeInTheDocument()
    expect(await screen.findByText('Aktif randevunuz yok.')).toBeInTheDocument()
    expect(screen.getByText('SMS yok.')).toBeInTheDocument()
    expect(calls.some((c) => c.method === 'DELETE' && c.path === '/appointments/5')).toBe(true)
  })

  it('keeps the appointment when the patient changes their mind', async () => {
    const calls = fakeBackend({
      ...signIn(PATIENT),
      'GET /patients/me/appointments': () => [UPCOMING],
      'GET /patients/me/messages': () => [],
    })
    renderApp('/randevularim')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'İptal' }))
    await user.click(screen.getByRole('button', { name: 'Vazgeç' }))

    expect(screen.getByText('R-000005')).toBeInTheDocument()
    expect(calls.some((c) => c.method === 'DELETE')).toBe(false)
  })
})
