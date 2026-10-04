import { Link } from 'react-router'
import { INSTITUTION_NAME, SYSTEM_NAME } from '../config'
import { PATHS } from '../routes'

const BOOKING_STEPS = [
  'Hasta girişi ile sisteme girin.',
  'Branşı ve hekimi seçin.',
  'Uygun günü ve saati seçip randevuyu onaylayın.',
  'Randevu numaranızı not alın; randevularınızı "Randevularım" sayfasından izleyin.',
]

export function HomePage() {
  return (
    <div className="public-page">
      <header className="topbar">
        <div className="container topbar-inner">
          <Link to={PATHS.home} className="brand">
            <span className="brand-name">{INSTITUTION_NAME}</span>
            <span className="brand-system">{SYSTEM_NAME}</span>
          </Link>
          <div className="actions">
            <Link to={PATHS.doctorLogin} className="button">
              Hekim girişi
            </Link>
            <Link to={PATHS.patientLogin} className="button primary">
              Hasta girişi
            </Link>
          </div>
        </div>
      </header>

      <main className="container main home">
        <section className="intro">
          <h1>Poliklinik randevu sistemi</h1>
          <p>
            {INSTITUTION_NAME} randevularınızı çevrimiçi alabilir, randevularınızı takip edebilir ve
            gelemeyeceğiniz randevuları iptal edebilirsiniz. Hekimler günlük hasta listelerini ve
            geliş kayıtlarını bu sistemden yönetir.
          </p>
          <div className="actions">
            <Link to={PATHS.patientLogin} className="button primary">
              Hasta girişi
            </Link>
            <Link to={PATHS.doctorLogin} className="button">
              Hekim girişi
            </Link>
          </div>
        </section>

        <section className="columns services" aria-label="Hizmetler">
          <article className="panel panel-body">
            <h2>Randevu alma</h2>
            <p className="muted">
              Branş ve hekim seçerek uygun gün ve saatlerden randevu alın. Dolu bir saatte yer
              açılabiliyorsa ek randevu talep edebilirsiniz.
            </p>
          </article>
          <article className="panel panel-body">
            <h2>Randevu takibi</h2>
            <p className="muted">
              Aktif ve geçmiş randevularınızı randevu numarası, hekim, tarih ve durumuyla görün.
            </p>
          </article>
          <article className="panel panel-body">
            <h2>Hekim hasta listesi</h2>
            <p className="muted">
              Hekimler günlük hasta listesini görür, hastanın gelip gelmediğini kaydeder ve randevu
              saatlerini açar.
            </p>
          </article>
        </section>

        <section className="panel">
          <div className="panel-head">
            <h2>Hastalar için bilgiler</h2>
          </div>
          <div className="panel-body info-grid">
            <div>
              <h3>Randevu nasıl alınır?</h3>
              <ol className="steps">
                {BOOKING_STEPS.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
            </div>
            <div>
              <h3>E-posta bildirimleri</h3>
              <p className="muted">
                Randevunuz alındığında kayıtlı e-posta adresinize onay e-postası gönderilir.
                Randevunuzdan önce hatırlatma e-postası da gönderilebilir.
              </p>
            </div>
            <div>
              <h3>Gelemeyecekseniz</h3>
              <p className="muted">
                Randevunuza gelemeyecekseniz lütfen "Randevularım" sayfasından iptal edin. Boşalan
                saat başka bir hastaya verilebilir; böylece bekleme süreleri kısalır.
              </p>
            </div>
          </div>
        </section>
      </main>

      <footer className="public-footer">
        Demo ortamı. Sistemdeki hasta ve hekim kayıtları gerçek kişilere ait değildir.
      </footer>
    </div>
  )
}
