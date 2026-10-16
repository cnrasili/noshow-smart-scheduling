import { CONTACT } from '../../content/site'
import { PageHeader } from '../../ui'

export function ContactPage() {
  return (
    <>
      <PageHeader title="İletişim ve Ulaşım" />
      <div className="guide-grid">
        <section className="panel panel-body" aria-labelledby="contact-title">
          <h2 id="contact-title">İletişim</h2>
          <address className="stack-tight">
            <span>{CONTACT.address}</span>
            <span>Telefon: {CONTACT.phone}</span>
            <span>
              E-posta: <a href={`mailto:${CONTACT.email}`}>{CONTACT.email}</a>
            </span>
            <span>
              Randevu soruları:{' '}
              <a href={`mailto:${CONTACT.appointmentEmail}`}>{CONTACT.appointmentEmail}</a>
            </span>
          </address>
        </section>
        <section className="panel panel-body" aria-labelledby="hours-title">
          <h2 id="hours-title">Çalışma saatleri</h2>
          <dl className="facts">
            {CONTACT.hours.map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        </section>
        <section id="ulasim" className="panel panel-body" aria-labelledby="transport-title">
          <h2 id="transport-title">Nasıl giderim?</h2>
          <dl className="facts">
            {CONTACT.transport.map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        </section>
      </div>
    </>
  )
}
