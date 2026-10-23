import { render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Job } from './api'
import { App } from './App'
import { JobForm } from './components/JobForm'
import { JobList } from './components/JobList'
import { type UseJobsResult, useJobs } from './hooks/useJobs'

// The hook's data is controlled here; the components render for real and are only
// observed, so this file asserts the shell and its wiring, not the components' bodies.
vi.mock('./hooks/useJobs', () => ({ useJobs: vi.fn() }))
vi.mock('./components/JobForm', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./components/JobForm')>()
  return { JobForm: vi.fn(actual.JobForm) }
})
vi.mock('./components/JobList', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./components/JobList')>()
  return { JobList: vi.fn(actual.JobList) }
})

function job(id: number): Job {
  return {
    id,
    text: `Text ${id}`,
    analysis: 'word_count',
    status: 'pending',
    result: null,
    error: null,
    created_at: '2026-10-23T10:00:00Z',
    updated_at: '2026-10-23T10:00:00Z',
  }
}

function hookState(overrides: Partial<UseJobsResult> = {}): UseJobsResult {
  return {
    jobs: [],
    error: null,
    loading: false,
    refresh: vi.fn(() => Promise.resolve()),
    ...overrides,
  }
}

beforeEach(() => {
  vi.mocked(useJobs).mockReset()
  vi.mocked(JobForm).mockClear()
  vi.mocked(JobList).mockClear()
})

describe('App shell', () => {
  it('renders the page heading, subtitle and the form and list areas', () => {
    vi.mocked(useJobs).mockReturnValue(hookState())
    render(<App />)

    expect(
      screen.getByRole('heading', { level: 1, name: 'Textanalyse-Aufträge' }),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Aufträge anlegen, der Worker verarbeitet sie im Hintergrund.'),
    ).toBeInTheDocument()
    expect(screen.getByRole('main')).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Neuer Auftrag' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Aufträge' })).toBeInTheDocument()
  })

  it('polls every 3 seconds and says so in the live indicator', () => {
    vi.mocked(useJobs).mockReturnValue(hookState())
    render(<App />)

    expect(useJobs).toHaveBeenCalledWith(3000)
    expect(screen.getByRole('status')).toHaveTextContent('Aktualisiert automatisch alle 3 s')
  })

  it('shows the interrupted connection in the live indicator while the API fails', () => {
    vi.mocked(useJobs).mockReturnValue(
      hookState({ jobs: [job(1)], error: 'Die API ist nicht erreichbar.' }),
    )
    render(<App />)

    const indicator = screen.getByRole('status')
    expect(indicator).toHaveTextContent('Verbindung unterbrochen')
    expect(indicator).toHaveAttribute('data-state', 'error')
  })

  it('shows how many jobs the list holds', () => {
    vi.mocked(useJobs).mockReturnValue(hookState({ jobs: [job(2), job(1)] }))
    render(<App />)

    const listArea = screen.getByRole('region', { name: 'Aufträge' })
    expect(within(listArea).getByTestId('job-count')).toHaveTextContent('2')
  })

  it('hands refresh to the form and the hook state to the list', () => {
    const state = hookState({ jobs: [job(1)], loading: false, error: null })
    vi.mocked(useJobs).mockReturnValue(state)
    render(<App />)

    const formProps = vi.mocked(JobForm).mock.lastCall?.[0]
    expect(formProps?.onCreated).toBe(state.refresh)

    const listProps = vi.mocked(JobList).mock.lastCall?.[0]
    expect(listProps).toEqual({ jobs: state.jobs, loading: false, error: null })
  })
})
