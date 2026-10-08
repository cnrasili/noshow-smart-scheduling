import { ABOUT } from '../../content/site'
import { PageHeader } from '../../ui'

export function AboutPage() {
  return (
    <>
      <PageHeader title="Hastanemiz" />
      <section className="panel panel-body prose">
        <p>{ABOUT.intro}</p>
        {ABOUT.sections.map((section) => (
          <div key={section.title}>
            <h2>{section.title}</h2>
            <p>{section.text}</p>
          </div>
        ))}
      </section>
    </>
  )
}
