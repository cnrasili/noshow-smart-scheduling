import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { api, errorText } from '../../api'
import { DEPARTMENT_NAME } from '../../config'
import { WEEKDAY_NAMES, formatClock } from '../../format'
import { PATHS } from '../../routes'
import type { PublicWorkingHours } from '../../types'
import { PageHeader } from '../../ui'

type HoursState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; hours: PublicWorkingHours[] }

const WORKDAYS = [0, 1, 2, 3, 4]

/** The weekly working hours of the department, the only record of the public list. */
function useWorkingHours(): HoursState {
  const [state, setState] = useState<HoursState>({ status: 'loading' })
  useEffect(() => {
    let current = true
    api
      .publicDoctors()
      .then((records) => {
        if (current) setState({ status: 'ready', hours: records[0]?.working_hours ?? [] })
      })
      .catch((error) => {
        if (current) setState({ status: 'error', message: errorText(error) })
      })
    return () => {
      current = false
    }
  }, [])
  return state
}

export function DepartmentPage() {
  const state = useWorkingHours()
  // Weekend rows appear only if the department works then
  const weekdays =
    state.status === 'ready' && state.hours.some((hours) => hours.weekday > 4)
      ? [...WORKDAYS, 5, 6]
      : WORKDAYS
  return (
    <>
      <PageHeader
        title={DEPARTMENT_NAME}
        description="Her yaştan hastanın muayenesi, kronik hastalıkların takibi ve koruyucu sağlık hizmetleri."
      >
        <Link to={PATHS.booking} className="button primary">
          Online Randevu
        </Link>
      </PageHeader>
      <section className="panel" aria-labelledby="working-hours">
        <div className="panel-head">
          <h2 id="working-hours">Çalışma saatleri</h2>
        </div>
        {state.status !== 'ready' ? (
          <p
            className={`panel-body ${state.status === 'error' ? 'form-error' : 'muted'}`}
            role={state.status === 'error' ? 'alert' : undefined}
          >
            {state.status === 'error'
              ? `Çalışma saatleri alınamadı: ${state.message}`
              : 'Çalışma saatleri yükleniyor…'}
          </p>
        ) : (
          <table className="table compact">
            <tbody>
              {weekdays.map((weekday) => {
                const hours = state.hours.find((h) => h.weekday === weekday)
                return (
                  <tr key={weekday} className={hours ? '' : 'row-empty'}>
                    <td className="strong">{WEEKDAY_NAMES[weekday]}</td>
                    <td className="mono">
                      {hours ? (
                        `${formatClock(hours.start_time)}–${formatClock(hours.end_time)}`
                      ) : (
                        <span className="muted">Kapalı</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </section>
    </>
  )
}
