import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import './styles.css'

const rootElement = document.getElementById('root')
if (!rootElement) {
  throw new Error('index.html has no element with id "root" to mount the app into.')
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
