import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { api, errorText } from '../../api'
import { WEEKDAY_NAMES, addDays, formatClock, formatShortDate, todayKey } from '../../format'
import type { ScheduleDay } from '../../types'
import { Notice, PageHeader, type NoticeState } from '../../ui'

const GENERATION_DAYS = 14

export function SchedulePage() {
  const [schedule, setSchedule] = useState<ScheduleDay[] | null>(null)
  const [dateFrom, setDateFrom] = useState(todayKey)
  const [dateTo, setDateTo] = useState(() => addDays(todayKey(), GENERATION_DAYS - 1))
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState<NoticeState | null>(null)

  const closeNotice = useCallback(() => setNotice(null), [])

  useEffect(() => {
    api
      .schedule()
      .then(setSchedule)
      .catch((error) => setNotice({ kind: 'error', text: errorText(error) }))
  }, [])

  async function generate(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    try {
      const { created } = await api.generateSlots(dateFrom, dateTo)
      const range = `${formatShortDate(dateFrom)} – ${formatShortDate(dateTo)}`
      setNotice({
        kind: 'success',
        text:
          created > 0
            ? `${range} arasında ${created} yeni slot oluşturuldu.`
            : `${range} arasındaki tüm slotlar zaten tanımlı.`,
      })
    } catch (error) {
      setNotice({ kind: 'error', text: errorText(error) })
    } finally {
      setBusy(false)
    }
  }

  const byWeekday = new Map(schedule?.map((day) => [day.weekday, day]))

  return (
    <>
      <Notice notice={notice} onClose={closeNotice} />
      <PageHeader
        title="Çalışma Takvimi"
        description="Haftalık çalışma saatleri ve randevu slotlarının açılması."
      />

      <div className="columns">
        <section className="panel">
          <div className="panel-head">
            <h2>Haftalık çalışma saatleri</h2>
          </div>
          {schedule === null ? (
            <p className="muted panel-body">Yükleniyor…</p>
          ) : (
            <table className="table compact">
              <tbody>
                {WEEKDAY_NAMES.map((name, weekday) => {
                  const hours = byWeekday.get(weekday)
                  return (
                    <tr key={name} className={hours ? '' : 'row-empty'}>
                      <td className="strong">{name}</td>
                      <td className="mono">
                        {hours ? (
                          `${formatClock(hours.start_time)}–${formatClock(hours.end_time)}`
                        ) : (
                          <span className="muted">Çalışma yok</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </section>

        <section className="panel">
          <div className="panel-head">
            <h2>Slot aç</h2>
          </div>
          <form className="panel-body stack" onSubmit={generate}>
            <p className="muted">
              Seçilen tarih aralığında çalışma saatlerine göre slotlar açılır. Daha önce açılmış
              slotlar ve alınmış randevular değişmez.
            </p>
            <div className="filters">
              <label>
                Başlangıç
                <input
                  type="date"
                  value={dateFrom}
                  min={todayKey()}
                  onChange={(event) => setDateFrom(event.target.value)}
                  required
                />
              </label>
              <label>
                Bitiş
                <input
                  type="date"
                  value={dateTo}
                  min={dateFrom}
                  onChange={(event) => setDateTo(event.target.value)}
                  required
                />
              </label>
            </div>
            <div>
              <button type="submit" className="primary" disabled={busy}>
                {busy ? 'Açılıyor…' : 'Slotları aç'}
              </button>
            </div>
          </form>
        </section>
      </div>
    </>
  )
}
