import { Fragment, useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router'
import { api, errorText } from '../../api'
import { DEPARTMENT_NAME } from '../../config'
import {
  addDays,
  appointmentNumber,
  dayKey,
  dayParts,
  formatLongDate,
  formatTime,
  todayKey,
  weekLabel,
  weekStart,
} from '../../format'
import { PATHS } from '../../routes'
import type { Appointment, Slot } from '../../types'
import { Notice, PageTop, type NoticeState } from '../../ui'
import { PatientWho } from './PatientWho'

// Monday to Friday
const WORKDAYS = 5
// Weeks ahead the patient can browse
const WEEKS_AHEAD = 8

type CellState = 'open' | 'full' | 'mine' | 'closed'

const CELL_TEXT: Record<CellState, string> = {
  open: 'Müsait',
  full: 'Dolu',
  mine: 'Randevum',
  closed: 'Kapalı',
}

const SLOT_UNAVAILABLE = 'Bu saat dolu, başka bir saat seçin.'

// Backend booking errors are technical English; patients see a short Turkish message
const BOOKING_ERRORS: Record<string, string> = {
  'Slot is not available': SLOT_UNAVAILABLE,
  'Slot is full': SLOT_UNAVAILABLE,
  'Slot is already booked': SLOT_UNAVAILABLE,
  'Slot is no longer available': SLOT_UNAVAILABLE,
  'You already booked this slot': 'Bu saatte zaten randevunuz var.',
  'You already have an appointment on this day':
    'Bu gün için zaten bir randevunuz var. Aynı gün yalnızca bir randevu alabilirsiniz.',
  'Slot has already started': 'Bu saatin randevu zamanı geçti, başka bir saat seçin.',
}

function cellState(slot: Slot | undefined): CellState {
  if (!slot) return 'closed'
  if (slot.booked_by_me) return 'mine'
  return slot.available ? 'open' : 'full'
}

/** The first week to show: this week, or the next one on a weekend. */
function firstWeek(): string {
  const today = todayKey()
  const monday = weekStart(today)
  return today >= addDays(monday, WORKDAYS) ? addDays(monday, 7) : monday
}

export function BookingPage() {
  const minWeek = useMemo(() => firstWeek(), [])
  const [week, setWeek] = useState(minWeek)
  const [slots, setSlots] = useState<Slot[] | null>(null)
  const [selected, setSelected] = useState<Slot | null>(null)
  const [booked, setBooked] = useState<Appointment | null>(null)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState<NoticeState | null>(null)
  const closeNotice = useCallback(() => setNotice(null), [])

  const days = useMemo(() => [...Array(WORKDAYS).keys()].map((n) => addDays(week, n)), [week])
  const load = useCallback(() => api.slots(days[0], days[WORKDAYS - 1]), [days])

  useEffect(() => {
    // Ignore a late answer after the week has changed
    let current = true
    load()
      .then((next) => {
        if (current) setSlots(next)
      })
      .catch((error) => setNotice({ kind: 'error', text: errorText(error) }))
    return () => {
      current = false
    }
  }, [load])

  const byCell = useMemo(
    () =>
      new Map(
        (slots ?? []).map((slot) => [
          `${dayKey(slot.start_at)}|${formatTime(slot.start_at)}`,
          slot,
        ]),
      ),
    [slots],
  )
  const times = useMemo(
    () => [...new Set((slots ?? []).map((slot) => formatTime(slot.start_at)))].sort(),
    [slots],
  )

  function changeWeek(days: number) {
    setWeek((current) => addDays(current, days))
    setSlots(null)
    setSelected(null)
  }

  function choose(slot: Slot) {
    setSelected(slot)
    setBooked(null)
  }

  async function confirm() {
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
    setSlots(await load().catch(() => slots))
  }

  return (
    <>
      <main className="main">
        <Notice notice={notice} onClose={closeNotice} />
        <PageTop
          title="Randevu al"
          description={`${DEPARTMENT_NAME}. Haftalık takvimden müsait bir saati seçin.`}
        />
        <div className="wnav">
          <button type="button" onClick={() => changeWeek(-7)} disabled={week <= minWeek}>
            ‹ Önceki hafta
          </button>
          <b>{weekLabel(days[0], days[WORKDAYS - 1])}</b>
          <button
            type="button"
            onClick={() => changeWeek(7)}
            disabled={week >= addDays(minWeek, 7 * (WEEKS_AHEAD - 1))}
          >
            Sonraki hafta ›
          </button>
        </div>
        {slots === null ? (
          <p className="muted">Yükleniyor…</p>
        ) : times.length === 0 ? (
          <p className="card muted">Bu hafta için açık saat yok.</p>
        ) : (
          <div className="wk" role="group" aria-label="Haftalık takvim">
            <div />
            {days.map((day) => {
              const parts = dayParts(day)
              return (
                <div key={day} className="h">
                  {parts.weekday}
                  <small>
                    {parts.day} {parts.month}
                  </small>
                </div>
              )
            })}
            {times.map((time) => (
              <Fragment key={time}>
                <div className="t">{time}</div>
                {days.map((day) => {
                  const slot = byCell.get(`${day}|${time}`)
                  const state = cellState(slot)
                  const isSelected = slot !== undefined && selected?.id === slot.id
                  return (
                    <button
                      key={day}
                      type="button"
                      className={`wc ${state} ${isSelected ? 'sel' : ''}`}
                      disabled={state !== 'open' || busy}
                      aria-pressed={state === 'open' ? isSelected : undefined}
                      aria-label={`${formatLongDate(day)} ${time}: ${CELL_TEXT[state]}`}
                      onClick={() => slot && choose(slot)}
                    >
                      {state === 'open' || state === 'mine' ? CELL_TEXT[state] : ''}
                    </button>
                  )
                })}
              </Fragment>
            ))}
          </div>
        )}
        <div className="legend">
          <span>
            <i style={{ background: 'var(--freebg)', border: '1px solid #a9c4ec' }} />
            Müsait
          </span>
          <span>
            <i style={{ background: 'var(--soft)' }} />
            Dolu
          </span>
          <span>
            <i style={{ background: 'var(--acc)' }} />
            Randevum
          </span>
          <span>
            <i style={{ border: '1px dashed var(--mute)' }} />
            Kapalı
          </span>
        </div>
      </main>
      <aside className="side" aria-label="Randevu özeti">
        <PatientWho />
        {booked ? (
          <section aria-live="polite">
            <h2>Randevunuz alındı ✓</h2>
            <p>
              {formatLongDate(booked.appointment_date)}
              <br />
              Saat <b>{formatTime(booked.start_at)}</b> · Randevu no{' '}
              <b>{appointmentNumber(booked.id)}</b>
            </p>
            <p className="note">
              Onay SMS&apos;i gönderilir; &quot;Randevularım&quot; sayfasındaki SMS mesajlarınızda
              görünür.
            </p>
            <p className="gate-row">
              <Link to={PATHS.appointments} className="btn">
                Randevularım
              </Link>
              <button type="button" className="btn ghost" onClick={() => setBooked(null)}>
                Yeni randevu
              </button>
            </p>
          </section>
        ) : (
          <section>
            <h2>Randevu özeti</h2>
            {selected ? (
              <>
                <p>
                  <b>{formatLongDate(dayKey(selected.start_at))}</b>
                  <br />
                  Saat <b>{formatTime(selected.start_at)}</b> · {DEPARTMENT_NAME}
                </p>
                <p className="gate-row">
                  <button type="button" className="btn" onClick={confirm} disabled={busy}>
                    {busy ? 'Kaydediliyor…' : 'Randevuyu onayla'}
                  </button>
                </p>
              </>
            ) : (
              <p className="muted">Takvimden bir saat seçin.</p>
            )}
          </section>
        )}
      </aside>
    </>
  )
}
