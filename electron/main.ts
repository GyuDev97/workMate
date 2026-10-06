import { app, BrowserWindow, globalShortcut, Menu, nativeImage, Notification, Tray } from 'electron'
import { ChildProcess, spawn } from 'node:child_process'
import path from 'node:path'

let windowRef: BrowserWindow | null = null
let tray: Tray | null = null
let backend: ChildProcess | null = null
let isQuitting = false
const isDev = process.env.WORKMATE_BACKEND_MODE === 'development'
const backendUrl = process.env.WORKMATE_BACKEND_URL ?? 'http://127.0.0.1:8765'
const rendererUrl = 'http://127.0.0.1:5173'

function startBackend() {
  if (!isDev || backend) return
  const python = process.env.WORKMATE_PYTHON ?? 'python3'
  backend = spawn(python, ['-m', 'uvicorn', 'server.main:app', '--host', '127.0.0.1', '--port', '8765'], {
    cwd: path.join(__dirname, '..', 'backend'),
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
    stdio: 'pipe'
  })
  backend.stdout?.on('data', (chunk: Buffer) => process.stdout.write(`[backend] ${chunk.toString()}`))
  backend.stderr?.on('data', (chunk: Buffer) => process.stderr.write(`[backend] ${chunk.toString()}`))
  backend.on('error', (error) => console.error('Unable to start workMate backend:', error.message))
  backend.on('exit', (code, signal) => {
    console.info(`[backend] exited code=${code ?? 'none'} signal=${signal ?? 'none'}`)
    backend = null
  })
}

async function waitForBackend() {
  if (!isDev) return
  for (let attempt = 0; attempt < 20; attempt += 1) {
    try {
      const response = await fetch(`${backendUrl}/health`)
      if (response.ok) return
    } catch { /* backend is still starting */ }
    await new Promise((resolve) => setTimeout(resolve, 200))
  }
  console.warn(`[backend] did not become ready at ${backendUrl}; renderer will show its retry state.`)
}

function createWindow() {
  windowRef = new BrowserWindow({
    width: 1260,
    height: 820,
    minWidth: 980,
    minHeight: 680,
    title: 'workMate',
    backgroundColor: '#f7f8fc',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  })
  const url = isDev ? rendererUrl : `file://${path.join(__dirname, '../dist/index.html')}`
  windowRef.webContents.on('did-fail-load', (_event, errorCode, errorDescription, validatedUrl, isMainFrame) => {
    if (isMainFrame) console.error(`[renderer] load failed (${errorCode}): ${errorDescription} — ${validatedUrl}`)
  })
  windowRef.webContents.on('render-process-gone', (_event, details) => {
    console.error(`[renderer] process gone: ${details.reason} (exit ${details.exitCode})`)
  })
  windowRef.webContents.on('console-message', (_event, level, message, line, sourceId) => {
    if (isDev) console.info(`[renderer console:${level}] ${message} (${sourceId}:${line})`)
  })
  void windowRef.loadURL(url).catch((error: Error) => console.error(`[renderer] unable to load ${url}:`, error.message))
  if (isDev && process.env.WORKMATE_OPEN_DEVTOOLS === '1') windowRef.webContents.openDevTools({ mode: 'detach' })
  windowRef.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault()
      windowRef?.hide()
    }
  })
}

function toggleAssistant() {
  if (!windowRef) return
  if (windowRef.isVisible()) windowRef.hide()
  else {
    windowRef.show()
    windowRef.focus()
  }
}

function createTray() {
  // A template image stays legible in both macOS menu-bar appearances.
  const icon = nativeImage.createEmpty()
  tray = new Tray(icon)
  tray.setToolTip('workMate — 개인 AI 업무 비서')
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: 'workMate 열기', click: () => { windowRef?.show(); windowRef?.focus() } },
    { label: '오늘 브리핑 보기', click: () => { windowRef?.show(); windowRef?.webContents.send('navigate', 'home') } },
    { type: 'separator' },
    { label: '종료', click: () => { isQuitting = true; app.quit() } }
  ]))
  tray.on('click', toggleAssistant)
}

app.whenReady().then(async () => {
  startBackend()
  await waitForBackend()
  createWindow()
  createTray()
  globalShortcut.register('CommandOrControl+Shift+Space', toggleAssistant)
  if (Notification.isSupported()) {
    // The scheduler will own actionable reminders; this only verifies the native path exists.
    console.info('Native notifications are available. Backend:', backendUrl)
  }
  app.on('activate', () => windowRef ? windowRef.show() : createWindow())
})

app.on('before-quit', () => {
  isQuitting = true
  globalShortcut.unregisterAll()
  backend?.kill()
})

app.on('window-all-closed', () => {
  // Keep the resident assistant alive on macOS; Windows uses the tray as well.
  if (process.platform !== 'darwin') return
})
