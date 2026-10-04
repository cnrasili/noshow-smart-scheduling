import { useCallback, useEffect, useState } from 'react'
import { api, errorText } from '../../api'
import {
  addDays,
  formatLongDate,
  formatShortDate,
  formatTimeRange,
  genderLabel,
  hasStarted,
  todayKey,
} from '../../format'
import type { CalendarAppointment, CalendarSlot } from '../../types'
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

export function WorklistPage() {
  const [day, setDay] = useState(todayKey)
  const [calendar, setCalendar] = useState<CalendarSlot[] | null>(null)
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

  function changeDay(next: string) {
    if (!next) return
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
      <PageHeader title="Hasta Listesi" description={formatLongDate(day)}>
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

      <section className="panel">
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
                  <th>Hasta</th>
                  <th>Yaş / Cinsiyet</th>
                  <th>Randevu alma</th>
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
                        <td colSpan={5} className="muted">
                          Boş
                        </td>
                      </tr>,
                    ]
                  }
                  return slot.appointments.map((appointment) => (
                    <tr key={appointment.id}>
                      <td data-label="Saat" className="mono">
                        {time}
                      </td>
                      <td data-label="Hasta" className="strong">
                        {appointment.patient_name}
                      </td>
                      <td data-label="Yaş / Cinsiyet">
                        {appointment.patient_age} · {genderLabel(appointment.patient_gender)}
                      </td>
                      <td data-label="Randevu alma">{formatShortDate(appointment.booking_date)}</td>
                      <td data-label="Durum">
                        <AttendanceStatus appointment={appointment} started={started} />
                      </td>
                      <td data-label="Geliş kaydı" className="cell-actions">
                        <div className="segmented" aria-label="Geliş kaydı">
                          <button
                            type="button"
                            className={appointment.attended === true ? 'is-on is-ok' : ''}
                            aria-pressed={appointment.attended === true}
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
    </>
  )
}
