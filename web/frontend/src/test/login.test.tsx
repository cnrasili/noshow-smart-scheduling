import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { DOCTOR, PATIENT, fakeBackend, renderApp } from './backend'

const TOKEN = { token: 'new-token' }

describe('patient login', () => {
  it('signs in with national ID number and password and opens booking', async () => {
    const calls = fakeBackend({
      'POST /auth/login': () => ({ ...PATIENT, ...TOKEN }),
      'GET /doctors': () => [],
    })
    renderApp('/giris/hasta')
    const user = userEvent.setup()

    await user.type(screen.getByLabelText('T.C. kimlik numarası'), '99999000184')
    await user.type(screen.getByLabelText('Şifre'), 'demo1234')
    await user.click(screen.getByRole('button', { name: 'Giriş yap' }))

    expect(await screen.findByRole('heading', { name: 'Randevu Al' })).toBeInTheDocument()
    expect(calls.find((c) => c.path === '/auth/login')?.body).toEqual({
      role: 'patient',
      national_id: '99999000184',
      password: 'demo1234',
    })
    expect(localStorage.getItem('noshow.token')).toBe('new-token')
  })

  it('has no e-mail field and keeps only digits in the national ID field', async () => {
    fakeBackend({})
    renderApp('/giris/hasta')

    expect(screen.queryByLabelText('E-posta adresi')).not.toBeInTheDocument()
    const field = screen.getByLabelText('T.C. kimlik numarası')
    await userEvent.type(field, 'ayse@demo.local 999')
    expect(field).toHaveValue('999')
  })

  it('checks the national ID number before asking the backend', async () => {
    const calls = fakeBackend({})
    renderApp('/giris/hasta')
    const user = userEvent.setup()

    await user.type(screen.getByLabelText('T.C. kimlik numarası'), '99999000185')
    await user.type(screen.getByLabelText('Şifre'), 'demo1234')
    await user.click(screen.getByRole('button', { name: 'Giriş yap' }))

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Geçerli bir T.C. kimlik numarası girin (11 hane).',
    )
    expect(calls).toEqual([])
  })

  it('shows a generic message for wrong credentials', async () => {
    fakeBackend({
      'POST /auth/login': () => ({
        status: 401,
        body: { detail: 'Wrong national ID number or password' },
      }),
    })
    renderApp('/giris/hasta')
    const user = userEvent.setup()

    await user.type(screen.getByLabelText('T.C. kimlik numarası'), '99999000184')
    await user.type(screen.getByLabelText('Şifre'), 'wrong-password')
    await user.click(screen.getByRole('button', { name: 'Giriş yap' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'T.C. kimlik numarası veya şifre hatalı.',
    )
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

    await user.type(screen.getByLabelText('T.C. kimlik numarası'), '99999000184')
    await user.type(screen.getByLabelText('Şifre'), 'demo1234')
    await user.click(screen.getByRole('button', { name: 'Giriş yap' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Çok fazla başarısız giriş denemesi yapıldı. Lütfen 15 dakika sonra tekrar deneyin.',
    )
  })
})

describe('doctor login', () => {
  it('signs in with e-mail and password and opens the patient list', async () => {
    const calls = fakeBackend({
      'POST /auth/login': () => ({ ...DOCTOR, ...TOKEN }),
      'GET /doctors/me/calendar': () => [],
    })
    renderApp('/giris/hekim')
    const user = userEvent.setup()

    await user.type(screen.getByLabelText('E-posta adresi'), 'doktor@demo.local')
    await user.type(screen.getByLabelText('Şifre'), 'demo1234')
    await user.click(screen.getByRole('button', { name: 'Giriş yap' }))

    expect(await screen.findByRole('heading', { name: 'Hasta Listesi' })).toBeInTheDocument()
    expect(calls.find((c) => c.path === '/auth/login')?.body).toEqual({
      role: 'doctor',
      email: 'doktor@demo.local',
      password: 'demo1234',
    })
  })

  it('shows a generic message for wrong credentials', async () => {
    fakeBackend({
      'POST /auth/login': () => ({ status: 401, body: { detail: 'Wrong email or password' } }),
    })
    renderApp('/giris/hekim')
    const user = userEvent.setup()

    await user.type(screen.getByLabelText('E-posta adresi'), 'doktor@demo.local')
    await user.type(screen.getByLabelText('Şifre'), 'wrong-password')
    await user.click(screen.getByRole('button', { name: 'Giriş yap' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('E-posta adresi veya şifre hatalı.')
  })
})
