import type { Role } from './types'

// Each screen has its own address so refresh, back/forward and links work
export const PATHS = {
  home: '/',
  about: '/hastanemiz',
  department: '/aile-hekimligi',
  announcements: '/duyurular',
  guide: '/hasta-rehberi',
  contact: '/iletisim-ve-ulasim',
  patientLogin: '/giris/hasta',
  departmentLogin: '/giris/departman',
  booking: '/online-randevu',
  // Earlier booking address; redirects to the booking
  oldBooking: '/randevu-al',
  appointments: '/randevularim',
  worklist: '/hasta-listesi',
  schedule: '/calisma-takvimi',
} as const

export const homeFor = (role: Role) => (role === 'patient' ? PATHS.booking : PATHS.worklist)

export const loginFor = (role: Role) =>
  role === 'patient' ? PATHS.patientLogin : PATHS.departmentLogin

export const announcementPath = (slug: string) => `${PATHS.announcements}/${slug}`

// Router state the login page receives when a signed-out visitor opened a protected page
export interface LoginReturn {
  from: string
  role: Role
}
