import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as api from '../api'
import { JobForm } from './JobForm'

afterEach(() => {
  vi.restoreAllMocks()
})

const sampleJob: api.Job = {
  id: 1,
  text: 'Hallo Welt',
  analysis: 'top_words',
  status: 'pending',
  result: null,
  error: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

describe('JobForm', () => {
  it('disables submit while the text is empty or only whitespace', async () => {
    render(<JobForm onCreated={() => {}} />)
    const button = screen.getByRole('button', { name: 'Auftrag erstellen' })
    expect(button).toBeDisabled()
    await userEvent.type(screen.getByLabelText('Text'), '   ')
    expect(button).toBeDisabled()
    await userEvent.type(screen.getByLabelText('Text'), 'a')
    expect(button).toBeEnabled()
  })

  it('shows no error on the untouched form', () => {
    render(<JobForm onCreated={() => {}} />)
    expect(screen.queryByRole('alert')).toBeNull()
    expect(screen.getByLabelText('Text')).toHaveAttribute('aria-invalid', 'false')
  })

  it('submits with the chosen analysis, calls onCreated and clears the text', async () => {
    const spy = vi.spyOn(api, 'createJob').mockResolvedValue(sampleJob)
    const onCreated = vi.fn()
    render(<JobForm onCreated={onCreated} />)
    await userEvent.type(screen.getByLabelText('Text'), 'Hallo Welt')
    await userEvent.selectOptions(screen.getByLabelText('Analyse'), 'Häufigste Wörter')
    await userEvent.click(screen.getByRole('button', { name: 'Auftrag erstellen' }))
    await waitFor(() => expect(onCreated).toHaveBeenCalledTimes(1))
    expect(spy).toHaveBeenCalledWith('Hallo Welt', 'top_words')
    expect(screen.getByLabelText('Text')).toHaveValue('')
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('shows the server error after submit', async () => {
    vi.spyOn(api, 'createJob').mockRejectedValue(
      new api.ApiError('Die API ist nicht erreichbar.', 0),
    )
    const onCreated = vi.fn()
    render(<JobForm onCreated={onCreated} />)
    await userEvent.type(screen.getByLabelText('Text'), 'Text')
    await userEvent.click(screen.getByRole('button', { name: 'Auftrag erstellen' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Die API ist nicht erreichbar.')
    expect(onCreated).not.toHaveBeenCalled()
    expect(screen.getByLabelText('Text')).toHaveValue('Text')
  })
})
