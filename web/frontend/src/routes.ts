import type { Role } from './types'

// Each screen has its own address so refresh, back/forward and links work
export const PATHS = {
  home: '/',
  about: '/hastanemiz',
  announcements: '/duyurular',
  guide: '/hasta-rehberi',
  contact: '/iletisim-ve-ulasim',
  patientLogin: '/giris/hasta',
  doctorLogin: '/giris/hekim',
  booking: '/randevu-al',
  appointments: '/randevularim',
  worklist: '/hasta-listesi',
  schedule: '/calisma-takvimi',
} as const

export const homeFor = (role: Role) => (role === 'patient' ? PATHS.booking : PATHS.worklist)

export const loginFor = (role: Role) =>
  role === 'patient' ? PATHS.patientLogin : PATHS.doctorLogin

export const announcementPath = (slug: string) => `${PATHS.announcements}/${slug}`
