import { useState } from 'react'
import { DoctorCard, DoctorsPending } from '../../site/DoctorCard'
import { byDepartment, departmentOf, usePublicDoctors } from '../../site/doctors'
import { PageHeader } from '../../ui'

const ALL = ''

export function DoctorsPage() {
  const state = usePublicDoctors()
  const [department, setDepartment] = useState(ALL)
  const departments = state.status === 'ready' ? byDepartment(state.doctors) : []
  const shown =
    state.status === 'ready'
      ? state.doctors.filter((doctor) => department === ALL || departmentOf(doctor) === department)
      : []
  return (
    <>
      <PageHeader title="Hekimlerimiz">
        <label className="inline-field">
          Branş
          <select value={department} onChange={(event) => setDepartment(event.target.value)}>
            <option value={ALL}>Tüm branşlar</option>
            {departments.map(([name]) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
      </PageHeader>
      {state.status !== 'ready' ? (
        <DoctorsPending message={state.status === 'error' ? state.message : undefined} />
      ) : (
        <div className="doctor-grid">
          {shown.map((doctor) => (
            <DoctorCard key={doctor.id} doctor={doctor} />
          ))}
        </div>
      )}
    </>
  )
}
