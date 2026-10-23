import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiBaseUrl, createJob, type Job, listJobs } from './api'

const sampleJob: Job = {
  id: 7,
  text: 'eins zwei drei',
  analysis: 'word_count',
  status: 'pending',
  result: null,
  error: null,
  created_at: '2026-10-23T10:00:00Z',
  updated_at: '2026-10-23T10:00:00Z',
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

const fetchMock = vi.fn<typeof fetch>()

beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
  vi.stubEnv('VITE_API_BASE_URL', 'http://api.test:9000/')
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
})

async function caught(promise: Promise<unknown>): Promise<ApiError> {
  try {
    await promise
  } catch (error) {
    expect(error).toBeInstanceOf(ApiError)
    return error as ApiError
  }
  throw new Error('expected the call to fail')
}

describe('apiBaseUrl', () => {
  it('uses VITE_API_BASE_URL without its trailing slash', () => {
    expect(apiBaseUrl()).toBe('http://api.test:9000')
  })

  it('falls back to the API dev port on the page host when the variable is unset', () => {
    vi.stubEnv('VITE_API_BASE_URL', '')
    expect(apiBaseUrl()).toBe(`${window.location.protocol}//${window.location.hostname}:8000`)
  })

  it('falls back when the variable holds no http address', () => {
    vi.stubEnv('VITE_API_BASE_URL', '${service:api.origin}')
    expect(apiBaseUrl()).toBe(`${window.location.protocol}//${window.location.hostname}:8000`)
  })
})

describe('listJobs', () => {
  it('GETs /jobs and returns the jobs', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, [sampleJob]))

    await expect(listJobs()).resolves.toEqual([sampleJob])
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('http://api.test:9000/jobs')
    expect(init?.method).toBe('GET')
  })

  it('raises a network ApiError when the API is unreachable', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

    const error = await caught(listJobs())
    expect(error.status).toBe(0)
    expect(error.isNetworkError).toBe(true)
    expect(error.message).toBe('Die API ist nicht erreichbar.')
  })

  it('raises an ApiError without server details on a 500', async () => {
    fetchMock.mockResolvedValue(jsonResponse(500, { detail: 'Internal Server Error' }))

    const error = await caught(listJobs())
    expect(error.status).toBe(500)
    expect(error.message).not.toContain('Internal Server Error')
  })

  it('rejects a body that is not a job list', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, { jobs: [] }))

    const error = await caught(listJobs())
    expect(error.status).toBe(200)
  })
})

describe('createJob', () => {
  it('POSTs text and analysis as JSON and returns the created job', async () => {
    fetchMock.mockResolvedValue(jsonResponse(201, sampleJob))

    await expect(createJob('eins zwei drei', 'word_count')).resolves.toEqual(sampleJob)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('http://api.test:9000/jobs')
    expect(init?.method).toBe('POST')
    expect(JSON.parse(String(init?.body))).toEqual({
      text: 'eins zwei drei',
      analysis: 'word_count',
    })
  })

  it('turns a 422 for an empty text into a German message and keeps the detail', async () => {
    const detail = [{ type: 'string_too_short', loc: ['body', 'text'], msg: 'too short' }]
    fetchMock.mockResolvedValue(jsonResponse(422, { detail }))

    const error = await caught(createJob('   ', 'word_count'))
    expect(error.status).toBe(422)
    expect(error.message).toBe('Der Text darf nicht leer sein.')
    expect(error.detail).toEqual(detail)
  })

  it('turns a 422 for an overlong text into the length message', async () => {
    const detail = [{ type: 'string_too_long', loc: ['body', 'text'], msg: 'too long' }]
    fetchMock.mockResolvedValue(jsonResponse(422, { detail }))

    const error = await caught(createJob('a'.repeat(100_001), 'word_count'))
    expect(error.message).toBe('Der Text darf höchstens 100.000 Zeichen lang sein.')
  })

  it('turns a 422 for the analysis into the analysis message', async () => {
    const detail = [{ type: 'literal_error', loc: ['body', 'analysis'], msg: 'bad' }]
    fetchMock.mockResolvedValue(jsonResponse(422, { detail }))

    const error = await caught(createJob('Hallo', 'word_count'))
    expect(error.message).toBe('Bitte wähle eine gültige Analyse aus.')
  })

  it('raises a network ApiError when the API is unreachable', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

    const error = await caught(createJob('Hallo', 'top_words'))
    expect(error.isNetworkError).toBe(true)
  })
})
