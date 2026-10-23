import type { ReactElement } from 'react'
import { JobForm } from './components/JobForm'
import { JobList } from './components/JobList'
import { useJobs } from './hooks/useJobs'

/** How often the job list is reloaded (DESIGN.md ### LiveIndicator: 'alle 3 s'). */
const POLL_INTERVAL_MS = 3000

/** The single screen, DESIGN.md ### Home (/). */
export function App(): ReactElement {
  const { jobs, error, loading, refresh } = useJobs(POLL_INTERVAL_MS)
  const showCount = !loading || jobs.length > 0

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header__titles">
          <h1 className="app-header__title">Textanalyse-Aufträge</h1>
          <p className="app-header__subtitle">
            Aufträge anlegen, der Worker verarbeitet sie im Hintergrund.
          </p>
        </div>
        <LiveIndicator connected={error === null} />
      </header>

      <main className="app-layout">
        <section className="app-layout__form card" aria-labelledby="job-form-title">
          <h2 id="job-form-title" className="card__title">
            Neuer Auftrag
          </h2>
          <JobForm onCreated={refresh} />
        </section>

        <section className="app-layout__list card" aria-labelledby="job-list-title">
          <div className="card__header">
            <h2 id="job-list-title" className="card__title">
              Aufträge
            </h2>
            {showCount && (
              <span className="count-badge" data-testid="job-count">
                <span className="visually-hidden">Anzahl: </span>
                {jobs.length.toLocaleString('de-DE')}
              </span>
            )}
            <span className="card__meta">Neueste zuerst</span>
          </div>
          <JobList jobs={jobs} loading={loading} error={error} />
        </section>
      </main>
    </div>
  )
}

/** DESIGN.md ### LiveIndicator: informational only, never interactive. */
function LiveIndicator({ connected }: { connected: boolean }): ReactElement {
  return (
    <p className="live-indicator" data-state={connected ? 'live' : 'error'} role="status">
      <span className="live-indicator__dot" aria-hidden="true" />
      {connected
        ? `Aktualisiert automatisch alle ${POLL_INTERVAL_MS / 1000} s`
        : 'Verbindung unterbrochen'}
    </p>
  )
}
