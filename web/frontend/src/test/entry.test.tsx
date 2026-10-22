import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { INSTITUTION_NAME } from '../config'
import { DISCLAIMER } from '../pages/EntryPage'
import { PATHS } from '../routes'
import { DEPARTMENT, PATIENT, fakeBackend, renderApp, signIn } from './backend'

const PANEL = {
  'GET /doctors/me/calendar': () => [],
  'GET /doctors/me/agenda': () => [],
  'GET /department/dataset-days': () => [],
}

describe('entry page', () => {
  it('offers the patient and the department login', async () => {
    const calls = fakeBackend({})
    renderApp(PATHS.home)
    const user = userEvent.setup()

    expect(screen.getByRole('heading', { level: 1, name: INSTITUTION_NAME })).toBeVisible()
    expect(screen.getByText('Aile Hekimliği · online randevu')).toBeVisible()
    expect(screen.getByText(DISCLAIMER)).toBeInTheDocument()
    expect(document.title).toBe(INSTITUTION_NAME)

    await user.click(screen.getByRole('link', { name: 'Hasta Girişi' }))
    expect(screen.getByRole('heading', { name: 'Hasta Girişi' })).toBeVisible()
    await user.click(screen.getByRole('link', { name: 'Geri' }))
    await user.click(screen.getByRole('link', { name: 'Departman Girişi' }))
    expect(screen.getByRole('heading', { name: 'Departman Girişi' })).toBeVisible()
    expect(calls).toEqual([])
  })

  it('does not link to the management panel, which stays in the admin service', () => {
    fakeBackend({})
    renderApp(PATHS.home)

    expect(screen.getAllByRole('link').map((link) => link.getAttribute('href'))).toEqual([
      PATHS.patientLogin,
      PATHS.departmentLogin,
    ])
    expect(screen.getByText(/yalnızca hastane iç ağından açılır/)).toBeInTheDocument()
  })

  it('names no doctor, branch or national ID number', () => {
    fakeBackend({})
    for (const path of [PATHS.home, PATHS.patientLogin, PATHS.departmentLogin]) {
      const { container, unmount } = renderApp(path)
      // "Aile Hekimliği" is the department's name
      expect(container.textContent).not.toMatch(/\bDr\.|hekim(?!li)|branş|kimlik/i)
      expect(container.textContent).not.toMatch(/MHRS|e-Devlet|e-Nabız|Sağlık Bakanlığı/i)
      unmount()
    }
  })
})

describe('routing', () => {
  it('sends a signed-out visitor of a patient screen to the patient login and back', async () => {
    fakeBackend({ 'POST /auth/login': () => ({ ...PATIENT, token: 't' }), 'GET /slots': () => [] })
    renderApp(PATHS.appointments)
    const user = userEvent.setup()

    expect(screen.getByRole('heading', { name: 'Hasta Girişi' })).toBeVisible()
    await user.type(screen.getByLabelText('Hasta numarası'), '1')
    await user.type(screen.getByLabelText('Şifre'), 'demo1234')
    await user.click(screen.getByRole('button', { name: 'Giriş' }))

    expect(await screen.findByRole('heading', { name: 'Randevularım' })).toBeVisible()
  })

  it('sends a signed-out visitor of the panel to the department login', () => {
    fakeBackend({})
    renderApp(PATHS.panel)

    expect(screen.getByRole('heading', { name: 'Departman Girişi' })).toBeVisible()
  })

  it('takes a signed-in account from the entry page to its own home', async () => {
    fakeBackend({ ...signIn(DEPARTMENT), ...PANEL })
    renderApp(PATHS.home)

    expect(await screen.findByRole('link', { name: 'Bugünkü program' })).toBeVisible()
  })

  it('keeps the department out of the patient screens', async () => {
    fakeBackend({ ...signIn(DEPARTMENT), ...PANEL })
    renderApp(PATHS.booking)

    expect(await screen.findByRole('link', { name: 'Bugünkü program' })).toBeVisible()
    expect(screen.queryByRole('heading', { name: 'Randevu al' })).not.toBeInTheDocument()
  })

  it.each([
    ['/online-randevu', 'Randevu al'],
    ['/randevu-al', 'Randevu al'],
  ])('leads %s to the booking', async (path, heading) => {
    fakeBackend({ ...signIn(PATIENT), 'GET /slots': () => [] })
    renderApp(path)

    expect(await screen.findByRole('heading', { name: heading })).toBeVisible()
  })

  it('leads an unknown address to the entry page', () => {
    fakeBackend({})
    renderApp('/hekimlerimiz')

    expect(screen.getByRole('link', { name: 'Hasta Girişi' })).toBeVisible()
  })
})
