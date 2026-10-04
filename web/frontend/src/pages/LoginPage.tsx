import { useState, type FormEvent } from 'react'
import { api, errorText } from '../api'
import { INSTITUTION_NAME, SYSTEM_NAME } from '../config'
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
      const message = errorText(err)
      setError(
        message === 'Wrong email or password' ? 'E-posta adresi veya şifre hatalı.' : message,
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-page">
      <header className="login-header">
        <div className="brand">
          <span className="brand-name">{INSTITUTION_NAME}</span>
          <span className="brand-system">{SYSTEM_NAME}</span>
        </div>
      </header>

      <main className="login-main">
        <div className="login-box">
          <section className="login-info">
            <h1>Poliklinik randevu işlemleri</h1>
            <dl>
              <div>
                <dt>Hastalar</dt>
                <dd>Branş ve hekim seçerek randevu alma, randevuları görüntüleme ve iptal etme</dd>
              </div>
              <div>
                <dt>Hekimler</dt>
                <dd>Günlük hasta listesi, geliş kaydı ve çalışma takvimi</dd>
              </div>
            </dl>
          </section>

          <form className="login-form" onSubmit={submit}>
            <h2>Kullanıcı girişi</h2>
            <label>
              E-posta adresi
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
            <button type="submit" className="primary block" disabled={busy}>
              {busy ? 'Giriş yapılıyor…' : 'Giriş yap'}
            </button>
          </form>
        </div>
      </main>

      <footer className="login-footer">
        Demo ortamı. Sistemdeki hasta ve hekim kayıtları gerçek kişilere ait değildir.
      </footer>
    </div>
  )
}
