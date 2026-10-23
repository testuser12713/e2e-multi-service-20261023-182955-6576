import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, type Job } from '../api'
import { useJobs } from './useJobs'

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>()
  return { ...actual, listJobs: vi.fn() }
})

import { listJobs } from '../api'

const listJobsMock = vi.mocked(listJobs)

function job(status: Job['status']): Job {
  return {
    id: 1,
    text: 'eins zwei drei',
    analysis: 'word_count',
    status,
    result: status === 'done' ? '3' : null,
    error: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }
}

async function flush(): Promise<void> {
  await act(async () => {
    await Promise.resolve()
    await Promise.resolve()
  })
}

describe('useJobs', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    listJobsMock.mockReset()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('loads on mount and ends loading', async () => {
    listJobsMock.mockResolvedValue([job('pending')])
    const { result } = renderHook(() => useJobs())
    expect(result.current.loading).toBe(true)
    await flush()
    expect(result.current.loading).toBe(false)
    expect(result.current.jobs).toEqual([job('pending')])
    expect(listJobsMock).toHaveBeenCalledTimes(1)
  })

  it('polls after 3 seconds and shows the changed status', async () => {
    listJobsMock.mockResolvedValueOnce([job('pending')]).mockResolvedValueOnce([job('running')])
    const { result } = renderHook(() => useJobs())
    await flush()
    expect(result.current.jobs[0].status).toBe('pending')
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2999)
    })
    expect(listJobsMock).toHaveBeenCalledTimes(1)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1)
    })
    expect(listJobsMock).toHaveBeenCalledTimes(2)
    expect(result.current.jobs[0].status).toBe('running')
    expect(result.current.loading).toBe(false)
  })

  it('refresh() reloads immediately', async () => {
    listJobsMock.mockResolvedValueOnce([]).mockResolvedValueOnce([job('pending')])
    const { result } = renderHook(() => useJobs())
    await flush()
    await act(async () => {
      await result.current.refresh()
    })
    expect(listJobsMock).toHaveBeenCalledTimes(2)
    expect(result.current.jobs).toHaveLength(1)
  })

  it('sets an error, keeps the list, and clears it on recovery', async () => {
    listJobsMock
      .mockResolvedValueOnce([job('pending')])
      .mockRejectedValueOnce(new ApiError('Die API ist nicht erreichbar.', 0))
      .mockResolvedValueOnce([job('done')])
    const { result } = renderHook(() => useJobs())
    await flush()
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000)
    })
    expect(result.current.error).toBe('Die API ist nicht erreichbar.')
    expect(result.current.jobs[0].status).toBe('pending')
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000)
    })
    expect(result.current.error).toBeNull()
    expect(result.current.jobs[0].status).toBe('done')
  })

  it('stops polling after unmount', async () => {
    listJobsMock.mockResolvedValue([])
    const { unmount } = renderHook(() => useJobs())
    await flush()
    unmount()
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10000)
    })
    expect(listJobsMock).toHaveBeenCalledTimes(1)
  })
})
