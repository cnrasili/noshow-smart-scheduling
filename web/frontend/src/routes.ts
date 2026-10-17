import type { Role } from './types'

// Each screen has its own address so refresh, back/forward and links work
export const PATHS = {
  // Entry page: "Hasta Girişi" and "Departman Girişi"
  home: '/',
  patientLogin: '/giris/hasta',
  departmentLogin: '/giris/departman',
  booking: '/randevu-al',
  appointments: '/randevularim',
  panel: '/departman',
  schedule: '/calisma-takvimi',
} as const

// Addresses of the earlier site that lead to their new screen
export const OLD_PATHS: Record<string, string> = {
  '/online-randevu': PATHS.booking,
  '/hasta-listesi': PATHS.panel,
  '/giris/hekim': PATHS.departmentLogin,
}

export const homeFor = (role: Role) => (role === 'patient' ? PATHS.booking : PATHS.panel)

export const loginFor = (role: Role) =>
  role === 'patient' ? PATHS.patientLogin : PATHS.departmentLogin

// Router state the login page receives when a signed-out visitor opened a protected page
export interface LoginReturn {
  from: string
  role: Role
}
