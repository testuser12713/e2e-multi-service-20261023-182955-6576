/**
 * Client for the jobs API (see the sprint's shared interface):
 *   GET  /jobs  -> 200 Job[] (newest first)
 *   POST /jobs  -> 201 Job, 422 FastAPI validation body
 * Every failure (unreachable API, 4xx, 5xx, unreadable body) is raised as an ApiError
 * whose message is German and safe to show to the user.
 */

export type AnalysisKind = 'word_count' | 'top_words' | 'reading_time'

export type JobStatus = 'pending' | 'running' | 'done' | 'failed'

export type Job = {
  id: number
  text: string
  /** Normally an AnalysisKind; an unknown value from the database is passed through as-is. */
  analysis: string
  status: JobStatus
  result: string | null
  error: string | null
  /** ISO 8601, UTC. */
  created_at: string
  /** ISO 8601, UTC. */
  updated_at: string
}

/** Longest job text the API accepts, in characters. */
export const MAX_TEXT_LENGTH = 100_000

/** Port the API listens on in development when VITE_API_BASE_URL is not set. */
const FALLBACK_API_PORT = '8000'

const MESSAGE_UNREACHABLE = 'Die API ist nicht erreichbar.'
const MESSAGE_INVALID_RESPONSE = 'Die API hat eine unerwartete Antwort geschickt.'
const MESSAGE_SERVER_ERROR =
  'Die API hat einen internen Fehler gemeldet. Bitte versuche es später erneut.'
const MESSAGE_NOT_FOUND = 'Der Auftrag wurde nicht gefunden.'
const MESSAGE_TEXT_EMPTY = 'Der Text darf nicht leer sein.'
const MESSAGE_TEXT_TOO_LONG = 'Der Text darf höchstens 100.000 Zeichen lang sein.'
const MESSAGE_TEXT_INVALID = 'Der Text ist ungültig.'
const MESSAGE_ANALYSIS_INVALID = 'Bitte wähle eine gültige Analyse aus.'
const MESSAGE_INPUT_INVALID = 'Die Eingabe ist ungültig.'

export class ApiError extends Error {
  /** HTTP status of the response; 0 when the API could not be reached at all. */
  readonly status: number
  /** The `detail` field of the error body as the API sent it, or null. */
  readonly detail: unknown

  constructor(message: string, status: number, detail: unknown = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }

  /** True when no HTTP response arrived (API down, wrong address, network gone). */
  get isNetworkError(): boolean {
    return this.status === 0
  }
}

/**
 * Base address of the API without a trailing slash: VITE_API_BASE_URL when it holds an
 * absolute http(s) address, otherwise the API's development port on the host this page
 * was loaded from.
 */
export function apiBaseUrl(): string {
  const configured: unknown = import.meta.env.VITE_API_BASE_URL
  if (typeof configured === 'string' && isHttpUrl(configured.trim())) {
    return configured.trim().replace(/\/+$/, '')
  }
  const { protocol, hostname } = window.location
  return `${protocol}//${hostname}:${FALLBACK_API_PORT}`
}

function isHttpUrl(value: string): boolean {
  if (value === '') {
    return false
  }
  try {
    const { protocol } = new URL(value)
    return protocol === 'http:' || protocol === 'https:'
  } catch {
    return false
  }
}

/** All jobs, newest first, as the API orders them. */
export async function listJobs(): Promise<Job[]> {
  const { status, ok, body } = await send('/jobs', 'GET')
  if (!ok) {
    throw errorForStatus(status, body)
  }
  if (!Array.isArray(body) || !body.every(isJob)) {
    throw new ApiError(MESSAGE_INVALID_RESPONSE, status)
  }
  return body
}

/** Creates a job; it starts as `pending` and the worker picks it up. */
export async function createJob(text: string, analysis: AnalysisKind): Promise<Job> {
  const { status, ok, body } = await send('/jobs', 'POST', { text, analysis })
  if (status === 422) {
    throw new ApiError(validationMessage(text, body), status, detailOf(body))
  }
  if (status === 413) {
    throw new ApiError(MESSAGE_TEXT_TOO_LONG, status, detailOf(body))
  }
  if (!ok) {
    throw errorForStatus(status, body)
  }
  if (!isJob(body)) {
    throw new ApiError(MESSAGE_INVALID_RESPONSE, status)
  }
  return body
}

type SendResult = { status: number; ok: boolean; body: unknown }

async function send(path: string, method: 'GET' | 'POST', payload?: unknown): Promise<SendResult> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  const init: RequestInit = { method, headers }
  if (payload !== undefined) {
    headers['Content-Type'] = 'application/json'
    init.body = JSON.stringify(payload)
  }

  let response: Response
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, init)
  } catch {
    // fetch rejects only when no response arrived at all (or the browser blocked it).
    throw new ApiError(MESSAGE_UNREACHABLE, 0)
  }

  let raw = ''
  try {
    raw = await response.text()
  } catch {
    throw new ApiError(MESSAGE_UNREACHABLE, 0)
  }

  let body: unknown = null
  if (raw !== '') {
    try {
      body = JSON.parse(raw)
    } catch {
      if (response.ok) {
        throw new ApiError(MESSAGE_INVALID_RESPONSE, response.status)
      }
    }
  }
  return { status: response.status, ok: response.ok, body }
}

function errorForStatus(status: number, body: unknown): ApiError {
  if (status === 404) {
    return new ApiError(MESSAGE_NOT_FOUND, status, detailOf(body))
  }
  if (status >= 500) {
    return new ApiError(MESSAGE_SERVER_ERROR, status, detailOf(body))
  }
  return new ApiError(
    `Die API hat die Anfrage abgelehnt (Status ${status}).`,
    status,
    detailOf(body),
  )
}

function detailOf(body: unknown): unknown {
  if (typeof body === 'object' && body !== null && 'detail' in body) {
    return (body as { detail: unknown }).detail
  }
  return null
}

/** The fields a FastAPI validation body (detail[].loc) names, e.g. ["text"]. */
function invalidFields(body: unknown): Set<string> {
  const fields = new Set<string>()
  const detail = detailOf(body)
  if (!Array.isArray(detail)) {
    return fields
  }
  for (const entry of detail) {
    if (typeof entry !== 'object' || entry === null) {
      continue
    }
    const loc: unknown = (entry as { loc?: unknown }).loc
    if (Array.isArray(loc) && loc.length > 0) {
      const last: unknown = loc[loc.length - 1]
      if (typeof last === 'string') {
        fields.add(last)
      }
    }
  }
  return fields
}

/**
 * A German message for a 422. The wording of the API's own messages is not part of the
 * interface, so the message is derived from WHICH field was rejected and from the text
 * that was sent.
 */
function validationMessage(text: string, body: unknown): string {
  const fields = invalidFields(body)
  if (fields.has('text')) {
    const trimmed = text.trim()
    if (trimmed === '') {
      return MESSAGE_TEXT_EMPTY
    }
    if (Array.from(trimmed).length > MAX_TEXT_LENGTH || Array.from(text).length > MAX_TEXT_LENGTH) {
      return MESSAGE_TEXT_TOO_LONG
    }
    return MESSAGE_TEXT_INVALID
  }
  if (fields.has('analysis')) {
    return MESSAGE_ANALYSIS_INVALID
  }
  return MESSAGE_INPUT_INVALID
}

const JOB_STATUSES: readonly string[] = ['pending', 'running', 'done', 'failed']

function isJob(value: unknown): value is Job {
  if (typeof value !== 'object' || value === null) {
    return false
  }
  const job = value as Record<string, unknown>
  return (
    typeof job.id === 'number' &&
    typeof job.text === 'string' &&
    typeof job.analysis === 'string' &&
    typeof job.status === 'string' &&
    JOB_STATUSES.includes(job.status) &&
    (job.result === null || typeof job.result === 'string') &&
    (job.error === null || typeof job.error === 'string') &&
    typeof job.created_at === 'string' &&
    typeof job.updated_at === 'string'
  )
}
