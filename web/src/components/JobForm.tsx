import { type FormEvent, type ReactElement, useId, useState } from 'react'
import { type AnalysisKind, ApiError, createJob, MAX_TEXT_LENGTH } from '../api'

export type JobFormProps = {
  /** Called after the API accepted a new job, so the list can refresh immediately. */
  onCreated: () => void
}

const ANALYSIS_OPTIONS: ReadonlyArray<{ value: AnalysisKind; label: string }> = [
  { value: 'word_count', label: 'Wörter zählen' },
  { value: 'top_words', label: 'Häufigste Wörter' },
  { value: 'reading_time', label: 'Lesezeit schätzen' },
]

const MESSAGE_EMPTY = 'Der Text darf nicht leer sein.'
const MESSAGE_TOO_LONG = 'Der Text darf höchstens 100.000 Zeichen lang sein.'
const MESSAGE_UNKNOWN = 'Der Auftrag konnte nicht erstellt werden.'

function lengthOf(text: string): number {
  return Array.from(text).length
}

/**
 * The fields of the 'Neuer Auftrag' card (DESIGN.md ### Home (/)): Textarea 'Text' with
 * character counter, Select 'Analyse', inline ErrorNotice and the 'Auftrag erstellen' button.
 */
export function JobForm({ onCreated }: JobFormProps): ReactElement {
  const id = useId()
  const [text, setText] = useState('')
  const [analysis, setAnalysis] = useState<AnalysisKind>('word_count')
  const [touched, setTouched] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [serverError, setServerError] = useState<string | null>(null)

  const length = lengthOf(text)
  const overLimit = length > MAX_TEXT_LENGTH
  const empty = text.trim() === ''
  const validationError = !touched ? null : empty ? MESSAGE_EMPTY : overLimit ? MESSAGE_TOO_LONG : null
  const disabled = empty || overLimit || submitting

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    setTouched(true)
    if (disabled) {
      return
    }
    setSubmitting(true)
    setServerError(null)
    try {
      await createJob(text, analysis)
      setText('')
      setTouched(false)
      onCreated()
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : MESSAGE_UNKNOWN)
    } finally {
      setSubmitting(false)
    }
  }

  const textId = `${id}-text`
  const errorId = `${id}-text-error`

  return (
    <form className="form-stack" onSubmit={handleSubmit} noValidate>
      <div className="field">
        <label className="field__label" htmlFor={textId}>
          Text
        </label>
        <textarea
          id={textId}
          className="field__textarea job-content"
          placeholder="Text zur Analyse einfügen …"
          value={text}
          aria-invalid={validationError !== null}
          aria-describedby={validationError !== null ? errorId : undefined}
          onChange={(e) => {
            setText(e.target.value)
            setTouched(true)
          }}
        />
        <div className="field__footer">
          {validationError !== null ? (
            <p id={errorId} className="field__error" role="alert">
              {validationError}
            </p>
          ) : (
            <span />
          )}
          <span className="field__counter mono" data-over-limit={overLimit}>
            {length.toLocaleString('de-DE')} / {MAX_TEXT_LENGTH.toLocaleString('de-DE')}
          </span>
        </div>
      </div>

      <div className="field">
        <label className="field__label" htmlFor={`${id}-analysis`}>
          Analyse
        </label>
        <select
          id={`${id}-analysis`}
          className="field__select"
          value={analysis}
          onChange={(e) => setAnalysis(e.target.value as AnalysisKind)}
        >
          {ANALYSIS_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {serverError !== null && (
        <div className="error-notice" role="alert">
          <svg className="error-notice__icon" viewBox="0 0 24 24" aria-hidden="true" fill="none">
            <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2" />
            <path d="M12 7v6M12 16.5v.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <span>{serverError}</span>
        </div>
      )}

      <button type="submit" className="button" disabled={disabled}>
        {submitting ? 'Wird gesendet…' : 'Auftrag erstellen'}
      </button>
    </form>
  )
}
