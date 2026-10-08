import { useEffect, useState } from 'react'
import { api, errorText } from '../api'
import { NO_DEPARTMENT } from '../content/departments'
import { WEEKDAY_NAMES, formatClock } from '../format'
import type { PublicDoctor, PublicWorkingHours } from '../types'

export type DoctorsState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; doctors: PublicDoctor[] }

/** The public doctor list of the hospital site. */
export function usePublicDoctors(): DoctorsState {
  const [state, setState] = useState<DoctorsState>({ status: 'loading' })
  useEffect(() => {
    let current = true
    api
      .publicDoctors()
      .then((doctors) => {
        if (current) setState({ status: 'ready', doctors })
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

export const departmentOf = (doctor: PublicDoctor) => doctor.specialty ?? NO_DEPARTMENT

/** Departments in alphabetical order with their doctors. */
export function byDepartment(doctors: PublicDoctor[]): [string, PublicDoctor[]][] {
  const groups = new Map<string, PublicDoctor[]>()
  for (const doctor of doctors) {
    const name = departmentOf(doctor)
    groups.set(name, [...(groups.get(name) ?? []), doctor])
  }
  return [...groups].sort(([a], [b]) => a.localeCompare(b, 'tr-TR'))
}

/** "Dr. Leyla Aksoy" -> "LA" */
export function initials(fullName: string): string {
  const words = fullName
    .replace(/^Dr\.?\s+/i, '')
    .split(/\s+/)
    .filter(Boolean)
  const letters = words.length > 1 ? [words[0], words[words.length - 1]] : words
  return letters.map((word) => word[0].toLocaleUpperCase('tr-TR')).join('')
}

export const formatHours = (hours: PublicWorkingHours) =>
  `${formatClock(hours.start_time)}–${formatClock(hours.end_time)}`

/** "Salı 09:00–12:00" for each working day */
export const workingDays = (doctor: PublicDoctor) =>
  doctor.working_hours.map((hours) => `${WEEKDAY_NAMES[hours.weekday]} ${formatHours(hours)}`)
