import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // Bind explicitly to the same IPv4 loopback address used by Electron.
  // On macOS, Vite's default localhost may bind only to ::1 while Electron
  // loads 127.0.0.1, resulting in a blank chrome-error renderer page.
  server: { host: '127.0.0.1', port: 5173, strictPort: true },
  build: { outDir: 'dist' }
})
