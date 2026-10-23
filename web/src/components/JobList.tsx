import type { ReactElement } from 'react'
import type { Job } from '../api'

export type JobListProps = {
  jobs: Job[]
  loading: boolean
  error: string | null
}

/**
 * The body of the 'Aufträge' card: ErrorNotice, SkeletonRows on the first load,
 * EmptyState or the JobItem rows (DESIGN.md ### Home (/)). App renders the card and
 * its header ('Aufträge' with the count badge) around it.
 *
 * Inert in the web skeleton: it renders nothing. The list belongs to the ticket
 * 'Build the job list with status badges and error notice'.
 */
export function JobList(_props: JobListProps): ReactElement | null {
  return null
}
