import { useEffect, useState, type ReactNode } from 'react'
import { NavLink, Navigate, Outlet, Route, Routes, useNavigate } from 'react-router'
import { api, getToken, onUnauthorized } from './api'
import { INSTITUTION_NAME, SYSTEM_NAME } from './config'
import { SchedulePage } from './pages/doctor/SchedulePage'
import { WorklistPage } from './pages/doctor/WorklistPage'
import { HomePage } from './pages/HomePage'
import { LoginPage } from './pages/LoginPage'
import { AppointmentsPage } from './pages/patient/AppointmentsPage'
import { BookingPage } from './pages/patient/BookingPage'
import { PATHS, homeFor, loginFor } from './routes'
import type { Me, Role } from './types'

type Session = { status: 'loading' } | { status: 'signed-out' } | { status: 'signed-in'; me: Me }

const NAV: Record<Role, { to: string; label: string }[]> = {
  patient: [
    { to: PATHS.booking, label: 'Randevu Al' },
    { to: PATHS.appointments, label: 'Randevularım' },
  ],
  doctor: [
    { to: PATHS.worklist, label: 'Hasta Listesi' },
    { to: PATHS.schedule, label: 'Çalışma Takvimi' },
  ],
}

function Shell({ me, onSignOut }: { me: Me; onSignOut: () => void }) {
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
            <button type="button" onClick={onSignOut}>
              Çıkış
            </button>
          </div>
        </div>
        <nav className="container nav" aria-label="Ana menü">
          {NAV[me.role].map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? 'is-active' : '')}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="container main">
        <Outlet />
      </main>
    </div>
  )
}

function App() {
  const navigate = useNavigate()
  const [session, setSession] = useState<Session>(() =>
    getToken() ? { status: 'loading' } : { status: 'signed-out' },
  )

  useEffect(() => {
    onUnauthorized(() => setSession({ status: 'signed-out' }))
    if (!getToken()) return
    // Restore the previous session
    api
      .me()
      .then((me) => setSession({ status: 'signed-in', me }))
      .catch(() => setSession({ status: 'signed-out' }))
  }, [])

  if (session.status === 'loading') return <p className="center muted">Yükleniyor…</p>
  const me = session.status === 'signed-in' ? session.me : null

  function signedIn(next: Me) {
    setSession({ status: 'signed-in', me: next })
    navigate(homeFor(next.role), { replace: true })
  }

  async function signOut() {
    await api.logout().catch(() => {})
    // A full load of the landing page also clears every screen's state left in memory
    window.location.replace(PATHS.home)
  }

  // Signed-out visitors go to the login form of the page's role; others to their own home
  function only(role: Role, page: ReactNode) {
    if (!me) return <Navigate to={loginFor(role)} replace />
    return me.role === role ? page : <Navigate to={homeFor(me.role)} replace />
  }

  // Login forms get a key per role so switching forms starts with empty fields
  function publicPage(page: ReactNode) {
    return me ? <Navigate to={homeFor(me.role)} replace /> : page
  }

  return (
    <Routes>
      <Route path={PATHS.home} element={publicPage(<HomePage />)} />
      <Route
        path={PATHS.patientLogin}
        element={publicPage(<LoginPage key="patient" role="patient" onSignedIn={signedIn} />)}
      />
      <Route
        path={PATHS.doctorLogin}
        element={publicPage(<LoginPage key="doctor" role="doctor" onSignedIn={signedIn} />)}
      />
      <Route element={me ? <Shell me={me} onSignOut={signOut} /> : <Outlet />}>
        <Route
          path={PATHS.booking}
          element={only(
            'patient',
            <BookingPage onShowAppointments={() => navigate(PATHS.appointments)} />,
          )}
        />
        <Route
          path={PATHS.appointments}
          element={only('patient', <AppointmentsPage onBook={() => navigate(PATHS.booking)} />)}
        />
        <Route path={PATHS.worklist} element={only('doctor', <WorklistPage />)} />
        <Route path={PATHS.schedule} element={only('doctor', <SchedulePage />)} />
      </Route>
      <Route path="*" element={<Navigate to={PATHS.home} replace />} />
    </Routes>
  )
}

export default App
