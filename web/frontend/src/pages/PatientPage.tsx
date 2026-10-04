import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, errorText } from '../api'
import { dayKey, formatDay, formatTime, formatTimeRange, hasStarted } from '../format'
import type { Appointment, Doctor, Slot } from '../types'
import { AttendanceBadge, Notice, type NoticeState } from '../ui'

const load = (doctorId: number) => Promise.all([api.slots(doctorId), api.myAppointments()])

function groupByDay(slots: Slot[]): [string, Slot[]][] {
  const days = new Map<string, Slot[]>()
  for (const slot of slots) {
    const key = dayKey(slot.start_at)
    days.set(key, [...(days.get(key) ?? []), slot])
  }
  return [...days]
}

export function PatientPage() {
  const [doctors, setDoctors] = useState<Doctor[]>([])
  const [doctorId, setDoctorId] = useState<number | null>(null)
  const [slots, setSlots] = useState<Slot[] | null>(null)
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [selected, setSelected] = useState<Slot | null>(null)
  const [busy, setBusy] = useState(false)
  const [confirmCancelId, setConfirmCancelId] = useState<number | null>(null)
  const [notice, setNotice] = useState<NoticeState | null>(null)

  const closeNotice = useCallback(() => setNotice(null), [])
  const showError = (error: unknown) => setNotice({ kind: 'error', text: errorText(error) })

  useEffect(() => {
    api
      .doctors()
      .then((list) => {
        setDoctors(list)
        setDoctorId((current) => current ?? list[0]?.id ?? null)
      })
      .catch(showError)
  }, [])

  useEffect(() => {
    if (doctorId === null) return
    // Ignore a late response after the doctor has changed
    let current = true
    load(doctorId)
      .then(([nextSlots, nextAppointments]) => {
        if (!current) return
        setSlots(nextSlots)
        setAppointments(nextAppointments)
      })
      .catch(showError)
    return () => {
      current = false
    }
  }, [doctorId])

  async function refresh() {
    if (doctorId === null) return
    const [nextSlots, nextAppointments] = await load(doctorId)
    setSlots(nextSlots)
    setAppointments(nextAppointments)
  }

  function chooseDoctor(id: number) {
    setDoctorId(id)
    setSlots(null)
    setSelected(null)
  }

  const days = useMemo(() => groupByDay(slots ?? []), [slots])
  const doctor = doctors.find((d) => d.id === doctorId)
  const upcoming = appointments.filter((a) => !hasStarted(a.start_at))
  const past = appointments.filter((a) => hasStarted(a.start_at)).reverse()

  async function book() {
    if (!selected) return
    setBusy(true)
    try {
      const appointment = await api.book(selected.id)
      setNotice({
        kind: 'success',
        text: `Randevunuz alındı: ${formatDay(dayKey(appointment.start_at))}, ${formatTime(appointment.start_at)}`,
      })
      setSelected(null)
      await refresh()
    } catch (error) {
      showError(error)
      await refresh().catch(() => {})
    } finally {
      setBusy(false)
    }
  }

  async function cancel(appointment: Appointment) {
    setBusy(true)
    setConfirmCancelId(null)
    try {
      await api.cancel(appointment.id)
      setNotice({ kind: 'success', text: 'Randevunuz iptal edildi.' })
      await refresh()
    } catch (error) {
      showError(error)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page">
      <Notice notice={notice} onClose={closeNotice} />

      <section className="card">
        <div className="card-head">
          <h2>Randevu al</h2>
          <label className="inline">
            Doktor
            <select
              value={doctorId ?? ''}
              onChange={(event) => chooseDoctor(Number(event.target.value))}
            >
              {doctors.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.full_name}
                  {d.specialty ? ` · ${d.specialty}` : ''}
                </option>
              ))}
            </select>
          </label>
        </div>

        {slots === null ? (
          <p className="muted">Yükleniyor…</p>
        ) : days.length === 0 ? (
          <p className="muted">Önümüzdeki iki hafta için açık slot yok.</p>
        ) : (
          <div className="days">
            {days.map(([key, daySlots]) => (
              <div key={key} className="day">
                <h3>{formatDay(key)}</h3>
                <div className="slot-grid">
                  {daySlots.map((slot) => {
                    const state = slot.booked_by_me ? 'mine' : slot.available ? 'free' : 'taken'
                    return (
                      <button
                        key={slot.id}
                        type="button"
                        className={`slot slot-${state} ${selected?.id === slot.id ? 'slot-selected' : ''}`}
                        disabled={state !== 'free' || busy}
                        onClick={() => setSelected(slot)}
                        title={state === 'mine' ? 'Randevunuz' : state === 'taken' ? 'Dolu' : 'Boş'}
                      >
                        {formatTime(slot.start_at)}
                      </button>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        )}

        <ul className="legend">
          <li>
            <span className="swatch slot-free" /> Boş
          </li>
          <li>
            <span className="swatch slot-taken" /> Dolu
          </li>
          <li>
            <span className="swatch slot-mine" /> Randevunuz
          </li>
        </ul>

        {selected && (
          <div className="confirm-bar">
            <span>
              <strong>{formatDay(dayKey(selected.start_at))}</strong>,{' '}
              {formatTimeRange(selected.start_at, selected.end_at)} · {doctor?.full_name}
            </span>
            <div className="actions">
              <button type="button" onClick={() => setSelected(null)} disabled={busy}>
                Vazgeç
              </button>
              <button type="button" className="primary" onClick={book} disabled={busy}>
                Randevuyu onayla
              </button>
            </div>
          </div>
        )}
      </section>

      <section className="card">
        <h2>Randevularım</h2>
        {upcoming.length === 0 ? (
          <p className="muted">Yaklaşan randevunuz yok.</p>
        ) : (
          <ul className="list">
            {upcoming.map((appointment) => (
              <li key={appointment.id}>
                <div>
                  <strong>{formatDay(dayKey(appointment.start_at))}</strong>
                  <span className="muted">
                    {formatTimeRange(appointment.start_at, appointment.end_at)} ·{' '}
                    {appointment.doctor_name}
                  </span>
                </div>
                {confirmCancelId === appointment.id ? (
                  <div className="actions">
                    <span className="muted">İptal edilsin mi?</span>
                    <button type="button" onClick={() => setConfirmCancelId(null)} disabled={busy}>
                      Vazgeç
                    </button>
                    <button
                      type="button"
                      className="danger"
                      onClick={() => cancel(appointment)}
                      disabled={busy}
                    >
                      Evet, iptal et
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    className="danger"
                    onClick={() => setConfirmCancelId(appointment.id)}
                    disabled={busy}
                  >
                    İptal et
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}

        {past.length > 0 && (
          <>
            <h3 className="subhead">Geçmiş randevular</h3>
            <ul className="list">
              {past.map((appointment) => (
                <li key={appointment.id}>
                  <div>
                    <strong>{formatDay(dayKey(appointment.start_at))}</strong>
                    <span className="muted">
                      {formatTime(appointment.start_at)} · {appointment.doctor_name}
                    </span>
                  </div>
                  <AttendanceBadge attended={appointment.attended} />
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </div>
  )
}
