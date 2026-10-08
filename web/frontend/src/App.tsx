import { useEffect, useState, type ReactNode } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router'
import { api, getToken, onUnauthorized } from './api'
import { SchedulePage } from './pages/doctor/SchedulePage'
import { WorklistPage } from './pages/doctor/WorklistPage'
import { HomePage } from './pages/HomePage'
import { LoginPage } from './pages/LoginPage'
import { AppointmentsPage } from './pages/patient/AppointmentsPage'
import { BookingPage } from './pages/patient/BookingPage'
import { AboutPage } from './pages/site/AboutPage'
import { AnnouncementPage, AnnouncementsPage } from './pages/site/AnnouncementsPage'
import { ContactPage } from './pages/site/ContactPage'
import { DepartmentPage, DepartmentsPage } from './pages/site/DepartmentsPage'
import { DoctorsPage } from './pages/site/DoctorsPage'
import { GuidePage } from './pages/site/GuidePage'
import { WorkingListPage } from './pages/site/WorkingListPage'
import { PATHS, homeFor, loginFor } from './routes'
import { SiteLayout } from './site/SiteLayout'
import type { Me, Role } from './types'

type Session = { status: 'loading' } | { status: 'signed-out' } | { status: 'signed-in'; me: Me }

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
  function signedOutOnly(page: ReactNode) {
    return me ? <Navigate to={homeFor(me.role)} replace /> : page
  }

  return (
    <Routes>
      <Route element={<SiteLayout me={me} onSignOut={signOut} />}>
        <Route path={PATHS.home} element={<HomePage />} />
        <Route path={PATHS.about} element={<AboutPage />} />
        <Route path={PATHS.departments} element={<DepartmentsPage />} />
        <Route path={`${PATHS.departments}/:slug`} element={<DepartmentPage />} />
        <Route path={PATHS.doctors} element={<DoctorsPage />} />
        <Route path={PATHS.workingList} element={<WorkingListPage />} />
        <Route path={PATHS.announcements} element={<AnnouncementsPage />} />
        <Route path={`${PATHS.announcements}/:slug`} element={<AnnouncementPage />} />
        <Route path={PATHS.guide} element={<GuidePage />} />
        <Route path={PATHS.contact} element={<ContactPage />} />
        <Route
          path={PATHS.patientLogin}
          element={signedOutOnly(<LoginPage key="patient" role="patient" onSignedIn={signedIn} />)}
        />
        <Route
          path={PATHS.doctorLogin}
          element={signedOutOnly(<LoginPage key="doctor" role="doctor" onSignedIn={signedIn} />)}
        />
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
