import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { DEPARTMENT_INFO } from '../content/departments'
import { PATHS, departmentPath, departmentSlug } from '../routes'
import type { PublicDoctor } from '../types'
import { fakeBackend, renderApp } from './backend'

const hours = (weekday: number, start: string, end: string) => ({
  weekday,
  start_time: `${start}:00`,
  end_time: `${end}:00`,
})

const DOCTORS: PublicDoctor[] = [
  {
    id: 1,
    full_name: 'Dr. Deniz Yıldız',
    specialty: 'Dahiliye',
    working_hours: [hours(0, '09:00', '12:00'), hours(2, '09:00', '12:00')],
  },
  {
    id: 2,
    full_name: 'Dr. Can Özkan',
    specialty: 'Dahiliye',
    working_hours: [hours(1, '13:00', '16:00')],
  },
  {
    id: 3,
    full_name: 'Dr. Leyla Aksoy',
    specialty: 'Kardiyoloji',
    working_hours: [hours(3, '09:00', '12:00')],
  },
  // A department added later, without a description in the frontend
  { id: 4, full_name: 'Dr. Yeni Hekim', specialty: 'Fizik Tedavi', working_hours: [] },
]

const publicBackend = () => fakeBackend({ 'GET /public/doctors': () => DOCTORS })

describe('department and doctor pages', () => {
  it('builds Turkish-free department addresses', () => {
    expect(departmentSlug('Göz Hastalıkları')).toBe('goz-hastaliklari')
    expect(departmentSlug('Çocuk Sağlığı ve Hastalıkları')).toBe('cocuk-sagligi-ve-hastaliklari')
  })

  it('lists the departments from the database without signing in', async () => {
    const calls = publicBackend()
    renderApp(PATHS.departments)

    for (const [name, count] of [
      ['Dahiliye', '2 hekim'],
      ['Kardiyoloji', '1 hekim'],
      ['Fizik Tedavi', '1 hekim'],
    ]) {
      const link = await screen.findByRole('link', { name: new RegExp(name) })
      expect(link).toHaveAttribute('href', departmentPath(name))
      expect(link).toHaveTextContent(count)
    }
    expect(calls.map((c) => c.path)).toEqual(['/public/doctors'])
  })

  it('shows a department with its description, doctors and Online Randevu', async () => {
    publicBackend()
    renderApp(departmentPath('Dahiliye'))

    expect(await screen.findByRole('heading', { level: 1, name: 'Dahiliye' })).toBeVisible()
    expect(screen.getByText(DEPARTMENT_INFO.Dahiliye)).toBeInTheDocument()
    const deniz = screen.getByRole('article', { name: 'Dr. Deniz Yıldız' })
    expect(within(deniz).getByText('DY')).toBeInTheDocument()
    expect(within(deniz).getByText('Pazartesi 09:00–12:00')).toBeInTheDocument()
    expect(screen.getByRole('article', { name: 'Dr. Can Özkan' })).toBeInTheDocument()
    expect(screen.queryByRole('article', { name: 'Dr. Leyla Aksoy' })).not.toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Online Randevu' }).length).toBeGreaterThan(1)
  })

  it('shows the doctors of a department without a description', async () => {
    publicBackend()
    renderApp(departmentPath('Fizik Tedavi'))

    expect(await screen.findByRole('heading', { level: 1, name: 'Fizik Tedavi' })).toBeVisible()
    expect(screen.getByRole('article', { name: 'Dr. Yeni Hekim' })).toBeInTheDocument()
    expect(screen.getByText('Çalışma saati tanımlı değil')).toBeInTheDocument()
  })

  it('tells about an unknown department', async () => {
    publicBackend()
    renderApp(`${PATHS.departments}/yok`)

    expect(await screen.findByRole('heading', { name: 'Poliklinik bulunamadı' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Tüm poliklinikler' })).toBeInTheDocument()
  })

  it('filters the doctors by department', async () => {
    publicBackend()
    renderApp(PATHS.doctors)
    const user = userEvent.setup()

    expect(await screen.findAllByRole('article')).toHaveLength(DOCTORS.length)
    await user.selectOptions(screen.getByLabelText('Branş'), 'Kardiyoloji')

    expect(screen.getAllByRole('article').map((a) => a.getAttribute('aria-labelledby'))).toEqual([
      'doctor-3',
    ])
  })

  it('shows the weekly working list grouped by department', async () => {
    publicBackend()
    renderApp(PATHS.workingList)

    const dahiliye = await screen.findByRole('region', { name: 'Dahiliye' })
    const deniz = within(dahiliye).getByRole('row', { name: /Dr. Deniz Yıldız/ })
    const cells = within(deniz).getAllByRole('cell')
    expect(cells.map((cell) => cell.textContent)).toEqual([
      'Dr. Deniz Yıldız',
      '09:00–12:00',
      '—',
      '09:00–12:00',
      '—',
      '—',
    ])
    expect(screen.getByRole('region', { name: 'Kardiyoloji' })).toBeInTheDocument()
    expect(screen.queryAllByRole('columnheader', { name: 'Cumartesi' })).toHaveLength(0)
  })

  it('reaches the new pages from the main menu and the home page', async () => {
    publicBackend()
    renderApp(PATHS.home)
    const user = userEvent.setup()
    const menu = screen.getByRole('navigation', { name: 'Ana menü' })

    expect(within(menu).getByRole('link', { name: 'Poliklinikler' })).toBeInTheDocument()
    expect(within(menu).getByRole('link', { name: 'Hekimlerimiz' })).toBeInTheDocument()
    await user.click(
      within(screen.getByRole('main')).getByRole('link', { name: /^Hekim Çalışma Listesi/ }),
    )

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Hekim Çalışma Listesi' }),
    ).toBeVisible()
  })

  it('shows a message when the doctor list cannot be loaded', async () => {
    fakeBackend({ 'GET /public/doctors': () => ({ status: 503, body: { detail: 'Down' } }) })
    renderApp(PATHS.doctors)

    expect(await screen.findByRole('alert')).toHaveTextContent('Hekim bilgileri alınamadı')
  })
})
