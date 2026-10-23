import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { Job } from '../api'
import { ERROR_NOTICE_TEXT, JobList } from './JobList'

function job(overrides: Partial<Job>): Job {
  return {
    id: 1,
    text: 'Hallo Welt',
    analysis: 'word_count',
    status: 'pending',
    result: null,
    error: null,
    created_at: '2026-10-23T12:00:00Z',
    updated_at: '2026-10-23T12:00:00Z',
    ...overrides,
  }
}

describe('JobList', () => {
  it('shows a German badge for all four statuses, in received order', () => {
    render(
      <JobList
        loading={false}
        error={null}
        jobs={[
          job({ id: 4, status: 'failed', error: 'Analyse fehlgeschlagen (KeyError)' }),
          job({ id: 3, status: 'done', result: '2' }),
          job({ id: 2, status: 'running' }),
          job({ id: 1, status: 'pending' }),
        ]}
      />,
    )
    const items = screen.getAllByTestId('job-item')
    expect(items.map((i) => within(i).getByText(/^#\d+$/).textContent)).toEqual([
      '#4',
      '#3',
      '#2',
      '#1',
    ])
    const labels = ['fehlgeschlagen', 'fertig', 'in Arbeit', 'wartend']
    const statuses = ['failed', 'done', 'running', 'pending']
    items.forEach((item, i) => {
      const badge = within(item).getByText(labels[i])
      expect(badge.getAttribute('data-status')).toBe(statuses[i])
    })
    expect(screen.getAllByText('Wörter zählen')).toHaveLength(4)
  })

  it('shows results for done jobs and the error for failed jobs', () => {
    render(
      <JobList
        loading={false}
        error={null}
        jobs={[
          job({ id: 5, analysis: 'top_words', status: 'done', result: '[{"word":"haus","count":4}]' }),
          job({ id: 4, analysis: 'top_words', status: 'done', result: 'kein json' }),
          job({ id: 3, analysis: 'reading_time', status: 'done', result: '2' }),
          job({ id: 2, analysis: 'word_count', status: 'done', result: '100000' }),
          job({ id: 1, status: 'failed', error: 'Unbekannte Analyse' }),
        ]}
      />,
    )
    expect(screen.getByText('haus × 4')).toBeTruthy()
    expect(screen.getByText('kein json')).toBeTruthy()
    expect(screen.getByText('2 Min. Lesezeit')).toBeTruthy()
    expect(screen.getByText('100.000 Wörter')).toBeTruthy()
    expect(screen.getByText('Fehler: Unbekannte Analyse')).toBeTruthy()
  })

  it('shows the empty state when there are no jobs and nothing is loading', () => {
    render(<JobList jobs={[]} loading={false} error={null} />)
    expect(screen.getByText('Noch keine Aufträge')).toBeTruthy()
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('shows no empty state while loading', () => {
    render(<JobList jobs={[]} loading={true} error={null} />)
    expect(screen.queryByText('Noch keine Aufträge')).toBeNull()
  })

  it('shows an error notice and keeps the list visible', () => {
    render(<JobList jobs={[job({ id: 9 })]} loading={false} error="Die API ist nicht erreichbar." />)
    expect(screen.getByRole('alert').textContent).toContain(ERROR_NOTICE_TEXT)
    expect(screen.getByText('#9')).toBeTruthy()
  })

  it('renders markup in job content as text only', () => {
    const payload = '<img src=x onerror=alert(1)>'
    const { container } = render(
      <JobList
        loading={false}
        error={null}
        jobs={[
          job({ id: 2, text: payload, status: 'failed', error: payload }),
          job({ id: 1, text: payload, status: 'done', analysis: 'top_words', result: payload }),
        ]}
      />,
    )
    expect(container.querySelector('img')).toBeNull()
    expect(screen.getAllByText(payload).length).toBeGreaterThanOrEqual(3)
  })
})
