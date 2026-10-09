import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router'
import { api, errorText } from '../../api'
import {
  appointmentNumber,
  branchLabel,
  dayKey,
  dayParts,
  formatLongDate,
  formatTime,
  formatTimeRange,
} from '../../format'
import type { Appointment, Doctor, Slot } from '../../types'
import { BOOKING_PARAMS } from '../../routes'
import { Notice, PageHeader, type NoticeState } from '../../ui'

type SlotState = 'free' | 'extra' | 'taken' | 'mine'

// An already booked slot below capacity is offered as an extra appointment; the
// overbooking service decides at booking time whether it is granted
function slotState(slot: Slot): SlotState {
  if (slot.booked_by_me) return 'mine'
  if (!slot.available) return 'taken'
  return slot.booked_count > 0 ? 'extra' : 'free'
}

const SLOT_UNAVAILABLE = 'Bu saat dolu, başka bir saat seçin.'

// Backend booking errors are technical English; patients see a short Turkish message
const BOOKING_ERRORS: Record<string, string> = {
  'Slot is not available': SLOT_UNAVAILABLE,
  'Slot is full': SLOT_UNAVAILABLE,
  'Slot is already booked': SLOT_UNAVAILABLE,
  'Slot is no longer available': SLOT_UNAVAILABLE,
  'You already booked this slot': 'Bu saatte zaten randevunuz var.',
  'Slot has already started': 'Bu saatin randevu zamanı geçti, başka bir saat seçin.',
}

function groupByDay(slots: Slot[]): Map<string, Slot[]> {
  const days = new Map<string, Slot[]>()
  for (const slot of slots) {
    const key = dayKey(slot.start_at)
    days.set(key, [...(days.get(key) ?? []), slot])
  }
  return days
}

function Field({ label, value }: { label: string; value: string | undefined }) {
  return (
    <div className="field">
      <dt>{label}</dt>
      <dd>{value ?? '—'}</dd>
    </div>
  )
}

function AppointmentSlip({
  appointment,
  onNew,
  onShowAppointments,
}: {
  appointment: Appointment
  onNew: () => void
  onShowAppointments: () => void
}) {
  return (
    <section className="panel slip" aria-live="polite">
      <div className="panel-head">
        <h2>Randevunuz oluşturuldu</h2>
      </div>
      <div className="panel-body">
        <dl className="fields">
          <Field label="Randevu no" value={appointmentNumber(appointment.id)} />
          <Field label="Branş" value={branchLabel(appointment.doctor_specialty)} />
          <Field label="Hekim" value={appointment.doctor_name} />
          <Field label="Tarih" value={formatLongDate(appointment.appointment_date)} />
          <Field label="Saat" value={formatTimeRange(appointment.start_at, appointment.end_at)} />
        </dl>
        <p className="note">
          Randevu saatinden 15 dakika önce poliklinik bankosuna başvurunuz. Gelemeyecekseniz
          randevunuzu iptal ederek sıranın başka bir hastaya verilmesini sağlayabilirsiniz.
        </p>
        <div className="actions">
          <button type="button" className="primary" onClick={onShowAppointments}>
            Randevularım
          </button>
          <button type="button" onClick={onNew}>
            Yeni randevu
          </button>
        </div>
      </div>
    </section>
  )
}

/** The doctor to start with: the one asked for, else the first of the department asked for. */
function initialDoctor(doctors: Doctor[], department: string | null, doctorId: string | null) {
  return (
    doctors.find((d) => String(d.id) === doctorId) ??
    doctors.find((d) => branchLabel(d.specialty) === department) ??
    doctors[0]
  )
}

export function BookingPage({ onShowAppointments }: { onShowAppointments: () => void }) {
  const [params] = useSearchParams()
  const preselectedDepartment = params.get(BOOKING_PARAMS.department)
  const preselectedDoctor = params.get(BOOKING_PARAMS.doctor)
  const [doctors, setDoctors] = useState<Doctor[]>([])
  const [branch, setBranch] = useState<string | null>(null)
  const [doctorId, setDoctorId] = useState<number | null>(null)
  const [slots, setSlots] = useState<Slot[] | null>(null)
  const [day, setDay] = useState<string | null>(null)
  const [selected, setSelected] = useState<Slot | null>(null)
  const [booked, setBooked] = useState<Appointment | null>(null)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState<NoticeState | null>(null)

  const closeNotice = useCallback(() => setNotice(null), [])
  const showError = (error: unknown) => setNotice({ kind: 'error', text: errorText(error) })

  useEffect(() => {
    api
      .doctors()
      .then((list) => {
        setDoctors(list)
        // A department or doctor chosen on the hospital site is selected; it can be changed
        const first = initialDoctor(list, preselectedDepartment, preselectedDoctor)
        if (first) {
          setBranch(branchLabel(first.specialty))
          setDoctorId(first.id)
        }
      })
      .catch(showError)
  }, [preselectedDepartment, preselectedDoctor])

  useEffect(() => {
    if (doctorId === null) return
    // Ignore a late response after the doctor has changed
    let current = true
    api
      .slots(doctorId)
      .then((next) => {
        if (current) setSlots(next)
      })
      .catch(showError)
    return () => {
      current = false
    }
  }, [doctorId])

  const branches = useMemo(
    // Turkish collation puts "Çocuk…" between "C" and "D", as on the Poliklinikler page
    () =>
      [...new Set(doctors.map((d) => branchLabel(d.specialty)))].sort((a, b) =>
        a.localeCompare(b, 'tr'),
      ),
    [doctors],
  )
  const branchDoctors = doctors.filter((d) => branchLabel(d.specialty) === branch)
  const doctor = doctors.find((d) => d.id === doctorId)
  const days = useMemo(() => groupByDay(slots ?? []), [slots])
  const firstOpenDay = [...days].find(([, list]) => list.some((s) => s.available))?.[0]
  const activeDay = day !== null && days.has(day) ? day : (firstOpenDay ?? null)
  const daySlots = activeDay ? (days.get(activeDay) ?? []) : []

  function chooseBranch(next: string) {
    setBranch(next)
    chooseDoctor(doctors.find((d) => branchLabel(d.specialty) === next)?.id ?? null)
  }

  function chooseDoctor(id: number | null) {
    setDoctorId(id)
    setSlots(null)
    setDay(null)
    setSelected(null)
  }

  function chooseDay(key: string) {
    setDay(key)
    setSelected(null)
  }

  async function book() {
    if (!selected || doctorId === null) return
    setBusy(true)
    try {
      setBooked(await api.book(selected.id))
    } catch (error) {
      const text = errorText(error)
      setNotice({ kind: 'error', text: BOOKING_ERRORS[text] ?? text })
    } finally {
      setSelected(null)
      setBusy(false)
    }
    setSlots(await api.slots(doctorId).catch(() => slots))
  }

  return (
    <>
      <Notice notice={notice} onClose={closeNotice} />
      <PageHeader
        title="Online Randevu"
        description="Branş ve hekim seçip uygun gün ve saati belirleyin."
      />

      <div className="booking">
        <section className="panel">
          <div className="panel-body stack">
            <div className="filters">
              <label>
                Branş
                <select
                  value={branch ?? ''}
                  onChange={(event) => chooseBranch(event.target.value)}
                  disabled={branches.length === 0}
                >
                  {branches.map((name) => (
                    <option key={name} value={name}>
                      {name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Hekim
                <select
                  value={doctorId ?? ''}
                  onChange={(event) => chooseDoctor(Number(event.target.value))}
                  disabled={branchDoctors.length === 0}
                >
                  {branchDoctors.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.full_name}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div>
              <h2 className="section-title">Gün</h2>
              {slots === null ? (
                <p className="muted">Yükleniyor…</p>
              ) : days.size === 0 ? (
                <p className="muted">Bu hekim için önümüzdeki iki haftada açık gün yok.</p>
              ) : (
                <div className="day-strip" role="listbox" aria-label="Gün seçimi">
                  {[...days].map(([key, list]) => {
                    const free = list.filter((s) => slotState(s) === 'free').length
                    const open = list.filter((s) => s.available && !s.booked_by_me).length
                    const parts = dayParts(key)
                    return (
                      <button
                        key={key}
                        type="button"
                        role="option"
                        aria-selected={key === activeDay}
                        className={`day-option ${key === activeDay ? 'is-active' : ''}`}
                        onClick={() => chooseDay(key)}
                      >
                        <span className="day-weekday">{parts.weekday}</span>
                        <span className="day-number">{parts.day}</span>
                        <span className="day-month">{parts.month}</span>
                        <span className={`day-free ${open === 0 ? 'is-full' : ''}`}>
                          {free > 0 ? `${free} boş` : open > 0 ? 'Ek randevu' : 'Dolu'}
                        </span>
                      </button>
                    )
                  })}
                </div>
              )}
            </div>

            {activeDay && (
              <div>
                <h2 className="section-title">Saat · {formatLongDate(activeDay)}</h2>
                <div className="time-grid">
                  {daySlots.map((slot) => {
                    const state = slotState(slot)
                    return (
                      <button
                        key={slot.id}
                        type="button"
                        className={`time time-${state} ${selected?.id === slot.id ? 'is-selected' : ''}`}
                        disabled={state === 'taken' || state === 'mine' || busy}
                        title={state === 'extra' ? 'Ek randevu' : undefined}
                        aria-pressed={selected?.id === slot.id}
                        onClick={() => setSelected(slot)}
                      >
                        {formatTime(slot.start_at)}
                      </button>
                    )
                  })}
                </div>
                <ul className="legend">
                  <li>
                    <span className="swatch time-free" /> Uygun
                  </li>
                  <li>
                    <span className="swatch time-extra" /> Ek randevu
                  </li>
                  <li>
                    <span className="swatch time-taken" /> Dolu
                  </li>
                  <li>
                    <span className="swatch time-mine" /> Sizin randevunuz
                  </li>
                </ul>
              </div>
            )}
          </div>
        </section>

        <aside>
          {booked ? (
            <AppointmentSlip
              appointment={booked}
              onNew={() => setBooked(null)}
              onShowAppointments={onShowAppointments}
            />
          ) : (
            <section className="panel">
              <div className="panel-head">
                <h2>Randevu özeti</h2>
              </div>
              <div className="panel-body">
                <dl className="fields">
                  <Field label="Branş" value={branch ?? undefined} />
                  <Field label="Hekim" value={doctor?.full_name} />
                  <Field
                    label="Tarih"
                    value={selected ? formatLongDate(dayKey(selected.start_at)) : undefined}
                  />
                  <Field
                    label="Saat"
                    value={
                      selected ? formatTimeRange(selected.start_at, selected.end_at) : undefined
                    }
                  />
                </dl>
                <button
                  type="button"
                  className="primary block"
                  onClick={book}
                  disabled={!selected || busy}
                >
                  {busy ? 'Kaydediliyor…' : 'Randevuyu onayla'}
                </button>
                <p className="note">
                  {!selected
                    ? 'Devam etmek için uygun bir saat seçin.'
                    : slotState(selected) === 'extra'
                      ? 'Bu saat için ek randevu talep ediyorsunuz. Uygunluk onay sırasında kontrol edilir.'
                      : 'Bilgileri kontrol edip randevunuzu onaylayın.'}
                </p>
              </div>
            </section>
          )}
        </aside>
      </div>
    </>
  )
}
