import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { addDays, formatLongDate, todayKey, weekStart } from '../format'
import type { AgendaAppointment, AgendaDay, CalendarAppointment, CalendarSlot } from '../types'
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

function agendaAppointment(id: number, name: string, extra = false): AgendaAppointment {
  const start = `${addDays(todayKey(), 0)}T07:00:00Z`
  return {
    id,
    slot_id: id,
    start_at: start,
    end_at: plusMinutes(start, 20),
    patient_name: name,
    extra,
  }
}

/** Agenda answer: every day of the range, with slots on weekdays and the given appointments. */
function agenda(booked: Record<string, AgendaAppointment[]> = {}) {
  return (_: unknown, url: URL): AgendaDay[] => {
    const from = url.searchParams.get('date_from')!
    const to = url.searchParams.get('date_to')!
    const days: AgendaDay[] = []
    for (let key = from; key <= to; key = addDays(key, 1)) {
      const weekday = (new Date(`${key}T12:00:00Z`).getUTCDay() + 6) % 7
      days.push({ date: key, slot_count: weekday < 5 ? 9 : 0, appointments: booked[key] ?? [] })
    }
    return days
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
      'GET /doctors/me/agenda': agenda(),
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
    fakeBackend({
      ...signIn(DOCTOR),
      'GET /doctors/me/agenda': agenda(),
      'GET /doctors/me/calendar': () => CALENDAR,
    })
    renderApp('/hasta-listesi')

    expect(await screen.findByRole('button', { name: 'Zeynep Çelik: geldi' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Zeynep Çelik: gelmedi' })).toBeDisabled()
  })

  it('opens another day', async () => {
    const calls = fakeBackend({
      ...signIn(DOCTOR),
      'GET /doctors/me/agenda': agenda(),
      'GET /doctors/me/calendar': () => [],
    })
    renderApp('/hasta-listesi')
    const user = userEvent.setup()

    expect(await screen.findByText('Bu gün için tanımlı slot yok.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Sonraki gün' }))

    const days = calls.filter((c) => c.path === '/doctors/me/calendar').map((c) => c.search)
    expect(days).toHaveLength(2)
    expect(days[1]).not.toBe(days[0])
  })

  it('shows the selected date, the appointment number, the booking date and extra appointments', async () => {
    fakeBackend({
      ...signIn(DOCTOR),
      'GET /doctors/me/agenda': agenda(),
      'GET /doctors/me/calendar': () => CALENDAR,
    })
    renderApp('/hasta-listesi')

    const heading = await screen.findByRole('heading', { name: formatLongDate(todayKey()) })
    expect(within(heading.parentElement!).getByText('Bugün')).toBeInTheDocument()
    expect(await screen.findByRole('columnheader', { name: 'Alınma tarihi' })).toBeInTheDocument()
    expect(screen.queryByRole('columnheader', { name: 'Randevu alma' })).not.toBeInTheDocument()
    const ayseRow = screen.getByText('Ayşe Kaya').closest('tr')!
    expect(within(ayseRow).getByText('R-000010')).toBeInTheDocument()
    expect(within(ayseRow).queryByText('Ek randevu')).not.toBeInTheDocument()
    // Ali Şahin was booked into Ayşe Kaya's slot
    const aliRow = screen.getByText('Ali Şahin').closest('tr')!
    expect(within(aliRow).getByText('Ek randevu')).toBeInTheDocument()
  })

  it('shows the week with appointment counts and opens a day from it', async () => {
    const monday = weekStart(todayKey())
    const wednesday = addDays(monday, 2)
    const calls = fakeBackend({
      ...signIn(DOCTOR),
      'GET /doctors/me/agenda': agenda({
        [wednesday]: [agendaAppointment(30, 'Ayşe Kaya'), agendaAppointment(31, 'Ali Şahin')],
      }),
      'GET /doctors/me/calendar': () => [],
    })
    renderApp('/hasta-listesi')
    const user = userEvent.setup()

    const week = await screen.findByRole('group', { name: 'Haftanın günleri' })
    const saturday = addDays(monday, 5)
    expect(
      within(week).getByRole('button', { name: `${formatLongDate(wednesday)}: 2 randevu` }),
    ).toBeInTheDocument()
    expect(
      within(week).getByRole('button', { name: `${formatLongDate(saturday)}: çalışma yok` }),
    ).toBeInTheDocument()
    expect(within(week).getAllByRole('button')).toHaveLength(7)

    await user.click(
      within(week).getByRole('button', { name: `${formatLongDate(wednesday)}: 2 randevu` }),
    )

    expect(
      await screen.findByRole('heading', { name: formatLongDate(wednesday) }),
    ).toBeInTheDocument()
    expect(calls.filter((c) => c.path === '/doctors/me/calendar').at(-1)?.search).toBe(
      `?date=${wednesday}`,
    )
  })

  it('lists the next two weeks and opens a day two weeks ahead', async () => {
    const later = addDays(todayKey(), 13)
    const calls = fakeBackend({
      ...signIn(DOCTOR),
      'GET /doctors/me/agenda': agenda({
        [later]: [
          agendaAppointment(373, 'Zeynep Çelik'),
          agendaAppointment(374, 'Ali Şahin', true),
        ],
      }),
      'GET /doctors/me/calendar': () => [],
    })
    renderApp('/hasta-listesi')
    const user = userEvent.setup()

    const upcoming = await screen.findByRole('region', { name: 'Yaklaşan randevular' })
    const dayButton = await within(upcoming).findByRole('button', { name: formatLongDate(later) })
    expect(within(upcoming).getByText('R-000373')).toBeInTheDocument()
    expect(within(upcoming).getByText('Zeynep Çelik')).toBeInTheDocument()
    expect(within(upcoming).getByText('Ek randevu')).toBeInTheDocument()
    const ranges = calls.filter((c) => c.path === '/doctors/me/agenda').map((c) => c.search)
    expect(ranges).toContain(`?date_from=${todayKey()}&date_to=${later}`)

    await user.click(dayButton)

    expect(await screen.findByRole('heading', { name: formatLongDate(later) })).toBeInTheDocument()
    expect(calls.filter((c) => c.path === '/doctors/me/calendar').at(-1)?.search).toBe(
      `?date=${later}`,
    )
  })
})
