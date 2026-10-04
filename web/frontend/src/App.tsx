import { useEffect, useState } from 'react'
import { api, getToken, onUnauthorized } from './api'
import { INSTITUTION_NAME, SYSTEM_NAME } from './config'
import { SchedulePage } from './pages/doctor/SchedulePage'
import { WorklistPage } from './pages/doctor/WorklistPage'
import { LoginPage } from './pages/LoginPage'
import { AppointmentsPage } from './pages/patient/AppointmentsPage'
import { BookingPage } from './pages/patient/BookingPage'
import type { Me } from './types'

type Session = { status: 'loading' } | { status: 'signed-out' } | { status: 'signed-in'; me: Me }
type View = 'booking' | 'appointments' | 'worklist' | 'schedule'

const NAV: Record<Me['role'], { view: View; label: string }[]> = {
  patient: [
    { view: 'booking', label: 'Randevu Al' },
    { view: 'appointments', label: 'Randevularım' },
  ],
  doctor: [
    { view: 'worklist', label: 'Hasta Listesi' },
    { view: 'schedule', label: 'Çalışma Takvimi' },
  ],
}

function App() {
  const [session, setSession] = useState<Session>(() =>
    getToken() ? { status: 'loading' } : { status: 'signed-out' },
  )
  const [view, setView] = useState<View | null>(null)

  useEffect(() => {
    onUnauthorized(() => setSession({ status: 'signed-out' }))
    if (!getToken()) return
    // Restore the previous session
    api
      .me()
      .then((me) => setSession({ status: 'signed-in', me }))
      .catch(() => setSession({ status: 'signed-out' }))
  }, [])

  async function signOut() {
    await api.logout().catch(() => {})
    setView(null)
    setSession({ status: 'signed-out' })
  }

  if (session.status === 'loading') return <p className="center muted">Yükleniyor…</p>
  if (session.status === 'signed-out') {
    return <LoginPage onSignedIn={(me) => setSession({ status: 'signed-in', me })} />
  }

  const { me } = session
  const nav = NAV[me.role]
  const current = view && nav.some((item) => item.view === view) ? view : nav[0].view

  return (
    <div className="shell">
      <header className="topbar">
        <div className="container topbar-inner">
          <div className="brand">
            <span className="brand-name">{INSTITUTION_NAME}</span>
            <span className="brand-system">{SYSTEM_NAME}</span>
          </div>
          <div className="user">
            <div className="user-text">
              <span className="user-name">{me.name}</span>
              <span className="user-role">
                {me.role === 'doctor'
                  ? `Hekim${me.specialty ? ` · ${me.specialty}` : ''}`
                  : 'Hasta'}
              </span>
            </div>
            <button type="button" onClick={signOut}>
              Çıkış
            </button>
          </div>
        </div>
        <nav className="container nav" aria-label="Ana menü">
          {nav.map((item) => (
            <button
              key={item.view}
              type="button"
              className={item.view === current ? 'is-active' : ''}
              aria-current={item.view === current ? 'page' : undefined}
              onClick={() => setView(item.view)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="container main">
        {current === 'booking' && (
          <BookingPage onShowAppointments={() => setView('appointments')} />
        )}
        {current === 'appointments' && <AppointmentsPage onBook={() => setView('booking')} />}
        {current === 'worklist' && <WorklistPage />}
        {current === 'schedule' && <SchedulePage />}
      </main>
    </div>
  )
}

export default App
