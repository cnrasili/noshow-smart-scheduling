import { useCallback, useEffect, useState } from 'react'
import { api, errorText } from '../../api'
import {
  addDays,
  appointmentNumber,
  dayParts,
  formatLongDate,
  formatShortDate,
  formatTime,
  formatTimeRange,
  genderLabel,
  hasStarted,
  relativeDayLabel,
  todayKey,
  weekStart,
} from '../../format'
import type { AgendaDay, CalendarAppointment, CalendarSlot } from '../../types'
import { Notice, PageHeader, Status, type NoticeState } from '../../ui'

function AttendanceStatus({
  appointment,
  started,
}: {
  appointment: CalendarAppointment
  started: boolean
}) {
  if (appointment.attended === true) return <Status tone="ok">Geldi</Status>
  if (appointment.attended === false) return <Status tone="miss">Gelmedi</Status>
  return started ? (
    <Status tone="warn">İşaretlenmedi</Status>
  ) : (
    <Status tone="neutral">Bekleniyor</Status>
  )
}

function Summary({ calendar }: { calendar: CalendarSlot[] }) {
  const appointments = calendar.flatMap((slot) => slot.appointments)
  const items = [
    ['Slot', calendar.length],
    ['Randevulu', appointments.length],
    ['Geldi', appointments.filter((a) => a.attended === true).length],
    ['Gelmedi', appointments.filter((a) => a.attended === false).length],
    ['Kayıt bekleyen', appointments.filter((a) => a.attended === null).length],
  ] as const
  return (
    <dl className="summary">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  )
}

// Days shown in the upcoming appointments, today included
const UPCOMING_DAYS = 14

function WeekOverview({
  week,
  day,
  onSelect,
}: {
  week: AgendaDay[] | null
  day: string
  onSelect: (day: string) => void
}) {
  if (week === null) return <p className="muted panel-body">Hafta yükleniyor…</p>
  return (
    <div className="panel-body">
      <div className="day-strip" role="group" aria-label="Haftanın günleri">
        {week.map((entry) => {
          const parts = dayParts(entry.date)
          const count = entry.appointments.length
          return (
            <button
              key={entry.date}
              type="button"
              aria-pressed={entry.date === day}
              aria-label={`${formatLongDate(entry.date)}: ${
                entry.slot_count === 0 ? 'çalışma yok' : `${count} randevu`
              }`}
              className={`day-option ${entry.date === day ? 'is-active' : ''}`}
              onClick={() => onSelect(entry.date)}
            >
              <span className="day-weekday">{parts.weekday}</span>
              <span className="day-number">{parts.day}</span>
              <span className="day-month">{parts.month}</span>
              <span
                className={`day-free ${entry.slot_count === 0 || count === 0 ? 'is-full' : ''}`}
              >
                {entry.slot_count === 0 ? 'Çalışma yok' : `${count} randevu`}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

function UpcomingAppointments({
  days,
  onSelect,
}: {
  days: AgendaDay[] | null
  onSelect: (day: string) => void
}) {
  const booked = days?.filter((entry) => entry.appointments.length > 0) ?? []
  return (
    <section className="panel" aria-labelledby="upcoming-title">
      <div className="panel-head">
        <h2 id="upcoming-title">Yaklaşan randevular</h2>
        <p className="muted">Bugünden itibaren {UPCOMING_DAYS} gün</p>
      </div>
      {days === null ? (
        <p className="muted panel-body">Yükleniyor…</p>
      ) : booked.length === 0 ? (
        <p className="muted panel-body">Önümüzdeki iki haftada randevu yok.</p>
      ) : (
        <div className="upcoming">
          {booked.map((entry) => {
            const relative = relativeDayLabel(entry.date)
            return (
              <div key={entry.date} className="upcoming-day">
                <h3>
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => onSelect(entry.date)}
                  >
                    {formatLongDate(entry.date)}
                  </button>
                  {relative && <Status tone="info">{relative}</Status>}
                  <span className="muted">{entry.appointments.length} randevu</span>
                </h3>
                <table className="table upcoming-table">
                  <thead>
                    <tr>
                      <th>Saat</th>
                      <th>Hasta</th>
                      <th>Randevu no</th>
                    </tr>
                  </thead>
                  <tbody>
                    {entry.appointments.map((appointment) => (
                      <tr key={appointment.id}>
                        <td data-label="Saat" className="mono">
                          {formatTime(appointment.start_at)}
                        </td>
                        <td data-label="Hasta" className="strong">
                          {appointment.patient_name}{' '}
                          {appointment.extra && <Status tone="warn">Ek randevu</Status>}
                        </td>
                        <td data-label="Randevu no" className="mono">
                          {appointmentNumber(appointment.id)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          })}
        </div>
      )}
    </section>
  )
}

export function WorklistPage() {
  const [day, setDay] = useState(todayKey)
  const [calendar, setCalendar] = useState<CalendarSlot[] | null>(null)
  const [week, setWeek] = useState<AgendaDay[] | null>(null)
  const [upcoming, setUpcoming] = useState<AgendaDay[] | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [notice, setNotice] = useState<NoticeState | null>(null)

  const closeNotice = useCallback(() => setNotice(null), [])
  const showError = (error: unknown) => setNotice({ kind: 'error', text: errorText(error) })

  useEffect(() => {
    // Ignore a late response after the day has changed
    let current = true
    api
      .calendar(day)
      .then((next) => {
        if (current) setCalendar(next)
      })
      .catch(showError)
    return () => {
      current = false
    }
  }, [day])

  const monday = weekStart(day)
  useEffect(() => {
    let current = true
    api
      .agenda(monday, addDays(monday, 6))
      .then((next) => {
        if (current) setWeek(next)
      })
      .catch(showError)
    return () => {
      current = false
    }
  }, [monday])

  useEffect(() => {
    const today = todayKey()
    api
      .agenda(today, addDays(today, UPCOMING_DAYS - 1))
      .then(setUpcoming)
      .catch(showError)
  }, [])

  function changeDay(next: string) {
    if (!next) return
    if (weekStart(next) !== monday) setWeek(null)
    setCalendar(null)
    setDay(next)
  }

  async function mark(appointment: CalendarAppointment, attended: boolean) {
    setBusyId(appointment.id)
    try {
      const updated = await api.markAttendance(appointment.id, attended)
      setCalendar(
        (slots) =>
          slots?.map((slot) => ({
            ...slot,
            appointments: slot.appointments.map((a) => (a.id === updated.id ? updated : a)),
          })) ?? null,
      )
    } catch (error) {
      showError(error)
    } finally {
      setBusyId(null)
    }
  }

  return (
    <>
      <Notice notice={notice} onClose={closeNotice} />
      <PageHeader title="Hasta Listesi" description="Günlük randevular ve geliş kaydı">
        <div className="date-nav">
          <button type="button" onClick={() => changeDay(addDays(day, -1))} aria-label="Önceki gün">
            ‹
          </button>
          <input
            type="date"
            value={day}
            onChange={(event) => changeDay(event.target.value)}
            aria-label="Gün"
          />
          <button type="button" onClick={() => changeDay(addDays(day, 1))} aria-label="Sonraki gün">
            ›
          </button>
          <button type="button" onClick={() => changeDay(todayKey())} disabled={day === todayKey()}>
            Bugün
          </button>
        </div>
      </PageHeader>

      <div className="stack">
        <section className="panel" aria-labelledby="week-title">
          <div className="panel-head">
            <h2 id="week-title">Hafta</h2>
          </div>
          <WeekOverview week={week} day={day} onSelect={changeDay} />
        </section>

        <section className="panel" aria-labelledby="day-title">
          <div className="panel-head day-head">
            <h2 id="day-title" className="day-title">
              {formatLongDate(day)}
            </h2>
            {relativeDayLabel(day) && <Status tone="info">{relativeDayLabel(day)}</Status>}
          </div>
          {calendar === null ? (
            <p className="muted panel-body">Yükleniyor…</p>
          ) : calendar.length === 0 ? (
            <p className="muted panel-body">Bu gün için tanımlı slot yok.</p>
          ) : (
            <>
              <Summary calendar={calendar} />
              <table className="table worklist">
                <thead>
                  <tr>
                    <th>Saat</th>
                    <th>Randevu no</th>
                    <th>Hasta</th>
                    <th>Yaş / Cinsiyet</th>
                    <th>Alınma tarihi</th>
                    <th>Durum</th>
                    <th className="cell-actions">Geliş kaydı</th>
                  </tr>
                </thead>
                <tbody>
                  {calendar.flatMap((slot) => {
                    const time = formatTimeRange(slot.start_at, slot.end_at)
                    const started = hasStarted(slot.start_at)
                    if (slot.appointments.length === 0) {
                      return [
                        <tr key={`slot-${slot.slot_id}`} className="row-empty">
                          <td data-label="Saat" className="mono">
                            {time}
                          </td>
                          <td colSpan={6} className="muted">
                            Boş
                          </td>
                        </tr>,
                      ]
                    }
                    // Later patients in a slot came in as overbooks
                    return slot.appointments.map((appointment, index) => (
                      <tr key={appointment.id}>
                        <td data-label="Saat" className="mono">
                          {time}
                        </td>
                        <td data-label="Randevu no" className="mono">
                          {appointmentNumber(appointment.id)}
                        </td>
                        <td data-label="Hasta" className="strong">
                          {appointment.patient_name}{' '}
                          {index > 0 && <Status tone="warn">Ek randevu</Status>}
                        </td>
                        <td data-label="Yaş / Cinsiyet">
                          {appointment.patient_age} · {genderLabel(appointment.patient_gender)}
                        </td>
                        <td data-label="Alınma tarihi">
                          {formatShortDate(appointment.booking_date)}
                        </td>
                        <td data-label="Durum">
                          <AttendanceStatus appointment={appointment} started={started} />
                        </td>
                        <td data-label="Geliş kaydı" className="cell-actions">
                          <div
                            className="segmented"
                            role="group"
                            aria-label={`${appointment.patient_name}: geliş kaydı`}
                          >
                            <button
                              type="button"
                              className={appointment.attended === true ? 'is-on is-ok' : ''}
                              aria-pressed={appointment.attended === true}
                              aria-label={`${appointment.patient_name}: geldi`}
                              onClick={() => mark(appointment, true)}
                              disabled={!started || busyId === appointment.id}
                              title={started ? undefined : 'Randevu saati gelince işaretlenebilir'}
                            >
                              Geldi
                            </button>
                            <button
                              type="button"
                              className={appointment.attended === false ? 'is-on is-miss' : ''}
                              aria-pressed={appointment.attended === false}
                              aria-label={`${appointment.patient_name}: gelmedi`}
                              onClick={() => mark(appointment, false)}
                              disabled={!started || busyId === appointment.id}
                              title={started ? undefined : 'Randevu saati gelince işaretlenebilir'}
                            >
                              Gelmedi
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  })}
                </tbody>
              </table>
            </>
          )}
        </section>

        <UpcomingAppointments days={upcoming} onSelect={changeDay} />
      </div>
    </>
  )
}
