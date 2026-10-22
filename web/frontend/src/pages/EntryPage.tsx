import { Link } from 'react-router'
import { DEPARTMENT_NAME, INSTITUTION_NAME } from '../config'
import { PATHS } from '../routes'
import { usePageTitle } from '../title'

export const DISCLAIMER =
  'Bu site bir ders projesidir; gerçek bir hastaneye ait değildir. Hastalar herkese açık bir veri setinden alınmıştır ve yalnızca numarayla gösterilir.'

/** Entry page: the patient and the department choose their login. */
export function EntryPage() {
  usePageTitle()
  return (
    <main className="gate">
      <div className="gate-card">
        <h1>{INSTITUTION_NAME}</h1>
        <p className="sub">{DEPARTMENT_NAME} · online randevu</p>
        <Link to={PATHS.patientLogin} className="gate-choice">
          Hasta Girişi
        </Link>
        <Link to={PATHS.departmentLogin} className="gate-choice">
          Departman Girişi
        </Link>
        <p className="gate-note">
          Yönetim paneli ayrı bir serviste çalışır ve yalnızca hastane iç ağından açılır.
        </p>
      </div>
      <p className="disclaimer">{DISCLAIMER}</p>
    </main>
  )
}
