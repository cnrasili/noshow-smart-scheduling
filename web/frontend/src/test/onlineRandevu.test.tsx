import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { PATHS, bookingPath, departmentPath } from '../routes'
import type { Doctor, PublicDoctor } from '../types'
import { DOCTOR, PATIENT, fakeBackend, renderApp, signIn } from './backend'

const DOCTORS: Doctor[] = [
  { id: 1, full_name: 'Dr. Deniz Yıldız', specialty: 'Dahiliye' },
  { id: 2, full_name: 'Dr. Can Özkan', specialty: 'Dahiliye' },
  { id: 3, full_name: 'Dr. Leyla Aksoy', specialty: 'Kardiyoloji' },
  { id: 4, full_name: 'Dr. Selim Karataş', specialty: 'Kardiyoloji' },
]

const PUBLIC: PublicDoctor[] = DOCTORS.map((doctor) => ({ ...doctor, working_hours: [] }))

const booking = {
  'GET /doctors': () => DOCTORS,
  'GET /slots': () => [],
  'GET /public/doctors': () => PUBLIC,
}

async function expectSelection(department: string, doctorId: string) {
  expect(await screen.findByRole('heading', { level: 1, name: 'Online Randevu' })).toBeVisible()
  await screen.findByRole('option', { name: 'Kardiyoloji' })
  expect(screen.getByLabelText('Branş')).toHaveValue(department)
  expect(screen.getByLabelText('Hekim')).toHaveValue(doctorId)
}

async function signInAsPatient(user: ReturnType<typeof userEvent.setup>) {
  expect(await screen.findByRole('heading', { name: 'Hasta girişi' })).toBeVisible()
  await user.type(screen.getByLabelText('T.C. kimlik numarası'), '99999000184')
  await user.type(screen.getByLabelText('Şifre'), 'demo1234')
  await user.click(screen.getByRole('button', { name: 'Giriş yap' }))
}

describe('Online Randevu', () => {
  it('takes a signed-out visitor from the header through the patient login to the booking', async () => {
    fakeBackend({ ...booking, 'POST /auth/login': () => ({ ...PATIENT, token: 't' }) })
    renderApp(PATHS.about)
    const user = userEvent.setup()

    await user.click(
      within(screen.getByRole('banner')).getByRole('link', { name: 'Online Randevu' }),
    )
    await signInAsPatient(user)

    await expectSelection('Dahiliye', '1')
  })

  it('keeps the department chosen on its page through the login', async () => {
    fakeBackend({ ...booking, 'POST /auth/login': () => ({ ...PATIENT, token: 't' }) })
    renderApp(departmentPath('Kardiyoloji'))
    const user = userEvent.setup()

    await screen.findByRole('heading', { level: 1, name: 'Kardiyoloji' })
    await user.click(
      within(screen.getByRole('main')).getAllByRole('link', { name: 'Online Randevu' })[0],
    )
    await signInAsPatient(user)

    await expectSelection('Kardiyoloji', '3')
  })

  it('opens the booking with the doctor of a card selected, and the patient can change it', async () => {
    fakeBackend({ ...signIn(PATIENT), ...booking })
    renderApp(PATHS.doctors)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('link', { name: 'Dr. Selim Karataş: Online Randevu' }))

    await expectSelection('Kardiyoloji', '4')
    await user.selectOptions(screen.getByLabelText('Branş'), 'Dahiliye')
    expect(screen.getByLabelText('Hekim')).toHaveValue('1')
  })

  it('tells a signed-in doctor that booking needs a patient account', async () => {
    const calls = fakeBackend({ ...signIn(DOCTOR), ...booking })
    renderApp(bookingPath({ department: 'Kardiyoloji' }))

    expect(await screen.findByText(/hasta hesabıyla giriş yapmanız gerekir/)).toBeVisible()
    expect(calls.some((c) => c.path === '/slots')).toBe(false)
  })

  it('redirects the old booking address and keeps the preselection', async () => {
    fakeBackend({ ...signIn(PATIENT), ...booking })
    renderApp('/randevu-al?hekim=3')

    await expectSelection('Kardiyoloji', '3')
  })

  it('names the booking Online Randevu in the account menu', async () => {
    fakeBackend({ ...signIn(PATIENT), ...booking })
    renderApp(PATHS.appointments.toString())

    const account = await screen.findByRole('navigation', { name: 'Hesap menüsü' })
    expect(within(account).getByRole('link', { name: 'Online Randevu' })).toHaveAttribute(
      'href',
      PATHS.booking,
    )
    expect(screen.queryByText('Randevu Al')).not.toBeInTheDocument()
  })

  it('ignores an unknown preselection', async () => {
    fakeBackend({ ...signIn(PATIENT), ...booking })
    renderApp(bookingPath({ department: 'Yok', doctorId: 99 }))

    await expectSelection('Dahiliye', '1')
  })
})
