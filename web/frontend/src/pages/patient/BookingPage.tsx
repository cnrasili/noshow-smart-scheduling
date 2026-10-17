import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, errorText } from '../../api'
import { DEPARTMENT_NAME } from '../../config'
import {
  appointmentNumber,
  dayKey,
  dayParts,
  formatLongDate,
  formatTime,
  formatTimeRange,
} from '../../format'
import type { Appointment, Slot } from '../../types'
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
          <Field label="Bölüm" value={DEPARTMENT_NAME} />
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

export function BookingPage({ onShowAppointments }: { onShowAppointments: () => void }) {
  const [slots, setSlots] = useState<Slot[] | null>(null)
  const [day, setDay] = useState<string | null>(null)
  const [selected, setSelected] = useState<Slot | null>(null)
  const [booked, setBooked] = useState<Appointment | null>(null)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState<NoticeState | null>(null)

  const closeNotice = useCallback(() => setNotice(null), [])
  const showError = (error: unknown) => setNotice({ kind: 'error', text: errorText(error) })

  // The department's slots; there is only one department
  useEffect(() => {
    api.slots().then(setSlots).catch(showError)
  }, [])

  const days = useMemo(() => groupByDay(slots ?? []), [slots])
  const firstOpenDay = [...days].find(([, list]) => list.some((s) => s.available))?.[0]
  const activeDay = day !== null && days.has(day) ? day : (firstOpenDay ?? null)
  const daySlots = activeDay ? (days.get(activeDay) ?? []) : []

  function chooseDay(key: string) {
    setDay(key)
    setSelected(null)
  }

  async function book() {
    if (!selected) return
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
    setSlots(await api.slots().catch(() => slots))
  }

  return (
    <>
      <Notice notice={notice} onClose={closeNotice} />
      <PageHeader
        title="Online Randevu"
        description={`${DEPARTMENT_NAME} için uygun gün ve saati seçin.`}
      />

      <div className="booking">
        <section className="panel">
          <div className="panel-body stack">
            <div>
              <h2 className="section-title">Gün</h2>
              {slots === null ? (
                <p className="muted">Yükleniyor…</p>
              ) : days.size === 0 ? (
                <p className="muted">Önümüzdeki iki haftada açık gün yok.</p>
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
                  <Field label="Bölüm" value={DEPARTMENT_NAME} />
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
