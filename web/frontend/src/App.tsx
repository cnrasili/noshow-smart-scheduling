import { useEffect, useState } from 'react'
import { api, getToken, onUnauthorized } from './api'
import { LoginPage } from './pages/LoginPage'
import { PatientPage } from './pages/PatientPage'
import type { Me } from './types'

type Session = { status: 'loading' } | { status: 'signed-out' } | { status: 'signed-in'; me: Me }

function App() {
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

  async function signOut() {
    await api.logout().catch(() => {})
    setSession({ status: 'signed-out' })
  }

  if (session.status === 'loading') return <p className="center muted">Yükleniyor…</p>
  if (session.status === 'signed-out') {
    return <LoginPage onSignedIn={(me) => setSession({ status: 'signed-in', me })} />
  }

  const { me } = session
  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <span className="brand">Poliklinik Randevu Sistemi</span>
          <div className="user">
            <span className="role">{me.role === 'doctor' ? 'Doktor' : 'Hasta'}</span>
            <span>{me.name}</span>
            <button type="button" onClick={signOut}>
              Çıkış
            </button>
          </div>
        </div>
      </header>
      <main className="app">
        {me.role === 'patient' ? (
          <PatientPage />
        ) : (
          <p className="muted">Doktor ekranı hazırlanıyor.</p>
        )}
      </main>
    </>
  )
}

export default App
