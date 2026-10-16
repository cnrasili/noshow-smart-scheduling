import { useCallback, useEffect, useState } from 'react'
import { api, errorText } from '../../api'
import {
  appointmentNumber,
  branchLabel,
  formatShortDate,
  formatTimeRange,
  hasStarted,
} from '../../format'
import type { Appointment } from '../../types'
import { Notice, PageHeader, Status, type NoticeState } from '../../ui'

type Tab = 'active' | 'past'

function PastStatus({ attended }: { attended: boolean | null }) {
  if (attended === true) return <Status tone="ok">Geldi</Status>
  if (attended === false) return <Status tone="miss">Gelmedi</Status>
  return <Status tone="neutral">Kayıt bekleniyor</Status>
}

export function AppointmentsPage({ onBook }: { onBook: () => void }) {
  const [appointments, setAppointments] = useState<Appointment[] | null>(null)
  const [tab, setTab] = useState<Tab>('active')
  const [confirmId, setConfirmId] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState<NoticeState | null>(null)

  const closeNotice = useCallback(() => setNotice(null), [])
  const showError = (error: unknown) => setNotice({ kind: 'error', text: errorText(error) })

  useEffect(() => {
    api.myAppointments().then(setAppointments).catch(showError)
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

  const active = (appointments ?? []).filter((a) => !hasStarted(a.start_at))
  const past = (appointments ?? []).filter((a) => hasStarted(a.start_at)).reverse()
  const rows = tab === 'active' ? active : past

  return (
    <>
      <Notice notice={notice} onClose={closeNotice} />
      <PageHeader title="Randevularım" description="Aktif ve geçmiş randevularınız.">
        <button type="button" className="primary" onClick={onBook}>
          Yeni randevu al
        </button>
      </PageHeader>

      <section className="panel">
        <div className="tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'active'}
            className={tab === 'active' ? 'is-active' : ''}
            onClick={() => setTab('active')}
          >
            Aktif <span className="count">{active.length}</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'past'}
            className={tab === 'past' ? 'is-active' : ''}
            onClick={() => setTab('past')}
          >
            Geçmiş <span className="count">{past.length}</span>
          </button>
        </div>

        {appointments === null ? (
          <p className="muted panel-body">Yükleniyor…</p>
        ) : rows.length === 0 ? (
          <p className="muted panel-body">
            {tab === 'active' ? 'Aktif randevunuz bulunmuyor.' : 'Geçmiş randevunuz bulunmuyor.'}
          </p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Randevu no</th>
                <th>Tarih</th>
                <th>Saat</th>
                <th>Branş</th>
                <th>Hekim</th>
                <th>Durum</th>
                {tab === 'active' && <th className="cell-actions">İşlem</th>}
              </tr>
            </thead>
            <tbody>
              {rows.map((appointment) => (
                <tr key={appointment.id}>
                  <td data-label="Randevu no" className="mono">
                    {appointmentNumber(appointment.id)}
                  </td>
                  <td data-label="Tarih">{formatShortDate(appointment.appointment_date)}</td>
                  <td data-label="Saat" className="mono">
                    {formatTimeRange(appointment.start_at, appointment.end_at)}
                  </td>
                  <td data-label="Branş">{branchLabel(appointment.doctor_specialty)}</td>
                  <td data-label="Hekim">{appointment.doctor_name}</td>
                  <td data-label="Durum">
                    {tab === 'active' ? (
                      <Status tone="info">Aktif</Status>
                    ) : (
                      <PastStatus attended={appointment.attended} />
                    )}
                  </td>
                  {tab === 'active' && (
                    <td data-label="İşlem" className="cell-actions">
                      {confirmId === appointment.id ? (
                        <div className="actions">
                          <span className="muted">İptal edilsin mi?</span>
                          <button
                            type="button"
                            className="small"
                            onClick={() => setConfirmId(null)}
                            disabled={busy}
                          >
                            Vazgeç
                          </button>
                          <button
                            type="button"
                            className="small danger"
                            onClick={() => cancel(appointment)}
                            disabled={busy}
                          >
                            Evet, iptal et
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          className="small"
                          onClick={() => setConfirmId(appointment.id)}
                          disabled={busy}
                        >
                          İptal et
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </>
  )
}
