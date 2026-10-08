import { Link, NavLink, Outlet } from 'react-router'
import { INSTITUTION_NAME } from '../config'
import { CONTACT, DISCLAIMER } from '../content/site'
import { PATHS } from '../routes'
import type { Me, Role } from '../types'
import { Logo } from './Logo'

interface MenuItem {
  to: string
  label: string
}

// Main menu of the hospital site, the same for every visitor
const MAIN_MENU: MenuItem[] = [
  { to: PATHS.home, label: 'Anasayfa' },
  { to: PATHS.about, label: 'Hastanemiz' },
  { to: PATHS.departments, label: 'Poliklinikler' },
  { to: PATHS.doctors, label: 'Hekimlerimiz' },
  { to: PATHS.workingList, label: 'Hekim Çalışma Listesi' },
  { to: PATHS.announcements, label: 'Duyurular' },
  { to: PATHS.guide, label: 'Hasta Rehberi' },
  { to: PATHS.contact, label: 'İletişim ve Ulaşım' },
]

// Screens of a signed-in account, shown under the main menu
const ACCOUNT_MENU: Record<Role, MenuItem[]> = {
  patient: [
    { to: PATHS.booking, label: 'Randevu Al' },
    { to: PATHS.appointments, label: 'Randevularım' },
  ],
  doctor: [
    { to: PATHS.worklist, label: 'Hasta Listesi' },
    { to: PATHS.schedule, label: 'Çalışma Takvimi' },
  ],
}

const QUICK_LINKS: MenuItem[] = [
  { to: PATHS.booking, label: 'Online Randevu' },
  { to: PATHS.workingList, label: 'Hekim Çalışma Listesi' },
  { to: PATHS.guide, label: 'Hasta Rehberi' },
  { to: PATHS.contact, label: 'Nasıl Giderim?' },
]

const activeClass = ({ isActive }: { isActive: boolean }) => (isActive ? 'is-active' : '')

function Header({ me, onSignOut }: { me: Me | null; onSignOut: () => void }) {
  return (
    <header className="site-header">
      <div className="container site-header-inner">
        <Link to={PATHS.home} className="site-brand">
          <Logo />
          <span className="site-name">{INSTITUTION_NAME}</span>
        </Link>
        <div className="site-actions">
          <Link to={PATHS.booking} className="button primary">
            Online Randevu
          </Link>
          {me ? (
            <div className="user">
              <div className="user-text">
                <span className="user-name">{me.name}</span>
                <span className="user-role">
                  {me.role === 'doctor'
                    ? `Hekim${me.specialty ? ` · ${me.specialty}` : ''}`
                    : 'Hasta'}
                </span>
              </div>
              <button type="button" onClick={onSignOut}>
                Çıkış
              </button>
            </div>
          ) : (
            <>
              <Link to={PATHS.patientLogin} className="button">
                Hasta Girişi
              </Link>
              <Link to={PATHS.doctorLogin} className="button">
                Hekim Girişi
              </Link>
            </>
          )}
        </div>
      </div>
      <nav className="site-menu" aria-label="Ana menü">
        <div className="container site-menu-inner">
          {MAIN_MENU.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === PATHS.home}
              className={activeClass}
            >
              {item.label}
            </NavLink>
          ))}
        </div>
      </nav>
      {me && (
        <nav className="container nav" aria-label="Hesap menüsü">
          {ACCOUNT_MENU[me.role].map((item) => (
            <NavLink key={item.to} to={item.to} className={activeClass}>
              {item.label}
            </NavLink>
          ))}
        </nav>
      )}
    </header>
  )
}

function Footer() {
  return (
    <footer className="site-footer">
      <div className="container site-footer-grid">
        <section aria-labelledby="footer-contact">
          <h2 id="footer-contact">{INSTITUTION_NAME}</h2>
          <address>
            {CONTACT.address}
            <br />
            Telefon: {CONTACT.phone}
            <br />
            E-posta: <a href={`mailto:${CONTACT.email}`}>{CONTACT.email}</a>
          </address>
        </section>
        <nav aria-labelledby="footer-links">
          <h2 id="footer-links">Hızlı bağlantılar</h2>
          <ul>
            {QUICK_LINKS.map((item) => (
              <li key={item.label}>
                <Link to={item.to}>{item.label}</Link>
              </li>
            ))}
          </ul>
        </nav>
        <nav aria-labelledby="footer-menu">
          <h2 id="footer-menu">Kurumsal</h2>
          <ul>
            {MAIN_MENU.slice(1).map((item) => (
              <li key={item.to}>
                <Link to={item.to}>{item.label}</Link>
              </li>
            ))}
          </ul>
        </nav>
      </div>
      <p className="container disclaimer">{DISCLAIMER}</p>
    </footer>
  )
}

/** Frame of every page: header with the main menu, the page, and the footer. */
export function SiteLayout({ me, onSignOut }: { me: Me | null; onSignOut: () => void }) {
  return (
    <div className="site">
      <Header me={me} onSignOut={onSignOut} />
      <main className="container main">
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}
