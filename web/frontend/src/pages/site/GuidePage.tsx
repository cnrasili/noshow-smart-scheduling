import { GUIDE } from '../../content/site'
import { PageHeader } from '../../ui'

export function GuidePage() {
  return (
    <>
      <PageHeader
        title="Hasta Rehberi"
        description="Randevu almadan önce ve muayene günü bilmeniz gerekenler"
      />
      <div className="guide-grid">
        {GUIDE.map((section) => (
          <section key={section.id} id={section.id} className="panel panel-body">
            <h2>{section.title}</h2>
            <ul className="steps">
              {section.steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </>
  )
}
