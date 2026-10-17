import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { PATHS } from '../routes'
import type { PublicDoctor } from '../types'
import { fakeBackend, renderApp } from './backend'

const hours = (weekday: number) => ({ weekday, start_time: '08:00:00', end_time: '12:00:00' })

// The department's record as the backend stores it
const DEPARTMENT_RECORD: PublicDoctor[] = [
  {
    id: 1,
    full_name: 'General Practice',
    specialty: 'General Practice',
    working_hours: [0, 1, 2, 3, 4].map(hours),
  },
]

describe('department page', () => {
  it('shows the working hours of the one department', async () => {
    const calls = fakeBackend({ 'GET /public/doctors': () => DEPARTMENT_RECORD })
    renderApp(PATHS.department)

    expect(await screen.findByRole('heading', { level: 1, name: 'Aile Hekimliği' })).toBeVisible()
    const rows = await screen.findAllByRole('row')
    expect(rows.map((row) => row.textContent)).toEqual([
      'Pazartesi08:00–12:00',
      'Salı08:00–12:00',
      'Çarşamba08:00–12:00',
      'Perşembe08:00–12:00',
      'Cuma08:00–12:00',
    ])
    expect(
      within(screen.getByRole('main')).getByRole('link', { name: 'Online Randevu' }),
    ).toHaveAttribute('href', PATHS.booking)
    expect(screen.queryByText('General Practice')).not.toBeInTheDocument()
    expect(calls.map((c) => c.path)).toEqual(['/public/doctors'])
  })

  it('is reached from the main menu', async () => {
    fakeBackend({ 'GET /public/doctors': () => DEPARTMENT_RECORD })
    renderApp(PATHS.home)
    const user = userEvent.setup()
    const menu = screen.getByRole('navigation', { name: 'Ana menü' })

    expect(within(menu).queryByRole('link', { name: 'Hekimlerimiz' })).not.toBeInTheDocument()
    await user.click(within(menu).getByRole('link', { name: 'Aile Hekimliği' }))

    expect(await screen.findByRole('heading', { level: 1, name: 'Aile Hekimliği' })).toBeVisible()
  })

  it('shows a message when the working hours cannot be loaded', async () => {
    fakeBackend({ 'GET /public/doctors': () => ({ status: 503, body: { detail: 'Down' } }) })
    renderApp(PATHS.department)

    expect(await screen.findByRole('alert')).toHaveTextContent('Çalışma saatleri alınamadı')
  })
})
