import { useEffect, useState, type ReactNode } from 'react'
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router'
import { api, getToken, onUnauthorized } from './api'
import { PortalLayout } from './layout/PortalLayout'
import { PanelPage } from './pages/department/PanelPage'
import { SchedulePage } from './pages/department/SchedulePage'
import { EntryPage } from './pages/EntryPage'
import { LoginPage } from './pages/LoginPage'
import { AppointmentsPage } from './pages/patient/AppointmentsPage'
import { BookingPage } from './pages/patient/BookingPage'
import { OLD_PATHS, PATHS, homeFor, loginFor, type LoginReturn } from './routes'
import type { Me, Role } from './types'

type Session = { status: 'loading' } | { status: 'signed-out' } | { status: 'signed-in'; me: Me }

function App() {
  const navigate = useNavigate()
  const location = useLocation()
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

  if (session.status === 'loading') return <p className="center-text muted">Yükleniyor…</p>
  const me = session.status === 'signed-in' ? session.me : null

  // After signing in, continue to the page that sent the visitor to the login; otherwise to
  // the account's own home
  function afterLogin(user: Me) {
    const back = location.state as LoginReturn | null
    return back?.role === user.role ? back.from : homeFor(user.role)
  }

  function signedIn(next: Me) {
    setSession({ status: 'signed-in', me: next })
    navigate(afterLogin(next), { replace: true })
  }

  async function signOut() {
    await api.logout().catch(() => {})
    // A full load of the entry page also clears every screen's state left in memory
    window.location.replace(PATHS.home)
  }

  // Signed-out visitors go to the login form of the page's role; others to their own home
  function only(role: Role, page: ReactNode) {
    if (!me) {
      const back: LoginReturn = { from: location.pathname + location.search, role }
      return <Navigate to={loginFor(role)} replace state={back} />
    }
    return me.role === role ? page : <Navigate to={homeFor(me.role)} replace />
  }

  // The entry page and the login forms are for signed-out visitors
  function signedOutOnly(page: ReactNode) {
    return me ? <Navigate to={afterLogin(me)} replace /> : page
  }

  return (
    <Routes>
      <Route path={PATHS.home} element={signedOutOnly(<EntryPage />)} />
      {/* Login forms get a key per role so switching forms starts with empty fields */}
      <Route
        path={PATHS.patientLogin}
        element={signedOutOnly(<LoginPage key="patient" role="patient" onSignedIn={signedIn} />)}
      />
      <Route
        path={PATHS.departmentLogin}
        element={signedOutOnly(
          <LoginPage key="department" role="department" onSignedIn={signedIn} />,
        )}
      />
      {me && (
        <Route element={<PortalLayout me={me} onSignOut={signOut} />}>
          <Route path={PATHS.booking} element={only('patient', <BookingPage />)} />
          <Route path={PATHS.appointments} element={only('patient', <AppointmentsPage />)} />
          <Route path={PATHS.panel} element={only('department', <PanelPage />)} />
          <Route path={PATHS.schedule} element={only('department', <SchedulePage />)} />
        </Route>
      )}
      {!me &&
        [PATHS.booking, PATHS.appointments].map((path) => (
          <Route key={path} path={path} element={only('patient', null)} />
        ))}
      {!me &&
        [PATHS.panel, PATHS.schedule].map((path) => (
          <Route key={path} path={path} element={only('department', null)} />
        ))}
      {Object.entries(OLD_PATHS).map(([from, to]) => (
        <Route key={from} path={from} element={<Navigate to={to} replace />} />
      ))}
      <Route path="*" element={<Navigate to={PATHS.home} replace />} />
    </Routes>
  )
}

export default App
