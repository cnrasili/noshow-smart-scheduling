// Dates are shown in the clinic's time zone regardless of the viewer's settings
const TIME_ZONE = 'Europe/Istanbul'
const LOCALE = 'tr-TR'

const timeFormat = new Intl.DateTimeFormat(LOCALE, {
  timeZone: TIME_ZONE,
  hour: '2-digit',
  minute: '2-digit',
})
const dayFormat = new Intl.DateTimeFormat(LOCALE, {
  timeZone: TIME_ZONE,
  weekday: 'long',
  day: 'numeric',
  month: 'long',
})
// en-CA formats dates as YYYY-MM-DD
const keyFormat = new Intl.DateTimeFormat('en-CA', { timeZone: TIME_ZONE })

export const formatTime = (iso: string) => timeFormat.format(new Date(iso))

export const formatTimeRange = (start: string, end: string) =>
  `${formatTime(start)}–${formatTime(end)}`

/** Clinic-day key (YYYY-MM-DD) of an instant. */
export const dayKey = (iso: string) => keyFormat.format(new Date(iso))

export const todayKey = () => keyFormat.format(new Date())

/** Long label for a day key, read at noon so the key's own date is shown. */
export const formatDay = (key: string) => dayFormat.format(new Date(`${key}T12:00:00+03:00`))

export function addDays(key: string, days: number): string {
  const date = new Date(`${key}T12:00:00Z`)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

export const hasStarted = (iso: string) => new Date(iso).getTime() <= Date.now()
