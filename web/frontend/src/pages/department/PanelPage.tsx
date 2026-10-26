import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, errorText } from '../../api'
import { DEPARTMENT_NAME } from '../../config'
import { addDays, dayParts, formatLongDate, formatTime, todayKey, weekStart } from '../../format'
import type { AgendaDay, CalendarSlot, DatasetDay, DatasetRecord } from '../../types'
import { Notice, PageTop, type NoticeState } from '../../ui'

// Dataset days have thousands of records; the columns grow on request
const FIRST_SHOWN = 150
const MORE_SHOWN = 300
// How often today's board checks which appointments have started
const CLOCK_TICK_MS = 30_000

interface Entry {
  key: string
  // Clinic time; dataset records have none
  time: string | null
  // Slot start (UTC); a no-show can be marked only after it
  startAt: string | null
  name: string
  age: number
  attended: boolean | null
  // Booked in the application; dataset records cannot be marked
  appointmentId: number | null
}

type Mode = 'data' | 'today' | 'future' | 'past'

const fromCalendar = (slots: CalendarSlot[]): Entry[] =>
  slots.flatMap((slot) =>
    slot.appointments.map((a) => ({
      key: `a${a.id}`,
      time: formatTime(slot.start_at),
      startAt: slot.start_at,
      name: a.patient_name,
      age: a.patient_age,
      attended: a.attended,
      appointmentId: a.id,
    })),
  )

const fromDataset = (records: DatasetRecord[]): Entry[] =>
  records.map((r, index) => ({
    key: `r${index}`,
    time: null,
    startAt: null,
    name: r.patient_name,
    age: r.patient_age,
    attended: r.attended,
    appointmentId: null,
  }))

const percent = (part: number, whole: number) =>
  `%${((100 * part) / Math.max(whole, 1)).toLocaleString('tr-TR', { maximumFractionDigits: 1 })}`

type Column = { title: string; filter: (entry: Entry) => boolean }

const COLUMNS: Record<Mode, Column[]> = {
  today: [
    { title: 'Bekleyen', filter: (e) => e.attended === null },
    { title: 'Geldi', filter: (e) => e.attended === true },
    { title: 'Gelmedi', filter: (e) => e.attended === false },
  ],
  data: [
    { title: 'Geldi (kayıt)', filter: (e) => e.attended === true },
    { title: 'Gelmedi (kayıt)', filter: (e) => e.attended === false },
  ],
  past: [
    { title: 'Geldi', filter: (e) => e.attended === true },
    { title: 'Gelmedi', filter: (e) => e.attended === false },
    { title: 'İşaretlenmedi', filter: (e) => e.attended === null },
  ],
  future: [{ title: 'Randevular', filter: () => true }],
}

function Ticket({
  entry,
  live,
  now,
  busy,
  onMark,
}: {
  entry: Entry
  live: boolean
  // Current time in milliseconds
  now: number
  busy: boolean
  onMark: (entry: Entry, attended: boolean | null) => void
}) {
  const started = entry.startAt !== null && Date.parse(entry.startAt) <= now
  return (
    <li className="tk">
      <b>{entry.time ?? 'Randevu'}</b> · {entry.name}
      <small>{entry.age} yaşında</small>
      {live && (
        <div className="a">
          {entry.attended !== true && (
            <button
              type="button"
              onClick={() => onMark(entry, true)}
              disabled={busy}
              aria-label={`${entry.name}: geldi`}
            >
              Geldi
            </button>
          )}
          {entry.attended !== false && started && (
            <button
              type="button"
              onClick={() => onMark(entry, false)}
              disabled={busy}
              aria-label={`${entry.name}: gelmedi`}
            >
              Gelmedi
            </button>
          )}
          {entry.attended !== null && (
            <button
              type="button"
              onClick={() => onMark(entry, null)}
              disabled={busy}
              aria-label={`${entry.name}: geri al`}
            >
              Geri al
            </button>
          )}
        </div>
      )}
    </li>
  )
}

export function PanelPage() {
  const today = todayKey()
  const [day, setDay] = useState(today)
  const [datasetDays, setDatasetDays] = useState<DatasetDay[] | null>(null)
  const [week, setWeek] = useState<AgendaDay[] | null>(null)
  const [entries, setEntries] = useState<Entry[] | null>(null)
  const [todayEntries, setTodayEntries] = useState<Entry[] | null>(null)
  const [shown, setShown] = useState(FIRST_SHOWN)
  const [busyKey, setBusyKey] = useState<string | null>(null)
  const [now, setNow] = useState(() => Date.now())
  const [notice, setNotice] = useState<NoticeState | null>(null)
  const closeNotice = useCallback(() => setNotice(null), [])
  const showError = useCallback(
    (error: unknown) => setNotice({ kind: 'error', text: errorText(error) }),
    [],
  )

  const recordDays = useMemo(() => new Set(datasetDays?.map((d) => d.date)), [datasetDays])
  const mode: Mode = recordDays.has(day)
    ? 'data'
    : day === today
      ? 'today'
      : day > today
        ? 'future'
        : 'past'
  const monday = weekStart(day)

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), CLOCK_TICK_MS)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    api.datasetDays().then(setDatasetDays).catch(showError)
  }, [showError])

  const loadToday = useCallback(
    () =>
      api
        .calendar(today)
        .then((slots) => setTodayEntries(fromCalendar(slots)))
        .catch(showError),
    [today, showError],
  )
  useEffect(() => {
    loadToday()
  }, [loadToday])

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
  }, [monday, showError])

  useEffect(() => {
    // Today's board uses the same data as the side panel
    if (datasetDays === null || mode === 'today') return
    let current = true
    const load =
      mode === 'data' ? api.datasetDay(day).then(fromDataset) : api.calendar(day).then(fromCalendar)
    load
      .then((next) => {
        if (current) setEntries(next)
      })
      .catch(showError)
    return () => {
      current = false
    }
  }, [day, mode, datasetDays, showError])

  function changeDay(next: string) {
    // The selected day is already loaded; clearing it would leave the list empty
    if (!next || next === day) return
    if (weekStart(next) !== monday) setWeek(null)
    setEntries(null)
    setShown(FIRST_SHOWN)
    setDay(next)
  }

  async function mark(entry: Entry, attended: boolean | null) {
    if (entry.appointmentId === null) return
    setBusyKey(entry.key)
    try {
      await api.markAttendance(entry.appointmentId, attended)
      await loadToday()
    } catch (error) {
      showError(error)
    } finally {
      setBusyKey(null)
    }
  }

  const list = mode === 'today' ? todayEntries : entries
  const missed = (list ?? []).filter((e) => e.attended === false).length
  const next = todayEntries?.find((e) => e.attended === null)
  const columns = COLUMNS[mode]
  const empty =
    list !== null && list.length === 0 && mode !== 'today'
      ? mode === 'future'
        ? 'Bu gün için henüz randevu alınmadı.'
        : 'Bu gün için kayıt yok.'
      : null

  return (
    <>
      <main className="main">
        <Notice notice={notice} onClose={closeNotice} />
        <PageTop
          title={formatLongDate(day)}
          description={
            DEPARTMENT_NAME +
            (mode === 'data'
              ? ' · veri seti günü: günün tüm gerçek randevuları, sonuçlar kayıttır ve değiştirilemez'
              : mode === 'today'
                ? ' · bugün'
                : '')
          }
        >
          <div className="stats">
            <div className="stat">
              <small>Randevu</small>
              <b>{list === null ? '…' : list.length.toLocaleString('tr-TR')}</b>
            </div>
            {mode === 'data' && list !== null && (
              <div className="stat">
                <small>Gelmeme oranı</small>
                <b>{percent(missed, list.length)}</b>
              </div>
            )}
          </div>
        </PageTop>

        <div className="wnav">
          <button type="button" onClick={() => changeDay(addDays(day, -7))}>
            ‹ Önceki hafta
          </button>
          <div className="strip" role="group" aria-label="Haftanın günleri">
            {[...Array(7).keys()].map((n) => {
              const date = addDays(monday, n)
              const parts = dayParts(date)
              const count = week?.find((d) => d.date === date)?.appointments.length ?? 0
              const tag = recordDays.has(date)
                ? 'kayıt'
                : date === today
                  ? 'bugün'
                  : count > 0
                    ? `${count} randevu`
                    : ''
              return (
                <button
                  key={date}
                  type="button"
                  className={`dy ${date === day ? 'on' : ''} ${recordDays.has(date) ? 'rec' : ''}`}
                  aria-pressed={date === day}
                  aria-label={`${formatLongDate(date)}${tag ? `: ${tag}` : ''}`}
                  onClick={() => changeDay(date)}
                >
                  <small>{parts.weekday}</small>
                  <b>{parts.day}</b>
                  <small>{tag || ' '}</small>
                </button>
              )
            })}
          </div>
          <button type="button" onClick={() => changeDay(addDays(day, 7))}>
            Sonraki hafta ›
          </button>
          <button type="button" onClick={() => changeDay(today)} disabled={day === today}>
            Bugün
          </button>
          <select
            aria-label="Veri seti günü"
            value={recordDays.has(day) ? day : ''}
            onChange={(event) => changeDay(event.target.value)}
            disabled={!datasetDays?.length}
          >
            <option value="">Veri seti günleri</option>
            {datasetDays?.map((d) => (
              <option key={d.date} value={d.date}>
                {formatLongDate(d.date)}
              </option>
            ))}
          </select>
        </div>

        {list === null ? (
          <p className="muted">Yükleniyor…</p>
        ) : empty ? (
          <p className="card muted">{empty}</p>
        ) : (
          <div className={`board c${columns.length}`}>
            {columns.map((column) => {
              const items = list.filter(column.filter)
              return (
                <section key={column.title} className="col" aria-label={column.title}>
                  <h3>
                    {column.title}
                    <span>{items.length.toLocaleString('tr-TR')}</span>
                  </h3>
                  <ul>
                    {items.slice(0, shown).map((entry) => (
                      <Ticket
                        key={entry.key}
                        entry={entry}
                        live={mode === 'today'}
                        now={now}
                        busy={busyKey === entry.key}
                        onMark={mark}
                      />
                    ))}
                  </ul>
                  {mode === 'today' && column.title === 'Bekleyen' && list.length === 0 && (
                    <p className="note">
                      Bugün için randevu yok. Hasta portalından randevu alındığında burada görünür.
                    </p>
                  )}
                  {items.length > shown && (
                    <button
                      type="button"
                      className="btn ghost"
                      style={{ width: '100%' }}
                      onClick={() => setShown((n) => n + MORE_SHOWN)}
                    >
                      Daha fazla göster ({(items.length - shown).toLocaleString('tr-TR')})
                    </button>
                  )}
                </section>
              )
            })}
          </div>
        )}
      </main>
      <aside className="side" aria-label="Sıradaki hasta">
        <h2>Sıradaki hasta</h2>
        {todayEntries === null ? (
          <p className="muted">Yükleniyor…</p>
        ) : next ? (
          <>
            <p style={{ fontSize: 20 }}>
              <b>{next.time}</b> · {next.name}
            </p>
            <p className="muted">{next.age} yaşında</p>
          </>
        ) : (
          <p className="muted">Bekleyen hasta yok.</p>
        )}
        <p className="note">
          Hastalar yalnızca numarayla gösterilir. “Geldi / Gelmedi” yalnızca bugün işaretlenir;
          “Gelmedi” randevu saati gelince seçilebilir. Veri setindeki günlerin sonuçları kayıttan
          gelir ve değiştirilemez.
        </p>
      </aside>
    </>
  )
}
