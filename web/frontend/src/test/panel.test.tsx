import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { addDays, formatLongDate, todayKey, weekStart } from '../format'
import type { AgendaDay, CalendarAppointment, CalendarSlot, DatasetRecord } from '../types'
import { DEPARTMENT, fakeBackend, renderApp, signIn } from './backend'

const TODAY = todayKey()
const DATA_DAY = '2016-06-07'

const at = (day: string, clock: string) => new Date(`${day}T${clock}:00+03:00`).toISOString()

function appointment(id: number, number: string, attended: boolean | null = null) {
  return {
    id,
    patient_name: `Hasta ${number}`,
    patient_age: 30 + id,
    patient_gender: 'F',
    booking_date: TODAY,
    attended,
  } satisfies CalendarAppointment
}

function calendarSlot(id: number, day: string, clock: string, appointments: CalendarAppointment[]) {
  return {
    slot_id: id,
    start_at: at(day, clock),
    end_at: at(day, clock),
    max_patients: 2,
    appointments,
  } satisfies CalendarSlot
}

/** Agenda answer: every day of the range without appointments. */
const agenda = (_: unknown, url: URL): AgendaDay[] => {
  const days: AgendaDay[] = []
  for (
    let key = url.searchParams.get('date_from')!;
    key <= url.searchParams.get('date_to')!;
    key = addDays(key, 1)
  ) {
    days.push({ date: key, slot_count: 16, appointments: [] })
  }
  return days
}

const RECORDS: DatasetRecord[] = [
  { patient_name: 'Hasta 111', patient_age: 9, attended: false },
  { patient_name: 'Hasta 222', patient_age: 63, attended: true },
]

function backend(today: CalendarSlot[], others: Record<string, CalendarSlot[]> = {}) {
  return fakeBackend({
    ...signIn(DEPARTMENT),
    'GET /doctors/me/calendar': (_, url) => {
      const day = url.searchParams.get('date')!
      return day === TODAY ? today : (others[day] ?? [])
    },
    'GET /doctors/me/agenda': agenda,
    'GET /department/dataset-days': () => [{ date: DATA_DAY, appointments: 2, missed: 1 }],
    'GET /department/dataset-days/2016-06-07': () => RECORDS,
  })
}

const column = (name: string) => screen.getByRole('region', { name })

describe('department panel', () => {
  it("shows today's program in waiting, attended and missed columns", async () => {
    backend([
      calendarSlot(1, TODAY, '08:00', [appointment(10, '1421986987763')]),
      calendarSlot(2, TODAY, '08:15', [appointment(11, '93779.52927', true)]),
      calendarSlot(3, TODAY, '08:30', []),
    ])
    renderApp('/departman')

    expect(await screen.findByRole('heading', { name: formatLongDate(TODAY) })).toBeVisible()
    await screen.findByRole('region', { name: 'Bekleyen' })
    expect(await within(column('Bekleyen')).findByText(/Hasta 1421986987763/)).toBeVisible()
    expect(within(column('Geldi')).getByText(/Hasta 93779\.52927/)).toBeVisible()
    expect(within(column('Gelmedi')).queryAllByRole('listitem')).toHaveLength(0)
    const side = screen.getByRole('complementary', { name: 'Sıradaki hasta' })
    expect(within(side).getByText(/Hasta 1421986987763/)).toBeVisible()
    expect(within(side).getByText('40 yaşında')).toBeVisible()
    // The department sees no overbooking or risk information
    expect(document.body.textContent).not.toMatch(/Ek randevu|risk|overbook/i)
  })

  it('marks attendance for today and takes a mark back', async () => {
    let attended: boolean | null = null
    const calls = fakeBackend({
      ...signIn(DEPARTMENT),
      'GET /doctors/me/calendar': () => [
        calendarSlot(1, TODAY, '08:00', [appointment(10, '1421986987763', attended)]),
      ],
      'GET /doctors/me/agenda': agenda,
      'GET /department/dataset-days': () => [],
      'PATCH /appointments/10/attendance': (body) => {
        attended = (body as { attended: boolean | null }).attended
        return appointment(10, '1421986987763', attended)
      },
    })
    renderApp('/departman')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Hasta 1421986987763: gelmedi' }))
    expect(await within(column('Gelmedi')).findByText(/Hasta 1421986987763/)).toBeVisible()
    expect(screen.getByText('Bekleyen hasta yok.')).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Hasta 1421986987763: geri al' }))

    expect(await within(column('Bekleyen')).findByText(/Hasta 1421986987763/)).toBeVisible()
    expect(
      calls
        .filter((c) => c.method === 'PATCH')
        .map((c) => (c.body as { attended: unknown }).attended),
    ).toEqual([false, null])
  })

  it('shows a dataset day read-only with the recorded outcome', async () => {
    backend([])
    renderApp('/departman')
    const user = userEvent.setup()

    const select = await screen.findByRole('combobox', { name: 'Veri seti günü' })
    await screen.findByRole('option', { name: formatLongDate(DATA_DAY) })
    await user.selectOptions(select, DATA_DAY)

    expect(await screen.findByRole('heading', { name: formatLongDate(DATA_DAY) })).toBeVisible()
    expect(await within(column('Gelmedi (kayıt)')).findByText(/Hasta 111/)).toBeVisible()
    expect(within(column('Geldi (kayıt)')).getByText(/Hasta 222/)).toBeVisible()
    expect(screen.getByText('%50')).toBeVisible()
    expect(screen.queryByRole('button', { name: /geldi|gelmedi/ })).not.toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: `${formatLongDate(DATA_DAY)}: kayıt`, pressed: true }),
    ).toBeVisible()
  })

  it('shows the bookings of another day read-only', async () => {
    const nextMonday = addDays(weekStart(TODAY), 7)
    backend([], {
      [nextMonday]: [calendarSlot(5, nextMonday, '09:00', [appointment(20, '26886125921145')])],
    })
    renderApp('/departman')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Sonraki hafta ›' }))
    await user.click(
      screen.getByRole('button', { name: new RegExp(`^${formatLongDate(addDays(TODAY, 7))}`) }),
    )
    if (addDays(TODAY, 7) !== nextMonday) {
      await user.click(
        screen.getByRole('button', { name: new RegExp(`^${formatLongDate(nextMonday)}`) }),
      )
    }

    expect(await within(column('Randevular')).findByText(/Hasta 26886125921145/)).toBeVisible()
    expect(screen.queryByRole('button', { name: /: geldi$/ })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Bugün' }))
    expect(await screen.findByRole('heading', { name: formatLongDate(TODAY) })).toBeVisible()
  })

  it('keeps the list when the selected day is clicked again', async () => {
    const nextWeek = addDays(TODAY, 7)
    backend([], {
      [nextWeek]: [calendarSlot(5, nextWeek, '09:00', [appointment(20, '26886125921145')])],
    })
    renderApp('/departman')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Sonraki hafta ›' }))
    await screen.findByRole('region', { name: 'Randevular' })
    await user.click(
      screen.getByRole('button', { name: new RegExp(`^${formatLongDate(nextWeek)}`) }),
    )

    expect(await within(column('Randevular')).findByText(/Hasta 26886125921145/)).toBeVisible()
  })

  it('shows long dataset days in parts', async () => {
    const many: DatasetRecord[] = Array.from({ length: 160 }, (_, n) => ({
      patient_name: `Hasta ${n}`,
      patient_age: 40,
      attended: true,
    }))
    fakeBackend({
      ...signIn(DEPARTMENT),
      'GET /doctors/me/calendar': () => [],
      'GET /doctors/me/agenda': agenda,
      'GET /department/dataset-days': () => [{ date: DATA_DAY, appointments: 160, missed: 0 }],
      'GET /department/dataset-days/2016-06-07': () => many,
    })
    renderApp('/departman')
    const user = userEvent.setup()

    await screen.findByRole('option', { name: formatLongDate(DATA_DAY) })
    await user.selectOptions(screen.getByRole('combobox', { name: 'Veri seti günü' }), DATA_DAY)
    const attended = await screen.findByRole('region', { name: 'Geldi (kayıt)' })
    await within(attended).findByText(/Hasta 0$/)

    expect(within(attended).getAllByRole('listitem')).toHaveLength(150)
    await user.click(within(attended).getByRole('button', { name: 'Daha fazla göster (10)' }))
    expect(within(attended).getAllByRole('listitem')).toHaveLength(160)
  })
})
