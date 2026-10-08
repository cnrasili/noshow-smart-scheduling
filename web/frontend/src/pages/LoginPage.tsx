import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { ApiError, api, errorText } from '../api'
import { isValidNationalId } from '../nationalId'
import { PATHS, loginFor } from '../routes'
import { usePageTitle } from '../site/title'
import type { LoginCredentials, Me, Role } from '../types'

// Backend answers for wrong credentials; both are shown with the form's own message
const WRONG_CREDENTIALS = ['Wrong national ID number or password', 'Wrong email or password']
// Shown when the backend refuses logins after too many failures (429)
const TOO_MANY_ATTEMPTS =
  'Çok fazla başarısız giriş denemesi yapıldı. Lütfen 15 dakika sonra tekrar deneyin.'

const COPY: Record<
  Role,
  { title: string; description: string; other: string; wrongCredentials: string }
> = {
  patient: {
    title: 'Hasta girişi',
    description: 'Randevu almak ve randevularınızı görmek için giriş yapın.',
    other: 'Hekim misiniz? Hekim girişi',
    wrongCredentials: 'T.C. kimlik numarası veya şifre hatalı.',
  },
  doctor: {
    title: 'Hekim girişi',
    description: 'Günlük hasta listenize ve çalışma takviminize ulaşmak için giriş yapın.',
    other: 'Hasta mısınız? Hasta girişi',
    wrongCredentials: 'E-posta adresi veya şifre hatalı.',
  },
}

export function LoginPage({ role, onSignedIn }: { role: Role; onSignedIn: (me: Me) => void }) {
  // National ID number on the patient form, e-mail address on the doctor form
  const [login, setLogin] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const copy = COPY[role]
  usePageTitle(copy.title)

  async function submit(event: FormEvent) {
    event.preventDefault()
    const name = login.trim()
    if (role === 'patient' && !isValidNationalId(name)) {
      setError('Geçerli bir T.C. kimlik numarası girin (11 hane).')
      return
    }
    const credentials: LoginCredentials =
      role === 'patient' ? { role, national_id: name, password } : { role, email: name, password }
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
              T.C. kimlik numarası
              <input
                type="text"
                inputMode="numeric"
                autoComplete="username"
                maxLength={11}
                value={login}
                onChange={(event) => setLogin(event.target.value.replace(/\D/g, ''))}
                required
              />
            </label>
          ) : (
            <label>
              E-posta adresi
              <input
                type="email"
                autoComplete="username"
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
          <Link to={loginFor(role === 'patient' ? 'doctor' : 'patient')}>{copy.other}</Link>
        </div>
      </form>
    </div>
  )
}
