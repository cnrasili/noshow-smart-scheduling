import { Link, useParams } from 'react-router'
import { DEPARTMENT_INFO } from '../../content/departments'
import { PATHS, departmentPath, departmentSlug } from '../../routes'
import { DoctorCard, DoctorsPending } from '../../site/DoctorCard'
import { byDepartment, usePublicDoctors } from '../../site/doctors'
import { PageHeader } from '../../ui'

export function DepartmentsPage() {
  const state = usePublicDoctors()
  return (
    <>
      <PageHeader title="Poliklinikler" description="Hastanemizde hizmet veren branşlar" />
      {state.status !== 'ready' ? (
        <DoctorsPending message={state.status === 'error' ? state.message : undefined} />
      ) : (
        <ul className="department-grid">
          {byDepartment(state.doctors).map(([name, doctors]) => (
            <li key={name}>
              <Link to={departmentPath(name)} className="panel department-link">
                <span className="department-name">{name}</span>
                <span className="muted">{doctors.length} hekim</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}

export function DepartmentPage() {
  const { slug } = useParams()
  const state = usePublicDoctors()
  if (state.status !== 'ready') {
    return <DoctorsPending message={state.status === 'error' ? state.message : undefined} />
  }
  const department = byDepartment(state.doctors).find(([name]) => departmentSlug(name) === slug)
  if (!department) {
    return (
      <>
        <PageHeader title="Poliklinik bulunamadı" />
        <p className="panel panel-body">
          Bu adreste bir poliklinik yok. <Link to={PATHS.departments}>Tüm poliklinikler</Link>
        </p>
      </>
    )
  }
  const [name, doctors] = department
  return (
    <>
      <PageHeader title={name} description={DEPARTMENT_INFO[name]}>
        <Link to={PATHS.booking} className="button primary">
          Online Randevu
        </Link>
      </PageHeader>
      <section aria-labelledby="department-doctors" className="stack-tight">
        <h2 id="department-doctors">Hekimlerimiz</h2>
        <div className="doctor-grid">
          {doctors.map((doctor) => (
            <DoctorCard key={doctor.id} doctor={doctor} />
          ))}
        </div>
      </section>
      <Link to={PATHS.departments}>‹ Tüm poliklinikler</Link>
    </>
  )
}
