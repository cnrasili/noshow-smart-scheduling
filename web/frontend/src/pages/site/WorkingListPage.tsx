import { Link } from 'react-router'
import { WEEKDAY_NAMES } from '../../format'
import { departmentPath, departmentSlug } from '../../routes'
import { DoctorsPending } from '../../site/DoctorCard'
import { byDepartment, formatHours, usePublicDoctors } from '../../site/doctors'
import { PageHeader } from '../../ui'

const WORKDAYS = [0, 1, 2, 3, 4]

export function WorkingListPage() {
  const state = usePublicDoctors()
  // Weekend columns appear only if a doctor works then
  const weekdays =
    state.status === 'ready' &&
    state.doctors.some((doctor) => doctor.working_hours.some((hours) => hours.weekday > 4))
      ? [...WORKDAYS, 5, 6]
      : WORKDAYS
  return (
    <>
      <PageHeader
        title="Hekim Çalışma Listesi"
        description="Hekimlerimizin haftalık poliklinik çalışma saatleri"
      />
      {state.status !== 'ready' ? (
        <DoctorsPending message={state.status === 'error' ? state.message : undefined} />
      ) : (
        byDepartment(state.doctors).map(([name, doctors]) => (
          <section key={name} className="panel" aria-labelledby={`list-${departmentSlug(name)}`}>
            <div className="panel-head">
              <h2 id={`list-${departmentSlug(name)}`}>
                <Link to={departmentPath(name)}>{name}</Link>
              </h2>
            </div>
            <table className="table working-list">
              <thead>
                <tr>
                  <th>Hekim</th>
                  {weekdays.map((weekday) => (
                    <th key={weekday}>{WEEKDAY_NAMES[weekday]}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {doctors.map((doctor) => (
                  <tr key={doctor.id}>
                    <td data-label="Hekim" className="strong">
                      {doctor.full_name}
                    </td>
                    {weekdays.map((weekday) => {
                      const hours = doctor.working_hours.find((h) => h.weekday === weekday)
                      return (
                        <td key={weekday} data-label={WEEKDAY_NAMES[weekday]} className="mono">
                          {hours ? formatHours(hours) : '—'}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        ))
      )}
    </>
  )
}
