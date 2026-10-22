import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router'
import { api, errorText } from '../../api'
import {
  appointmentNumber,
  formatDateTime,
  formatLongDate,
  formatTime,
  hasStarted,
} from '../../format'
import { PATHS } from '../../routes'
import type { Appointment, SmsMessage } from '../../types'
import { Notice, PageTop, type NoticeState } from '../../ui'
import { PatientWho } from './PatientWho'

const SMS_KIND: Record<SmsMessage['kind'], string> = {
  confirmation: 'Randevu onayı',
  reminder: 'Randevu hatırlatması',
}

function SmsList({ messages }: { messages: SmsMessage[] | null }) {
  if (messages === null) return <p className="muted">Yükleniyor…</p>
  if (messages.length === 0) return <p className="muted">SMS yok.</p>
  return (
    <ul className="sms-list">
      {messages.map((message) => (
        <li key={`${message.kind}-${message.sent_at}`}>
          <b>SMS · {SMS_KIND[message.kind]}</b>{' '}
          <time dateTime={message.sent_at} className="muted">
            {formatDateTime(message.sent_at)}
          </time>
          <p>“{message.body}”</p>
        </li>
      ))}
    </ul>
  )
}

export function AppointmentsPage() {
  const [appointments, setAppointments] = useState<Appointment[] | null>(null)
  const [messages, setMessages] = useState<SmsMessage[] | null>(null)
  const [confirmId, setConfirmId] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState<NoticeState | null>(null)
  const closeNotice = useCallback(() => setNotice(null), [])
  const showError = (error: unknown) => setNotice({ kind: 'error', text: errorText(error) })

  useEffect(() => {
    api.myAppointments().then(setAppointments).catch(showError)
    api.myMessages().then(setMessages).catch(showError)
  }, [])

  async function cancel(appointment: Appointment) {
    setBusy(true)
    setConfirmId(null)
    try {
      await api.cancel(appointment.id)
      setNotice({
        kind: 'success',
        text: `${appointmentNumber(appointment.id)} numaralı randevunuz iptal edildi.`,
      })
      setAppointments(await api.myAppointments())
    } catch (error) {
      showError(error)
    } finally {
      setBusy(false)
    }
  }

  const upcoming = (appointments ?? []).filter((a) => !hasStarted(a.start_at))

  return (
    <>
      <main className="main">
        <Notice notice={notice} onClose={closeNotice} />
        <PageTop title="Randevularım" description="Alınan randevular ve SMS mesajları" />
        <section className="card" aria-labelledby="appointments-title">
          <h2 id="appointments-title">Randevular</h2>
          {appointments === null ? (
            <p className="muted">Yükleniyor…</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Tarih</th>
                  <th>Saat</th>
                  <th>Randevu no</th>
                  <th className="r">
                    <span className="visually-hidden">İşlem</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {upcoming.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="muted">
                      Aktif randevunuz yok.
                    </td>
                  </tr>
                ) : (
                  upcoming.map((appointment) => (
                    <tr key={appointment.id}>
                      <td>{formatLongDate(appointment.appointment_date)}</td>
                      <td>
                        <b>{formatTime(appointment.start_at)}</b>
                      </td>
                      <td>{appointmentNumber(appointment.id)}</td>
                      <td className="r">
                        {confirmId === appointment.id ? (
                          <span className="actions">
                            <span className="muted">İptal edilsin mi?</span>{' '}
                            <button
                              type="button"
                              className="btn small ghost"
                              onClick={() => setConfirmId(null)}
                              disabled={busy}
                            >
                              Vazgeç
                            </button>{' '}
                            <button
                              type="button"
                              className="btn small danger"
                              onClick={() => cancel(appointment)}
                              disabled={busy}
                            >
                              Evet, iptal et
                            </button>
                          </span>
                        ) : (
                          <button
                            type="button"
                            className="btn small ghost"
                            onClick={() => setConfirmId(appointment.id)}
                            disabled={busy}
                          >
                            İptal
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
          <p className="note">
            Gelemeyecekseniz lütfen iptal edin: boşalan saat başka bir hastaya verilebilir.
          </p>
        </section>
        <section className="card" aria-labelledby="sms-title">
          <h2 id="sms-title">SMS mesajları</h2>
          <SmsList messages={messages} />
        </section>
      </main>
      <aside className="side" aria-label="Hesap">
        <PatientWho />
        <h2>Yeni randevu</h2>
        <p className="muted">Haftalık takvimden müsait bir saat seçerek randevu alabilirsiniz.</p>
        <p className="gate-row">
          <Link to={PATHS.booking} className="btn">
            Randevu al
          </Link>
        </p>
      </aside>
    </>
  )
}
