import { Link, Navigate, useParams } from 'react-router'
import { ANNOUNCEMENTS } from '../../content/site'
import { formatLongDate } from '../../format'
import { PATHS, announcementPath } from '../../routes'
import { PageHeader } from '../../ui'

export function AnnouncementsPage() {
  return (
    <>
      <PageHeader title="Duyurular" />
      <section className="panel">
        <ul className="announcement-list">
          {ANNOUNCEMENTS.map((item) => (
            <li key={item.slug}>
              <time dateTime={item.date}>{formatLongDate(item.date)}</time>
              <Link to={announcementPath(item.slug)}>{item.title}</Link>
              <p className="muted">{item.summary}</p>
            </li>
          ))}
        </ul>
      </section>
    </>
  )
}

export function AnnouncementPage() {
  const { slug } = useParams()
  const item = ANNOUNCEMENTS.find((announcement) => announcement.slug === slug)
  // An unknown announcement address leads back to the list
  if (!item) return <Navigate to={PATHS.announcements} replace />
  return (
    <>
      <PageHeader title={item.title} description={formatLongDate(item.date)} />
      <article className="panel panel-body prose">
        {item.body.map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
        <Link to={PATHS.announcements}>‹ Tüm duyurular</Link>
      </article>
    </>
  )
}
