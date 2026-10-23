import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, type Job, listJobs } from '../api'

export type UseJobsResult = {
  /** Last successfully loaded list, newest first; kept while a later poll fails. */
  jobs: Job[]
  /** German message while the API is unreachable, otherwise null. */
  error: string | null
  /** True only during the first load. */
  loading: boolean
  /** Loads the list right now (e.g. after a job was created). */
  refresh: () => Promise<void>
}

const FALLBACK_ERROR = 'Die API ist nicht erreichbar.'

/**
 * The job list, polled from the API every `intervalMs` milliseconds while the
 * component using it is mounted. Results arriving after unmount, or older than a
 * response already applied, are ignored.
 */
export function useJobs(intervalMs: number = 3000): UseJobsResult {
  const [jobs, setJobs] = useState<Job[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const mounted = useRef<boolean>(false)
  const requestSeq = useRef<number>(0)
  const appliedSeq = useRef<number>(0)

  const refresh = useCallback(async (): Promise<void> => {
    const seq = ++requestSeq.current
    try {
      const list = await listJobs()
      if (!mounted.current || seq < appliedSeq.current) return
      appliedSeq.current = seq
      setJobs(list)
      setError(null)
    } catch (err) {
      if (!mounted.current || seq < appliedSeq.current) return
      appliedSeq.current = seq
      setError(err instanceof ApiError && err.message ? err.message : FALLBACK_ERROR)
    } finally {
      if (mounted.current) setLoading(false)
    }
  }, [])

  useEffect(() => {
    mounted.current = true
    void refresh()
    const id = setInterval(() => {
      void refresh()
    }, intervalMs)
    return () => {
      mounted.current = false
      clearInterval(id)
    }
  }, [intervalMs, refresh])

  return { jobs, error, loading, refresh }
}
