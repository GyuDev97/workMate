import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('workMate', {
  platform: process.platform,
  onNavigate: (callback: (page: string) => void) => ipcRenderer.on('navigate', (_event, page) => callback(page))
})
