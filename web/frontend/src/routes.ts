import type { Role } from './types'

// Each screen has its own address so refresh, back/forward and links work
export const PATHS = {
  home: '/',
  about: '/hastanemiz',
  departments: '/poliklinikler',
  doctors: '/hekimlerimiz',
  workingList: '/hekim-calisma-listesi',
  announcements: '/duyurular',
  guide: '/hasta-rehberi',
  contact: '/iletisim-ve-ulasim',
  patientLogin: '/giris/hasta',
  doctorLogin: '/giris/hekim',
  booking: '/online-randevu',
  // Earlier booking address; redirects to the booking
  oldBooking: '/randevu-al',
  appointments: '/randevularim',
  worklist: '/hasta-listesi',
  schedule: '/calisma-takvimi',
} as const

export const homeFor = (role: Role) => (role === 'patient' ? PATHS.booking : PATHS.worklist)

export const loginFor = (role: Role) =>
  role === 'patient' ? PATHS.patientLogin : PATHS.doctorLogin

export const announcementPath = (slug: string) => `${PATHS.announcements}/${slug}`

// Department addresses are built from the department name: "Göz Hastalıkları" -> "goz-hastaliklari"
const ASCII: Record<string, string> = { ç: 'c', ğ: 'g', ı: 'i', ö: 'o', ş: 's', ü: 'u' }

export const departmentSlug = (name: string) =>
  name
    .toLocaleLowerCase('tr-TR')
    .replace(/[çğıöşü]/g, (letter) => ASCII[letter])
    .normalize('NFD')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')

export const departmentPath = (name: string) => `${PATHS.departments}/${departmentSlug(name)}`

// Query parameters of the booking that preselect a department or a doctor
export const BOOKING_PARAMS = { department: 'brans', doctor: 'hekim' } as const

/** Booking address, optionally with a department or a doctor selected in advance. */
export function bookingPath(preselect: { department?: string; doctorId?: number } = {}): string {
  const query = new URLSearchParams()
  if (preselect.department) query.set(BOOKING_PARAMS.department, preselect.department)
  if (preselect.doctorId !== undefined) query.set(BOOKING_PARAMS.doctor, String(preselect.doctorId))
  const search = query.toString()
  return search ? `${PATHS.booking}?${search}` : PATHS.booking
}

// Router state the login page receives when a signed-out visitor opened a protected page
export interface LoginReturn {
  from: string
  role: Role
}
