import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { todayKey } from '../format'
import type { CalendarAppointment, CalendarSlot } from '../types'
import { DOCTOR, fakeBackend, hoursFromNow, plusMinutes, renderApp, signIn } from './backend'

function appointment(id: number, name: string): CalendarAppointment {
  return {
    id,
    patient_name: name,
    patient_age: 34,
    patient_gender: 'F',
    booking_date: todayKey(),
    attended: null,
  }
}

function calendarSlot(
  id: number,
  start: string,
  appointments: CalendarAppointment[],
): CalendarSlot {
  return {
    slot_id: id,
    start_at: start,
    end_at: plusMinutes(start, 20),
    max_patients: 2,
    appointments,
  }
}

// Data of a fixed day returned by the fake backend; only the start times matter for marking
const CALENDAR = [
  calendarSlot(1, hoursFromNow(-2), [appointment(10, 'Ayşe Kaya'), appointment(11, 'Ali Şahin')]),
  calendarSlot(2, hoursFromNow(-1), []),
  calendarSlot(3, hoursFromNow(2), [appointment(12, 'Zeynep Çelik')]),
]

describe('doctor patient list', () => {
  it('shows the day and marks attendance', async () => {
    const calls = fakeBackend({
      ...signIn(DOCTOR),
      'GET /doctors/me/calendar': () => CALENDAR,
      'PATCH /appointments/10/attendance': (body) => ({
        ...appointment(10, 'Ayşe Kaya'),
        attended: (body as { attended: boolean }).attended,
      }),
      'PATCH /appointments/11/attendance': (body) => ({
        ...appointment(11, 'Ali Şahin'),
        attended: (body as { attended: boolean }).attended,
      }),
    })
    renderApp('/hasta-listesi')
    const user = userEvent.setup()

    expect(await screen.findByText('Ayşe Kaya')).toBeInTheDocument()
    expect(calls.find((c) => c.path === '/doctors/me/calendar')?.search).toBe(`?date=${todayKey()}`)
    expect(screen.getByText('Boş')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Ayşe Kaya: geldi' }))
    await user.click(screen.getByRole('button', { name: 'Ali Şahin: gelmedi' }))

    expect(await screen.findByRole('button', { name: 'Ayşe Kaya: geldi' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(screen.getByRole('button', { name: 'Ali Şahin: gelmedi' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    const ayseRow = screen.getByText('Ayşe Kaya').closest('tr')!
    expect(within(ayseRow).getAllByText('Geldi').length).toBeGreaterThan(0)
    expect(calls.filter((c) => c.method === 'PATCH').map((c) => [c.path, c.body])).toEqual([
      ['/appointments/10/attendance', { attended: true }],
      ['/appointments/11/attendance', { attended: false }],
    ])
  })

  it('cannot mark an appointment that has not started', async () => {
    fakeBackend({ ...signIn(DOCTOR), 'GET /doctors/me/calendar': () => CALENDAR })
    renderApp('/hasta-listesi')

    expect(await screen.findByRole('button', { name: 'Zeynep Çelik: geldi' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Zeynep Çelik: gelmedi' })).toBeDisabled()
  })

  it('opens another day', async () => {
    const calls = fakeBackend({ ...signIn(DOCTOR), 'GET /doctors/me/calendar': () => [] })
    renderApp('/hasta-listesi')
    const user = userEvent.setup()

    expect(await screen.findByText('Bu gün için tanımlı slot yok.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Sonraki gün' }))

    const days = calls.filter((c) => c.path === '/doctors/me/calendar').map((c) => c.search)
    expect(days).toHaveLength(2)
    expect(days[1]).not.toBe(days[0])
  })
})
