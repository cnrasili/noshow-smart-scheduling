// Dates are shown in the clinic's time zone regardless of the viewer's settings
const TIME_ZONE = 'Europe/Istanbul'
const LOCALE = 'tr-TR'

const format = (options: Intl.DateTimeFormatOptions) =>
  new Intl.DateTimeFormat(LOCALE, { timeZone: TIME_ZONE, ...options })

const timeFormat = format({ hour: '2-digit', minute: '2-digit' })
const longDateFormat = format({ day: 'numeric', month: 'long', year: 'numeric', weekday: 'long' })
const shortDateFormat = format({ day: '2-digit', month: '2-digit', year: 'numeric' })
const weekdayFormat = format({ weekday: 'short' })
const monthFormat = format({ month: 'short' })
const dayNumberFormat = format({ day: 'numeric' })
// en-CA formats dates as YYYY-MM-DD
const keyFormat = new Intl.DateTimeFormat('en-CA', { timeZone: TIME_ZONE })

export const WEEKDAY_NAMES = [
  'Pazartesi',
  'Salı',
  'Çarşamba',
  'Perşembe',
  'Cuma',
  'Cumartesi',
  'Pazar',
]

// A day key read at noon in the clinic so the key's own date is shown
const keyDate = (key: string) => new Date(`${key}T12:00:00+03:00`)

export const formatTime = (iso: string) => timeFormat.format(new Date(iso))

export const formatTimeRange = (start: string, end: string) =>
  `${formatTime(start)}–${formatTime(end)}`

/** Clinic-day key (YYYY-MM-DD) of an instant. */
export const dayKey = (iso: string) => keyFormat.format(new Date(iso))

export const todayKey = () => keyFormat.format(new Date())

/** "2 Ekim 2026 Cuma" */
export const formatLongDate = (key: string) => longDateFormat.format(keyDate(key))

/** "02.10.2026" */
export const formatShortDate = (key: string) => shortDateFormat.format(keyDate(key))

export const dayParts = (key: string) => ({
  weekday: weekdayFormat.format(keyDate(key)),
  day: dayNumberFormat.format(keyDate(key)),
  month: monthFormat.format(keyDate(key)),
})

/** "09:00:00" -> "09:00" */
export const formatClock = (value: string) => value.slice(0, 5)

export function addDays(key: string, days: number): string {
  const date = new Date(`${key}T12:00:00Z`)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

/** Monday of the week that contains a day key. */
export function weekStart(key: string): string {
  const weekday = (new Date(`${key}T12:00:00Z`).getUTCDay() + 6) % 7
  return addDays(key, -weekday)
}

/** "Bugün" or "Yarın" for today and tomorrow, otherwise null. */
export function relativeDayLabel(key: string): string | null {
  const today = todayKey()
  if (key === today) return 'Bugün'
  if (key === addDays(today, 1)) return 'Yarın'
  return null
}

export const hasStarted = (iso: string) => new Date(iso).getTime() <= Date.now()

export const appointmentNumber = (id: number) => `R-${String(id).padStart(6, '0')}`

export const genderLabel = (gender: string) =>
  gender === 'F' ? 'Kadın' : gender === 'M' ? 'Erkek' : '—'

export const branchLabel = (specialty: string | null) => specialty ?? 'Genel'
