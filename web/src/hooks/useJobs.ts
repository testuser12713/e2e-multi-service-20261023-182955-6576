import type { Job } from '../api'

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

const NO_JOBS: Job[] = []

const refreshNothing = (): Promise<void> => Promise.resolve()

/**
 * The job list, polled from the API every `intervalMs` milliseconds while the
 * component using it is mounted.
 *
 * Inert in the web skeleton: it returns an empty, settled list and never calls the
 * API. Polling belongs to the ticket 'Implement automatic list refresh'.
 */
export function useJobs(intervalMs: number = 3000): UseJobsResult {
  void intervalMs
  return { jobs: NO_JOBS, error: null, loading: false, refresh: refreshNothing }
}
