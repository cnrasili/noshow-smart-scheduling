import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { DEPARTMENT, PATIENT, PATIENT_NUMBER, fakeBackend, renderApp } from './backend'

const TOKEN = { token: 'new-token' }

async function signIn(name: string, label: string) {
  const user = userEvent.setup()
  await user.type(screen.getByLabelText(label), name)
  await user.type(screen.getByLabelText('Şifre'), 'demo1234')
  await user.click(screen.getByRole('button', { name: 'Giriş' }))
  return user
}

describe('patient login', () => {
  it('signs in with patient number and password and opens the booking', async () => {
    const calls = fakeBackend({
      'POST /auth/login': () => ({ ...PATIENT, ...TOKEN }),
      'GET /slots': () => [],
    })
    renderApp('/giris/hasta')

    expect(screen.getByRole('heading', { name: 'Hasta Girişi' })).toBeVisible()
    await signIn(PATIENT_NUMBER, 'Hasta numarası')

    expect(await screen.findByRole('heading', { name: 'Randevu al' })).toBeInTheDocument()
    expect(calls.find((c) => c.path === '/auth/login')?.body).toEqual({
      role: 'patient',
      patient_number: PATIENT_NUMBER,
      password: 'demo1234',
    })
    expect(localStorage.getItem('noshow.token')).toBe('new-token')
    expect(screen.getByText(`Hasta ${PATIENT_NUMBER}`, { selector: '.ribbon b' })).toBeVisible()
  })

  it('accepts patient numbers with a dot and keeps only digits and dots', async () => {
    fakeBackend({})
    renderApp('/giris/hasta')

    expect(screen.queryByText(/kimlik|e-posta/i)).not.toBeInTheDocument()
    const field = screen.getByLabelText('Hasta numarası')
    await userEvent.type(field, 'no 93779.52927')
    expect(field).toHaveValue('93779.52927')
  })

  it('shows a generic message for wrong credentials', async () => {
    fakeBackend({
      'POST /auth/login': () => ({
        status: 401,
        body: { detail: 'Wrong patient number or password' },
      }),
    })
    renderApp('/giris/hasta')

    await signIn(PATIENT_NUMBER, 'Hasta numarası')

    expect(await screen.findByRole('alert')).toHaveTextContent('Hasta numarası veya şifre hatalı.')
    expect(screen.getByRole('heading', { name: 'Hasta Girişi' })).toBeInTheDocument()
  })

  it('tells the user to wait after too many failed attempts', async () => {
    fakeBackend({
      'POST /auth/login': () => ({
        status: 429,
        body: { detail: 'Too many failed login attempts; try again later' },
      }),
    })
    renderApp('/giris/hasta')

    await signIn(PATIENT_NUMBER, 'Hasta numarası')

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Çok fazla başarısız giriş denemesi yapıldı. Lütfen 15 dakika sonra tekrar deneyin.',
    )
  })

  it('goes back to the entry page', async () => {
    fakeBackend({})
    renderApp('/giris/hasta')

    await userEvent.click(screen.getByRole('link', { name: 'Geri' }))

    expect(screen.getByRole('link', { name: 'Departman Girişi' })).toBeVisible()
  })
})

describe('department login', () => {
  it('signs in with username and password and opens the panel', async () => {
    const calls = fakeBackend({
      'POST /auth/login': () => ({ ...DEPARTMENT, ...TOKEN }),
      'GET /doctors/me/calendar': () => [],
      'GET /doctors/me/agenda': () => [],
      'GET /department/dataset-days': () => [],
    })
    renderApp('/giris/departman')

    expect(screen.getByRole('heading', { name: 'Departman Girişi' })).toBeVisible()
    await signIn('aile.hekimligi', 'Kullanıcı adı')

    const menu = await screen.findByRole('navigation', { name: 'Menü' })
    expect(within(menu).getByRole('link', { name: 'Bugünkü program' })).toBeInTheDocument()
    expect(calls.find((c) => c.path === '/auth/login')?.body).toEqual({
      role: 'department',
      username: 'aile.hekimligi',
      password: 'demo1234',
    })
    // The ribbon names the department, never a doctor
    expect(screen.getByText('Aile Hekimliği', { selector: '.ribbon b' })).toBeVisible()
    expect(within(menu).getByText('Departman paneli')).toBeInTheDocument()
  })

  it('shows a generic message for wrong credentials', async () => {
    fakeBackend({
      'POST /auth/login': () => ({ status: 401, body: { detail: 'Wrong username or password' } }),
    })
    renderApp('/giris/departman')

    await signIn('aile.hekimligi', 'Kullanıcı adı')

    expect(await screen.findByRole('alert')).toHaveTextContent('Kullanıcı adı veya şifre hatalı.')
  })
})
