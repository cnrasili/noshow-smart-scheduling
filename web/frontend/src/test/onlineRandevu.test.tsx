import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { PATHS } from '../routes'
import { DEPARTMENT, PATIENT, PATIENT_NUMBER, fakeBackend, renderApp, signIn } from './backend'

const booking = {
  'GET /slots': () => [],
  'GET /public/doctors': () => [],
}

async function signInAsPatient(user: ReturnType<typeof userEvent.setup>) {
  expect(await screen.findByRole('heading', { name: 'Hasta girişi' })).toBeVisible()
  await user.type(screen.getByLabelText('Hasta numarası'), PATIENT_NUMBER)
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

    expect(await screen.findByRole('heading', { level: 1, name: 'Online Randevu' })).toBeVisible()
    expect(screen.getByText('Aile Hekimliği için uygun gün ve saati seçin.')).toBeInTheDocument()
  })

  it('opens the booking from the department page through the login', async () => {
    fakeBackend({ ...booking, 'POST /auth/login': () => ({ ...PATIENT, token: 't' }) })
    renderApp(PATHS.department)
    const user = userEvent.setup()

    await screen.findByRole('heading', { level: 1, name: 'Aile Hekimliği' })
    await user.click(
      within(screen.getByRole('main')).getAllByRole('link', { name: 'Online Randevu' })[0],
    )
    await signInAsPatient(user)

    expect(await screen.findByRole('heading', { level: 1, name: 'Online Randevu' })).toBeVisible()
  })

  it('tells the signed-in department that booking needs a patient account', async () => {
    const calls = fakeBackend({ ...signIn(DEPARTMENT), ...booking })
    renderApp(PATHS.booking)

    expect(await screen.findByText(/hasta hesabıyla giriş yapmanız gerekir/)).toBeVisible()
    expect(calls.some((c) => c.path === '/slots')).toBe(false)
  })

  it('redirects the old booking address', async () => {
    fakeBackend({ ...signIn(PATIENT), ...booking })
    renderApp('/randevu-al')

    expect(await screen.findByRole('heading', { level: 1, name: 'Online Randevu' })).toBeVisible()
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
})
