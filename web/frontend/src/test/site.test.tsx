import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { INSTITUTION_NAME } from '../config'
import { ANNOUNCEMENTS, DISCLAIMER } from '../content/site'
import { PATHS, announcementPath } from '../routes'
import { DOCTOR, PATIENT, fakeBackend, renderApp, signIn } from './backend'

const STATIC_PAGES = [
  [PATHS.home, null],
  [PATHS.about, 'Hastanemiz'],
  [PATHS.announcements, 'Duyurular'],
  [announcementPath(ANNOUNCEMENTS[0].slug), ANNOUNCEMENTS[0].title],
  [PATHS.guide, 'Hasta Rehberi'],
  [PATHS.contact, 'İletişim ve Ulaşım'],
] as const

// Every address a link on the site may lead to
const KNOWN_PATHS = new Set<string>([
  ...Object.values(PATHS),
  ...ANNOUNCEMENTS.map((item) => announcementPath(item.slug)),
])

function expectFrame() {
  const header = screen.getByRole('banner')
  expect(within(header).getByRole('img', { name: `${INSTITUTION_NAME} logosu` })).toBeVisible()
  expect(within(header).getByText(INSTITUTION_NAME)).toBeInTheDocument()
  // A signed-in patient also has it in the account menu
  expect(within(header).getAllByRole('link', { name: 'Online Randevu' })[0]).toHaveAttribute(
    'href',
    PATHS.booking,
  )
  expect(screen.getByRole('navigation', { name: 'Ana menü' })).toBeInTheDocument()
  expect(within(screen.getByRole('contentinfo')).getByText(DISCLAIMER)).toBeInTheDocument()
}

describe('hospital site frame', () => {
  it.each(STATIC_PAGES)('shows the frame and the page title on %s', async (path, title) => {
    fakeBackend({})
    renderApp(path)

    if (title) expect(await screen.findByRole('heading', { level: 1, name: title })).toBeVisible()
    expectFrame()
    const header = screen.getByRole('banner')
    expect(within(header).getByRole('link', { name: 'Hasta Girişi' })).toBeInTheDocument()
    expect(within(header).getByRole('link', { name: 'Hekim Girişi' })).toBeInTheDocument()
    expect(document.title).toBe(title ? `${title} | ${INSTITUTION_NAME}` : INSTITUTION_NAME)
  })

  it('shows the frame on the login pages', async () => {
    fakeBackend({})
    renderApp(PATHS.patientLogin)

    expect(await screen.findByRole('heading', { name: 'Hasta girişi' })).toBeVisible()
    expectFrame()
    expect(document.title).toBe(`Hasta girişi | ${INSTITUTION_NAME}`)
  })

  it('keeps the frame for a signed-in patient, with the account menu', async () => {
    fakeBackend({ ...signIn(PATIENT), 'GET /doctors': () => [] })
    renderApp(PATHS.booking)

    expect(await screen.findByRole('heading', { name: 'Online Randevu' })).toBeVisible()
    expectFrame()
    const account = screen.getByRole('navigation', { name: 'Hesap menüsü' })
    expect(within(account).getByRole('link', { name: 'Randevularım' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Çıkış' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Hasta Girişi' })).not.toBeInTheDocument()
  })

  it('lets a signed-in doctor open the home page and keeps the doctor screens', async () => {
    fakeBackend({ ...signIn(DOCTOR) })
    renderApp(PATHS.home)

    expect(await screen.findByRole('heading', { level: 1, name: INSTITUTION_NAME })).toBeVisible()
    const account = screen.getByRole('navigation', { name: 'Hesap menüsü' })
    expect(within(account).getByRole('link', { name: 'Hasta Listesi' })).toBeInTheDocument()
  })
})

describe('hospital site pages', () => {
  it('opens every main menu page without signing in', async () => {
    const calls = fakeBackend({})
    renderApp(PATHS.home)
    const user = userEvent.setup()
    const menu = screen.getByRole('navigation', { name: 'Ana menü' })

    for (const [name, heading] of [
      ['Hastanemiz', 'Hastanemiz'],
      ['Duyurular', 'Duyurular'],
      ['Hasta Rehberi', 'Hasta Rehberi'],
      ['İletişim ve Ulaşım', 'İletişim ve Ulaşım'],
      ['Anasayfa', INSTITUTION_NAME],
    ]) {
      await user.click(within(menu).getByRole('link', { name }))
      expect(await screen.findByRole('heading', { level: 1, name: heading })).toBeVisible()
    }
    expect(calls).toEqual([])
  })

  it('has no link to a missing page', () => {
    fakeBackend({})
    for (const [path] of STATIC_PAGES) {
      const { unmount } = renderApp(path)
      for (const link of screen.getAllByRole('link')) {
        const href = link.getAttribute('href')!
        if (href.startsWith('mailto:')) continue
        expect(KNOWN_PATHS, `${href} on ${path}`).toContain(href.split('#')[0])
      }
      unmount()
    }
  })

  it('shows the latest announcements and quick actions on the home page', async () => {
    fakeBackend({})
    renderApp(PATHS.home)
    const user = userEvent.setup()

    for (const name of ['Online Randevu', 'Nasıl Giderim?', 'Hasta Rehberi']) {
      expect(screen.getAllByRole('link', { name: new RegExp(`^${name}`) }).length).toBeGreaterThan(
        0,
      )
    }
    await user.click(screen.getByRole('link', { name: ANNOUNCEMENTS[0].title }))

    expect(await screen.findByRole('heading', { name: ANNOUNCEMENTS[0].title })).toBeVisible()
    expect(screen.getByText(ANNOUNCEMENTS[0].body[0])).toBeInTheDocument()
  })

  it('covers the patient guide topics', async () => {
    fakeBackend({})
    renderApp(PATHS.guide)

    for (const topic of [
      'Randevu nasıl alınır?',
      'Randevuya gelirken yanınızda bulundurun',
      'Randevu saatinden 15 dakika önce gelin',
      'Gelemeyecekseniz randevunuzu iptal edin',
    ]) {
      expect(await screen.findByRole('heading', { name: topic })).toBeVisible()
    }
  })

  it('sends an unknown announcement address back to the list', async () => {
    fakeBackend({})
    renderApp(announcementPath('yok'))

    expect(await screen.findByRole('heading', { level: 1, name: 'Duyurular' })).toBeVisible()
  })

  it('names no real government service', () => {
    fakeBackend({})
    for (const [path] of STATIC_PAGES) {
      const { container, unmount } = renderApp(path)
      expect(container.textContent).not.toMatch(/MHRS|e-Devlet|e-Nabız|Sağlık Bakanlığı/i)
      unmount()
    }
  })
})
