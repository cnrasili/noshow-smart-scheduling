import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { DEPARTMENT, PATIENT, PATIENT_NUMBER, fakeBackend, renderApp } from './backend'

const TOKEN = { token: 'new-token' }

describe('patient login', () => {
  it('signs in with patient number and password and opens booking', async () => {
    const calls = fakeBackend({
      'POST /auth/login': () => ({ ...PATIENT, ...TOKEN }),
      'GET /slots': () => [],
    })
    renderApp('/giris/hasta')
    const user = userEvent.setup()

    await user.type(screen.getByLabelText('Hasta numarası'), PATIENT_NUMBER)
    await user.type(screen.getByLabelText('Şifre'), 'demo1234')
    await user.click(screen.getByRole('button', { name: 'Giriş yap' }))

    expect(await screen.findByRole('heading', { name: 'Online Randevu' })).toBeInTheDocument()
    expect(calls.find((c) => c.path === '/auth/login')?.body).toEqual({
      role: 'patient',
      patient_number: PATIENT_NUMBER,
      password: 'demo1234',
    })
    expect(localStorage.getItem('noshow.token')).toBe('new-token')
  })

  it('accepts patient numbers with a dot and keeps only digits and dots', async () => {
    fakeBackend({})
    renderApp('/giris/hasta')

    expect(screen.queryByLabelText('E-posta adresi')).not.toBeInTheDocument()
    expect(screen.queryByText(/kimlik/i)).not.toBeInTheDocument()
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
    const user = userEvent.setup()

    await user.type(screen.getByLabelText('Hasta numarası'), PATIENT_NUMBER)
    await user.type(screen.getByLabelText('Şifre'), 'wrong-password')
    await user.click(screen.getByRole('button', { name: 'Giriş yap' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Hasta numarası veya şifre hatalı.')
    expect(screen.getByRole('heading', { name: 'Hasta girişi' })).toBeInTheDocument()
  })

  it('tells the user to wait after too many failed attempts', async () => {
    fakeBackend({
      'POST /auth/login': () => ({
        status: 429,
        body: { detail: 'Too many failed login attempts; try again later' },
      }),
    })
    renderApp('/giris/hasta')
    const user = userEvent.setup()

    await user.type(screen.getByLabelText('Hasta numarası'), PATIENT_NUMBER)
    await user.type(screen.getByLabelText('Şifre'), 'demo1234')
    await user.click(screen.getByRole('button', { name: 'Giriş yap' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Çok fazla başarısız giriş denemesi yapıldı. Lütfen 15 dakika sonra tekrar deneyin.',
    )
  })
})

describe('department login', () => {
  it('signs in with username and password and opens the patient list', async () => {
    const calls = fakeBackend({
      'POST /auth/login': () => ({ ...DEPARTMENT, ...TOKEN }),
      'GET /doctors/me/calendar': () => [],
    })
    renderApp('/giris/departman')
    const user = userEvent.setup()

    expect(screen.getByRole('heading', { name: 'Departman girişi' })).toBeInTheDocument()
    await user.type(screen.getByLabelText('Kullanıcı adı'), 'aile.hekimligi')
    await user.type(screen.getByLabelText('Şifre'), 'demo1234')
    await user.click(screen.getByRole('button', { name: 'Giriş yap' }))

    expect(await screen.findByRole('heading', { name: 'Hasta Listesi' })).toBeInTheDocument()
    expect(calls.find((c) => c.path === '/auth/login')?.body).toEqual({
      role: 'department',
      username: 'aile.hekimligi',
      password: 'demo1234',
    })
    // The header names the department, never a doctor
    expect(screen.getByText('Aile Hekimliği', { selector: '.user-name' })).toBeInTheDocument()
    expect(screen.getByText('Departman', { selector: '.user-role' })).toBeInTheDocument()
  })

  it('shows a generic message for wrong credentials', async () => {
    fakeBackend({
      'POST /auth/login': () => ({ status: 401, body: { detail: 'Wrong username or password' } }),
    })
    renderApp('/giris/departman')
    const user = userEvent.setup()

    await user.type(screen.getByLabelText('Kullanıcı adı'), 'aile.hekimligi')
    await user.type(screen.getByLabelText('Şifre'), 'wrong-password')
    await user.click(screen.getByRole('button', { name: 'Giriş yap' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Kullanıcı adı veya şifre hatalı.')
  })
})
