import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { ApiError, api, errorText } from '../api'
import { DEPARTMENT_NAME } from '../config'
import { PATHS, loginFor } from '../routes'
import { usePageTitle } from '../site/title'
import type { LoginCredentials, Me, Role } from '../types'

// Backend answers for wrong credentials; both are shown with the form's own message
const WRONG_CREDENTIALS = ['Wrong patient number or password', 'Wrong username or password']
// Shown when the backend refuses logins after too many failures (429)
const TOO_MANY_ATTEMPTS =
  'Çok fazla başarısız giriş denemesi yapıldı. Lütfen 15 dakika sonra tekrar deneyin.'

const COPY: Record<
  Role,
  { title: string; description: string; other: string; wrongCredentials: string }
> = {
  patient: {
    title: 'Hasta girişi',
    description: 'Hasta numaranız ve şifrenizle giriş yapın.',
    other: 'Departman girişi',
    wrongCredentials: 'Hasta numarası veya şifre hatalı.',
  },
  department: {
    title: 'Departman girişi',
    description: `${DEPARTMENT_NAME} departman paneli: günlük hasta listesi ve çalışma takvimi.`,
    other: 'Hasta mısınız? Hasta girişi',
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
    <div className="login-main">
      <form className="panel login-card" onSubmit={submit}>
        <div className="panel-head">
          <h1>{copy.title}</h1>
          <p className="muted">{copy.description}</p>
        </div>
        <div className="panel-body stack-tight">
          {role === 'patient' ? (
            <label>
              Hasta numarası
              <input
                type="text"
                inputMode="decimal"
                autoComplete="username"
                maxLength={20}
                value={login}
                // Patient numbers are digits; a few dataset numbers also contain a dot
                onChange={(event) => setLogin(event.target.value.replace(/[^\d.]/g, ''))}
                required
              />
            </label>
          ) : (
            <label>
              Kullanıcı adı
              <input
                type="text"
                autoComplete="username"
                autoCapitalize="none"
                spellCheck={false}
                value={login}
                onChange={(event) => setLogin(event.target.value)}
                required
              />
            </label>
          )}
          <label>
            Şifre
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <button type="submit" className="primary block" disabled={busy}>
            {busy ? 'Giriş yapılıyor…' : 'Giriş yap'}
          </button>
        </div>
        <div className="login-links">
          <Link to={PATHS.home}>‹ Anasayfa</Link>
          <Link to={loginFor(role === 'patient' ? 'department' : 'patient')}>{copy.other}</Link>
        </div>
      </form>
    </div>
  )
}
