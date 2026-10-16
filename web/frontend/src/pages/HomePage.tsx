import { Link } from 'react-router'
import { INSTITUTION_NAME } from '../config'
import { ABOUT, ANNOUNCEMENTS } from '../content/site'
import { formatLongDate } from '../format'
import { PATHS, announcementPath } from '../routes'
import { usePageTitle } from '../site/title'

const QUICK_ACTIONS = [
  {
    to: PATHS.booking,
    title: 'Online Randevu',
    text: 'Branş, hekim, gün ve saat seçerek randevunuzu alın.',
  },
  {
    to: `${PATHS.contact}#ulasim`,
    title: 'Nasıl Giderim?',
    text: 'Adres, toplu taşıma ve otopark bilgileri.',
  },
  {
    to: PATHS.workingList,
    title: 'Hekim Çalışma Listesi',
    text: 'Hekimlerimizin haftalık poliklinik çalışma saatleri.',
  },
  {
    to: PATHS.guide,
    title: 'Hasta Rehberi',
    text: 'Randevu öncesi ve muayene günü bilmeniz gerekenler.',
  },
]

const LATEST = 3

export function HomePage() {
  usePageTitle()
  return (
    <div className="home">
      <section className="hero" aria-labelledby="hero-title">
        <div className="hero-text">
          <h1 id="hero-title">{INSTITUTION_NAME}</h1>
          <p>
            Poliklinik randevularınızı Online Randevu ile alın, randevularınızı takip edin ve
            gelemeyeceğiniz randevuları iptal edin.
          </p>
        </div>
        <ul className="quick-actions">
          {QUICK_ACTIONS.map((action) => (
            <li key={action.title}>
              <Link to={action.to} className="quick-action">
                <span className="quick-action-title">{action.title}</span>
                <span className="quick-action-text">{action.text}</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <div className="home-columns">
        <section className="panel" aria-labelledby="latest-title">
          <div className="panel-head panel-head-row">
            <h2 id="latest-title">Duyurular</h2>
            <Link to={PATHS.announcements}>Tüm duyurular</Link>
          </div>
          <ul className="announcement-list">
            {ANNOUNCEMENTS.slice(0, LATEST).map((item) => (
              <li key={item.slug}>
                <time dateTime={item.date}>{formatLongDate(item.date)}</time>
                <Link to={announcementPath(item.slug)}>{item.title}</Link>
              </li>
            ))}
          </ul>
        </section>

        <section className="panel" aria-labelledby="about-title">
          <div className="panel-head">
            <h2 id="about-title">Hastanemiz</h2>
          </div>
          <div className="panel-body stack-tight">
            <p>{ABOUT.intro}</p>
            <Link to={PATHS.about}>Hastanemizi tanıyın</Link>
          </div>
        </section>
      </div>
    </div>
  )
}
