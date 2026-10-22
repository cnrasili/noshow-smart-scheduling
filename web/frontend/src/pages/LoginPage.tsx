import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { ApiError, api, errorText } from '../api'
import { DEPARTMENT_NAME } from '../config'
import { PATHS } from '../routes'
import { usePageTitle } from '../title'
import type { LoginCredentials, Me, Role } from '../types'

// Backend answers for wrong credentials; both are shown with the form's own message
const WRONG_CREDENTIALS = ['Wrong patient number or password', 'Wrong username or password']
// Shown when the backend refuses logins after too many failures (429)
const TOO_MANY_ATTEMPTS =
  'Çok fazla başarısız giriş denemesi yapıldı. Lütfen 15 dakika sonra tekrar deneyin.'

const COPY: Record<Role, { title: string; description: string; wrongCredentials: string }> = {
  patient: {
    title: 'Hasta Girişi',
    description: 'Hasta numaranız ve şifrenizle giriş yapın',
    wrongCredentials: 'Hasta numarası veya şifre hatalı.',
  },
  department: {
    title: 'Departman Girişi',
    description: `${DEPARTMENT_NAME} departman paneli`,
    wrongCredentials: 'Kullanıcı adı veya şifre hatalı.',
  },
}

export function LoginPage({ role, onSignedIn }: { role: Role; onSignedIn: (me: Me) => void }) {
  // Patient number on the patient form, username on the department form
  const [login, setLogin] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const copy = COPY[role]
  usePageTitle(copy.title)

  async function submit(event: FormEvent) {
    event.preventDefault()
    const name = login.trim()
    const credentials: LoginCredentials =
      role === 'patient'
        ? { role, patient_number: name, password }
        : { role, username: name, password }
    setBusy(true)
    setError(null)
    try {
      onSignedIn(await api.login(credentials))
    } catch (err) {
      const message = errorText(err)
      if (err instanceof ApiError && err.status === 429) setError(TOO_MANY_ATTEMPTS)
      else setError(WRONG_CREDENTIALS.includes(message) ? copy.wrongCredentials : message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="gate">
      <form className="gate-card" onSubmit={submit}>
        <h1>{copy.title}</h1>
        <p className="sub">{copy.description}</p>
        {role === 'patient' ? (
          <>
            <label htmlFor="login-name">Hasta numarası</label>
            <input
              id="login-name"
              type="text"
              inputMode="decimal"
              autoComplete="username"
              maxLength={20}
              value={login}
              // Patient numbers are digits; a few dataset numbers also contain a dot
              onChange={(event) => setLogin(event.target.value.replace(/[^\d.]/g, ''))}
              required
            />
          </>
        ) : (
          <>
            <label htmlFor="login-name">Kullanıcı adı</label>
            <input
              id="login-name"
              type="text"
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              value={login}
              onChange={(event) => setLogin(event.target.value)}
              required
            />
          </>
        )}
        <label htmlFor="login-password">Şifre</label>
        <input
          id="login-password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />
        {error && (
          <p className="gate-error" role="alert">
            {error}
          </p>
        )}
        <div className="gate-row">
          <Link to={PATHS.home} className="btn ghost">
            Geri
          </Link>
          <button type="submit" className="btn" disabled={busy}>
            {busy ? 'Giriş yapılıyor…' : 'Giriş'}
          </button>
        </div>
      </form>
    </main>
  )
}
