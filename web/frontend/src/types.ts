export type Role = 'patient' | 'doctor'

export interface Me {
  role: Role
  name: string
  email: string
}

export interface LoginResponse extends Me {
  token: string
}

export interface Doctor {
  id: number
  full_name: string
  specialty: string | null
}

export interface Slot {
  id: number
  doctor_id: number
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
  doctor_name: string
  start_at: string
  end_at: string
  appointment_date: string
  booking_date: string
  attended: boolean | null
}

export interface CalendarAppointment {
  id: number
  patient_name: string
  attended: boolean | null
}

export interface CalendarSlot {
  slot_id: number
  start_at: string
  end_at: string
  max_patients: number
  appointments: CalendarAppointment[]
}
