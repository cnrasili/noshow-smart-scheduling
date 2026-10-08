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
  booking: '/randevu-al',
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
