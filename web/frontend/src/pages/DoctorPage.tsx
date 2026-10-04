import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { api, errorText } from '../api'
import { addDays, formatDay, formatTimeRange, hasStarted, todayKey } from '../format'
import type { CalendarAppointment, CalendarSlot } from '../types'
import { AttendanceBadge, Notice, type NoticeState } from '../ui'

const GENERATION_DAYS = 14

function Summary({ calendar }: { calendar: CalendarSlot[] }) {
  const appointments = calendar.flatMap((slot) => slot.appointments)
  const stats = [
    ['Slot', calendar.length],
    ['Dolu slot', calendar.filter((slot) => slot.appointments.length > 0).length],
    ['Geldi', appointments.filter((a) => a.attended === true).length],
    ['Gelmedi', appointments.filter((a) => a.attended === false).length],
    ['İşaretlenmedi', appointments.filter((a) => a.attended === null).length],
  ] as const
  return (
    <dl className="stats">
      {stats.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  )
}

export function DoctorPage() {
  const [day, setDay] = useState(todayKey)
  const [calendar, setCalendar] = useState<CalendarSlot[] | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [notice, setNotice] = useState<NoticeState | null>(null)
  const [generateFrom, setGenerateFrom] = useState(todayKey)
  const [generateTo, setGenerateTo] = useState(() => addDays(todayKey(), GENERATION_DAYS - 1))
  const [generating, setGenerating] = useState(false)

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

  function replaceAppointment(updated: CalendarAppointment) {
    setCalendar(
      (slots) =>
        slots?.map((slot) => ({
          ...slot,
          appointments: slot.appointments.map((a) => (a.id === updated.id ? updated : a)),
        })) ?? null,
    )
  }

  async function mark(appointment: CalendarAppointment, attended: boolean) {
    setBusyId(appointment.id)
    try {
      replaceAppointment(await api.markAttendance(appointment.id, attended))
    } catch (error) {
      showError(error)
    } finally {
      setBusyId(null)
    }
  }

  async function generate(event: FormEvent) {
    event.preventDefault()
    setGenerating(true)
    try {
      const { created } = await api.generateSlots(generateFrom, generateTo)
      setNotice({
        kind: 'success',
        text: created > 0 ? `${created} yeni slot oluşturuldu.` : 'Bu aralıkta eksik slot yok.',
      })
      setCalendar(await api.calendar(day))
    } catch (error) {
      showError(error)
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="page">
      <Notice notice={notice} onClose={closeNotice} />

      <section className="card">
        <div className="card-head">
          <h2>{formatDay(day)}</h2>
          <div className="actions">
            <button type="button" onClick={() => changeDay(addDays(day, -1))}>
              ‹ Önceki
            </button>
            <input
              type="date"
              value={day}
              onChange={(event) => changeDay(event.target.value)}
              aria-label="Gün"
            />
            <button type="button" onClick={() => changeDay(todayKey())}>
              Bugün
            </button>
            <button type="button" onClick={() => changeDay(addDays(day, 1))}>
              Sonraki ›
            </button>
          </div>
        </div>

        {calendar === null ? (
          <p className="muted">Yükleniyor…</p>
        ) : calendar.length === 0 ? (
          <p className="muted">Bu gün için slot yok.</p>
        ) : (
          <>
            <Summary calendar={calendar} />
            <ul className="list calendar">
              {calendar.map((slot) => (
                <li key={slot.slot_id}>
                  <span className="slot-time">{formatTimeRange(slot.start_at, slot.end_at)}</span>
                  {slot.appointments.length === 0 ? (
                    <span className="muted calendar-patients">Boş</span>
                  ) : (
                    <ul className="calendar-patients">
                      {slot.appointments.map((appointment) => (
                        <li key={appointment.id}>
                          <span className="patient-name">{appointment.patient_name}</span>
                          <AttendanceBadge attended={appointment.attended} />
                          {hasStarted(slot.start_at) ? (
                            <div className="actions">
                              <button
                                type="button"
                                onClick={() => mark(appointment, true)}
                                disabled={
                                  busyId === appointment.id || appointment.attended === true
                                }
                              >
                                Geldi
                              </button>
                              <button
                                type="button"
                                onClick={() => mark(appointment, false)}
                                disabled={
                                  busyId === appointment.id || appointment.attended === false
                                }
                              >
                                Gelmedi
                              </button>
                            </div>
                          ) : (
                            <span className="muted hint">
                              Randevu saati gelince işaretlenebilir
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      <section className="card">
        <h2>Slot üret</h2>
        <p className="muted">
          Haftalık çalışma saatlerinize göre seçilen aralıktaki eksik slotlar oluşturulur. Var olan
          slotlar değişmez.
        </p>
        <form className="generate" onSubmit={generate}>
          <label>
            Başlangıç
            <input
              type="date"
              value={generateFrom}
              min={todayKey()}
              onChange={(event) => setGenerateFrom(event.target.value)}
              required
            />
          </label>
          <label>
            Bitiş
            <input
              type="date"
              value={generateTo}
              min={generateFrom}
              onChange={(event) => setGenerateTo(event.target.value)}
              required
            />
          </label>
          <button type="submit" className="primary" disabled={generating}>
            {generating ? 'Oluşturuluyor…' : 'Slotları oluştur'}
          </button>
        </form>
      </section>
    </div>
  )
}
