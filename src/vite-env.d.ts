/// <reference types="vite/client" />

interface Window {
  workMate?: {
    platform: string
    onNavigate: (callback: (page: string) => void) => void
  }
}
