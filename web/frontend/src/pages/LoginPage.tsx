import { useState, type FormEvent } from 'react'
import { api, errorText } from '../api'
import type { Me } from '../types'

export function LoginPage({ onSignedIn }: { onSignedIn: (me: Me) => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      onSignedIn(await api.login(email, password))
    } catch (err) {
      setError(
        errorText(err) === 'Wrong email or password' ? 'E-posta veya şifre hatalı' : errorText(err),
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="login">
      <form className="card login-card" onSubmit={submit}>
        <h1>Poliklinik Randevu Sistemi</h1>
        <p className="muted">Hasta veya doktor hesabınızla giriş yapın.</p>
        <label>
          E-posta
          <input
            type="email"
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </label>
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
        <button type="submit" className="primary" disabled={busy}>
          {busy ? 'Giriş yapılıyor…' : 'Giriş yap'}
        </button>
      </form>
    </main>
  )
}
