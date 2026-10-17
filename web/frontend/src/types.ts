// The department's staff sign in with the department role; there is no doctor
export type Role = 'patient' | 'department'

export interface Me {
  role: Role
  // "Hasta <PatientId>" for patients
  name: string
}

// Patients sign in with their dataset patient number, the department with its username
export type LoginCredentials =
  | { role: 'patient'; patient_number: string; password: string }
  | { role: 'department'; username: string; password: string }

export interface LoginResponse extends Me {
  token: string
}

export interface Slot {
  id: number
  start_at: string
  end_at: string
  max_patients: number
  booked_count: number
  available: boolean
  booked_by_me: boolean
}

export interface Appointment {
  id: number
  slot_id: number
  start_at: string
  end_at: string
  appointment_date: string
  booking_date: string
  attended: boolean | null
}

export interface CalendarAppointment {
  id: number
  // "Hasta <PatientId>"
  patient_name: string
  patient_age: number
  patient_gender: string
  booking_date: string
  attended: boolean | null
}

export interface ScheduleDay {
  weekday: number
  start_time: string
  end_time: string
}

export interface CalendarSlot {
  slot_id: number
  start_at: string
  end_at: string
  max_patients: number
  appointments: CalendarAppointment[]
}

export interface AgendaAppointment {
  id: number
  slot_id: number
  start_at: string
  end_at: string
  patient_name: string
  // Booked into a slot that already had a patient (overbooking)
  extra: boolean
}

export interface AgendaDay {
  date: string
  // 0 when the department has no slots that day
  slot_count: number
  appointments: AgendaAppointment[]
}

export interface PublicWorkingHours {
  weekday: number
  start_time: string
  end_time: string
}

// The department's record as shown on the public hospital site; no account data
export interface PublicDoctor {
  id: number
  full_name: string
  specialty: string | null
  working_hours: PublicWorkingHours[]
}
