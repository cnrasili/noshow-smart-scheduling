import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Polling is needed for file changes to reach Docker containers on Windows and macOS
    watch: { usePolling: process.env.WATCH_POLLING === 'true' },
  },
})
