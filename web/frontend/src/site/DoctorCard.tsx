import type { ReactNode } from 'react'
import type { PublicDoctor } from '../types'
import { departmentOf, initials, workingDays } from './doctors'

/** A doctor with initials in place of a photo, department and working days. */
export function DoctorCard({ doctor, children }: { doctor: PublicDoctor; children?: ReactNode }) {
  const days = workingDays(doctor)
  return (
    <article className="panel doctor-card" aria-labelledby={`doctor-${doctor.id}`}>
      <span className="avatar" aria-hidden="true">
        {initials(doctor.full_name)}
      </span>
      <div className="doctor-card-body">
        <h3 id={`doctor-${doctor.id}`}>{doctor.full_name}</h3>
        <p className="muted">{departmentOf(doctor)}</p>
        {days.length > 0 ? (
          <ul className="working-days">
            {days.map((day) => (
              <li key={day}>{day}</li>
            ))}
          </ul>
        ) : (
          <p className="muted">Çalışma saati tanımlı değil</p>
        )}
        {children}
      </div>
    </article>
  )
}

/** Loading and error text while the public doctor list is not ready. */
export function DoctorsPending({ message }: { message?: string }) {
  return (
    <p
      className={`panel panel-body ${message ? 'form-error' : 'muted'}`}
      role={message ? 'alert' : undefined}
    >
      {message ? `Hekim bilgileri alınamadı: ${message}` : 'Hekim bilgileri yükleniyor…'}
    </p>
  )
}
