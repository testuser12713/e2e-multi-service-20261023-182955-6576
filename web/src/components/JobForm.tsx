import type { ReactElement } from 'react'

export type JobFormProps = {
  /** Called after the API accepted a new job, so the list can refresh immediately. */
  onCreated: () => void
}

/**
 * The fields of the 'Neuer Auftrag' card: Textarea 'Text' with character counter,
 * Select 'Analyse', inline ErrorNotice and the 'Auftrag erstellen' button
 * (DESIGN.md ### Home (/)). App renders the card and its heading around it.
 *
 * Inert in the web skeleton: it renders nothing. The form belongs to the ticket
 * 'Build the job creation form'.
 */
export function JobForm(_props: JobFormProps): ReactElement | null {
  return null
}
