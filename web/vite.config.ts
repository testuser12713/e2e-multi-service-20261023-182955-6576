/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    fs: {
      // src/styles.css imports the design's self-hosted fonts from ../design/fonts;
      // the dev server may serve this project and exactly that folder, nothing else.
      allow: ['.', '../design/fonts'],
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
