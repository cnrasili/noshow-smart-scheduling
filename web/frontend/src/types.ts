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

// A slot as the patient sees it: free ("Müsait") or full ("Dolu"); no counts or risks
export interface Slot {
  id: number
  start_at: string
  end_at: string
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

// A demo SMS that reached the patient
export interface SmsMessage {
  kind: 'confirmation' | 'reminder'
  sent_at: string
  body: string
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
  // Part of the API contract; the department's screens do not show it
  extra: boolean
}

export interface AgendaDay {
  date: string
  // 0 when the department has no slots that day
  slot_count: number
  appointments: AgendaAppointment[]
}

// A day of the public dataset (29 April – 8 June 2016)
export interface DatasetDay {
  date: string
  appointments: number
  missed: number
}

// A real appointment of a dataset day; read-only
export interface DatasetRecord {
  patient_name: string
  patient_age: number
  attended: boolean
}
