import type { ReactElement } from 'react'
import type { Job, JobStatus } from '../api'

export type JobListProps = {
  jobs: Job[]
  loading: boolean
  error: string | null
}

const STATUS_LABELS: Record<JobStatus, string> = {
  pending: 'wartend',
  running: 'in Arbeit',
  done: 'fertig',
  failed: 'fehlgeschlagen',
}

const ANALYSIS_LABELS: Record<string, string> = {
  word_count: 'Wörter zählen',
  top_words: 'Häufigste Wörter',
  reading_time: 'Lesezeit schätzen',
}

const PREVIEW_LENGTH = 120
const NUMBER_FORMAT = new Intl.NumberFormat('de-DE')

export const ERROR_NOTICE_TEXT = 'Die API ist nicht erreichbar. Neuer Versuch in wenigen Sekunden.'

/** Text preview: at most 120 characters, then '…' (DESIGN.md ### JobItem). */
export function previewText(text: string): string {
  const chars = Array.from(text)
  return chars.length > PREVIEW_LENGTH ? `${chars.slice(0, PREVIEW_LENGTH).join('')}…` : text
}

/** 'TT.MM.JJJJ, HH:mm:ss' in local time; the raw value when it does not parse. */
export function formatTimestamp(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) {
    return iso
  }
  const pad = (n: number): string => String(n).padStart(2, '0')
  return (
    `${pad(date.getDate())}.${pad(date.getMonth() + 1)}.${date.getFullYear()}, ` +
    `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
  )
}

type WordCount = { word: string; count: number }

/** The top_words result as entries, or null when the string has another shape. */
export function parseTopWords(result: string): WordCount[] | null {
  let parsed: unknown
  try {
    parsed = JSON.parse(result)
  } catch {
    return null
  }
  if (!Array.isArray(parsed)) {
    return null
  }
  const entries: WordCount[] = []
  for (const item of parsed) {
    if (
      typeof item !== 'object' ||
      item === null ||
      typeof (item as WordCount).word !== 'string' ||
      typeof (item as WordCount).count !== 'number'
    ) {
      return null
    }
    entries.push({ word: (item as WordCount).word, count: (item as WordCount).count })
  }
  return entries
}

function isInteger(value: string): boolean {
  return /^\d+$/.test(value.trim())
}

function StatusBadge({ status }: { status: JobStatus }): ReactElement {
  return (
    <span className="status-badge" data-status={status}>
      {STATUS_LABELS[status] ?? status}
    </span>
  )
}

function DoneResult({ job, result }: { job: Job; result: string }): ReactElement {
  if (job.analysis === 'top_words') {
    const words = parseTopWords(result)
    if (words !== null) {
      if (words.length === 0) {
        return <span>Keine Wörter gefunden</span>
      }
      return (
        <ul className="result-block__chips" aria-label="Häufigste Wörter">
          {words.map((entry, index) => (
            <li className="word-chip job-content" key={`${index}-${entry.word}`}>
              {`${entry.word} × ${NUMBER_FORMAT.format(entry.count)}`}
            </li>
          ))}
        </ul>
      )
    }
  } else if (job.analysis === 'word_count' && isInteger(result)) {
    const n = Number(result.trim())
    return <span>{`${NUMBER_FORMAT.format(n)} ${n === 1 ? 'Wort' : 'Wörter'}`}</span>
  } else if (job.analysis === 'reading_time' && isInteger(result)) {
    return <span>{`${NUMBER_FORMAT.format(Number(result.trim()))} Min. Lesezeit`}</span>
  }
  return <span className="job-content">{result}</span>
}

function ResultBlock({ job }: { job: Job }): ReactElement {
  if (job.status === 'done') {
    return (
      <div className="result-block" data-variant="done">
        <DoneResult job={job} result={job.result ?? ''} />
      </div>
    )
  }
  if (job.status === 'failed') {
    return (
      <div className="result-block job-content" data-variant="failed">
        {`Fehler: ${job.error ?? 'Unbekannter Fehler'}`}
      </div>
    )
  }
  return (
    <div className="result-block" data-variant="waiting">
      Ergebnis folgt …
    </div>
  )
}

function JobItem({ job }: { job: Job }): ReactElement {
  return (
    <li className="job-item" data-testid="job-item">
      <div className="job-item__top">
        <span className="job-item__id mono">{`#${job.id}`}</span>
        <span className="analysis-chip">{ANALYSIS_LABELS[job.analysis] ?? job.analysis}</span>
        <span className="job-item__status">
          <StatusBadge status={job.status} />
        </span>
        <time className="job-item__time mono" dateTime={job.created_at}>
          {formatTimestamp(job.created_at)}
        </time>
      </div>
      <p className="job-item__preview job-content">
        {previewText(job.text)}
      </p>
      <ResultBlock job={job} />
    </li>
  )
}

function ErrorNotice(): ReactElement {
  return (
    <div className="error-notice" role="alert">
      <svg
        className="error-notice__icon"
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="7" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12" y2="17" />
      </svg>
      <span>{ERROR_NOTICE_TEXT}</span>
    </div>
  )
}

function EmptyState(): ReactElement {
  return (
    <div className="empty-state">
      <svg
        className="empty-state__icon"
        width="40"
        height="40"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        aria-hidden="true"
      >
        <rect x="4" y="3" width="16" height="18" rx="2" />
        <line x1="8" y1="8" x2="16" y2="8" />
        <line x1="8" y1="12" x2="16" y2="12" />
        <line x1="8" y1="16" x2="12" y2="16" />
      </svg>
      <p className="empty-state__title">Noch keine Aufträge</p>
      <p className="empty-state__hint">
        Erstelle links deinen ersten Auftrag, das Ergebnis erscheint hier automatisch.
      </p>
    </div>
  )
}

function SkeletonRows(): ReactElement {
  return (
    <div aria-busy="true" aria-label="Aufträge werden geladen">
      {[0, 1, 2].map((i) => (
        <div className="skeleton-row" key={i}>
          <div className="skeleton-bar" />
          <div className="skeleton-bar" />
          <div className="skeleton-bar" />
        </div>
      ))}
    </div>
  )
}

/**
 * The body of the 'Aufträge' card: ErrorNotice, SkeletonRows on the first load,
 * EmptyState or the JobItem rows (DESIGN.md ### Home (/)). Job content is rendered only
 * as React text nodes.
 */
export function JobList({ jobs, loading, error }: JobListProps): ReactElement {
  let body: ReactElement | null
  if (jobs.length > 0) {
    body = (
      <ul className="job-list">
        {jobs.map((job) => (
          <JobItem job={job} key={job.id} />
        ))}
      </ul>
    )
  } else if (loading) {
    body = <SkeletonRows />
  } else {
    body = <EmptyState />
  }
  return (
    <>
      {error !== null && <ErrorNotice />}
      {body}
    </>
  )
}
