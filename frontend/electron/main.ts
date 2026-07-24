import { app, BrowserWindow, ipcMain, shell } from 'electron'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import crypto from 'node:crypto'
import fs from 'node:fs'
import { spawn, ChildProcess } from 'node:child_process'
import * as envSetup from './env-setup'

const require = createRequire(import.meta.url)
const __dirname = path.dirname(fileURLToPath(import.meta.url))

process.env.APP_ROOT = path.join(__dirname, '..')

export const VITE_DEV_SERVER_URL = process.env['VITE_DEV_SERVER_URL']
export const MAIN_DIST = path.join(process.env.APP_ROOT, 'dist-electron')
export const RENDERER_DIST = path.join(process.env.APP_ROOT, 'dist')

process.env.VITE_PUBLIC = VITE_DEV_SERVER_URL ? path.join(process.env.APP_ROOT, 'public') : RENDERER_DIST

let win: BrowserWindow | null

function getProjectRoot(): string {
  if (app.isPackaged) return process.resourcesPath
  return path.resolve(__dirname, '..', '..')
}

function getPythonExe(): string {
  if (app.isPackaged) {
    const bundled = path.join(path.dirname(process.resourcesPath), 'python', 'python.exe')
    if (fs.existsSync(bundled)) return bundled
    const appData = envSetup.getPythonExe()
    if (fs.existsSync(appData)) return appData
    return bundled
  }
  const venv = path.join(getProjectRoot(), 'venv', 'Scripts', 'python.exe')
  if (fs.existsSync(venv)) return venv
  return 'python'
}

const PROJECT_ROOT = getProjectRoot()
const PYTHON_EXE = getPythonExe()

let inferenceProcess: ChildProcess | null = null
let cloudProcess: ChildProcess | null = null

function spawnBackend(label: string, module: string): ChildProcess {
  const logFile = path.join(app.getPath("userData"), "backend.log")
  fs.appendFileSync(logFile, `[${new Date().toISOString()}] spawnBackend: ${label} module=${module} python=${PYTHON_EXE} cwd=${PROJECT_ROOT}\n`)

  if (!fs.existsSync(PYTHON_EXE)) {
    const msg = `[${new Date().toISOString()}] PYTHON_EXE NOT FOUND: ${PYTHON_EXE}`
    fs.appendFileSync(logFile, msg + "\n")
    console.error("[VoxAeterna] " + msg)
    return spawn('cmd', ['/c', 'echo Python runtime not found'], { stdio: 'pipe', windowsHide: true })
  }

  const sitePackages = `import sys, os; _sp = os.path.join(os.path.dirname(sys.executable), 'Lib', 'site-packages'); os.path.isdir(_sp) and _sp not in sys.path and sys.path.insert(0, _sp)`
  const args = ['-c', `${sitePackages}; import sys; sys.path.insert(0, r"${PROJECT_ROOT}"); import runpy; runpy.run_module("${module}", run_name="__main__")`]

  console.log(`[VoxAeterna] start ${label}: ${PYTHON_EXE}`)

  const child = spawn(PYTHON_EXE, args, { cwd: PROJECT_ROOT, stdio: 'pipe', windowsHide: true })
  child.stdout?.on('data', (data: Buffer) => {
    const msg = data.toString().trim()
    console.log(`[${label}] ${msg}`)
    fs.appendFileSync(logFile, `[${label}] ${msg}\n`)
  })
  child.stderr?.on('data', (data: Buffer) => {
    const msg = data.toString().trim()
    console.error(`[${label}] ${msg}`)
    fs.appendFileSync(logFile, `[${label} stderr] ${msg}\n`)
  })
  child.on('error', (err) => {
    console.error(`[${label}] error:`, err.message)
    fs.appendFileSync(logFile, `[${new Date().toISOString()}] ${label} error: ${err.message}\n`)
  })
  child.on('exit', (code, signal) => {
    console.log(`[${label}] exit code=${code} signal=${signal}`)
    fs.appendFileSync(logFile, `[${new Date().toISOString()}] ${label} exit: code=${code} signal=${signal}\n`)
  })
  return child
}

function startBackends() {
  inferenceProcess = spawnBackend('Inference', 'backend.app.main')
  cloudProcess = spawnBackend('Cloud', 'cloud.main')
}

function stopBackends() {
  for (const [label, proc] of [['Inference', inferenceProcess], ['Cloud', cloudProcess]] as const) {
    if (proc && !proc.killed) {
      console.log(`[VoxAeterna] stop ${label}...`)
      proc.kill()
      setTimeout(() => { if (!proc.killed) proc.kill('SIGKILL') }, 5000)
    }
  }
  inferenceProcess = null
  cloudProcess = null
}

ipcMain.handle("env-setup:check", async () => {
  const hasPython = fs.existsSync(PYTHON_EXE)
  const hasGPU = envSetup.checkGPU()
  if (!app.isPackaged) {
    return { python: hasPython, pythonPath: PYTHON_EXE, gpu: hasGPU, deps: { ok: true, missing: [] } }
  }
  return { python: hasPython, pythonPath: PYTHON_EXE, gpu: hasGPU, deps: { ok: hasPython, missing: hasPython ? [] : ["Python runtime not found"] } }
})

ipcMain.handle("env-setup:check-models", async () => envSetup.checkModels())
ipcMain.handle("env-setup:download-models", async () => envSetup.downloadModels(win))
ipcMain.handle("env-setup:cancel", async () => { envSetup.requestCancel(); return { message: "ok" } })
ipcMain.handle("env-setup:restart", async () => { app.relaunch(); app.exit(0) })
ipcMain.handle("env-setup:check-torch", async () => true)
ipcMain.handle("env-setup:torch-guide", async () => ({ cmd: "", size: "" }))
ipcMain.handle("env-setup:download-python", async () => ({ success: false, error: "extract python-runtime.zip to app install dir/python/" }))
ipcMain.handle("env-setup:install", async () => ({ success: false, error: "deps pre-installed in runtime zip" }))

function createWindow() {
  const iconPath = app.isPackaged ? path.join(process.resourcesPath, 'favicon.ico') : path.join(getProjectRoot(), 'favicon.ico')
  win = new BrowserWindow({ icon: iconPath, frame: false, titleBarStyle: 'hidden', backgroundColor: '#0D0D0C', webPreferences: { preload: path.join(__dirname, 'preload.mjs') } })
  win.webContents.on('did-finish-load', () => win?.webContents.send('main-process-message', (new Date).toLocaleString()))
  if (VITE_DEV_SERVER_URL) { win.loadURL(VITE_DEV_SERVER_URL) } else { win.loadFile(path.join(RENDERER_DIST, 'index.html')) }
}

app.on('window-all-closed', () => { if (process.platform !== 'darwin') { app.quit(); win = null } })
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow() })

function getDeviceFingerprint(): string {
  const fpDir = app.getPath('userData'), fpFile = path.join(fpDir, '.device_fingerprint')
  try {
    if (fs.existsSync(fpFile)) return fs.readFileSync(fpFile, 'utf-8').trim()
    const fp = crypto.randomUUID(); fs.writeFileSync(fpFile, fp, 'utf-8'); return fp
  } catch {
    try { return crypto.createHash('sha256').update(app.getPath('home')).digest('hex').slice(0, 32) }
    catch { return crypto.randomUUID() }
  }
}

ipcMain.handle('get-device-fingerprint', () => getDeviceFingerprint())
ipcMain.handle('window-minimize', () => win?.minimize())
ipcMain.handle('window-maximize', () => { if (win?.isMaximized()) win.unmaximize(); else win?.maximize() })
ipcMain.handle('window-close', () => win?.close())
ipcMain.handle('window-is-maximized', () => win?.isMaximized() ?? false)
ipcMain.handle('get-app-version', () => app.getVersion())
ipcMain.handle('open-external-url', (_event: any, url: string) => shell.openExternal(url))

function setupWindowStateListener() {
  win?.on('maximize', () => win?.webContents.send('window-maximized', true))
  win?.on('unmaximize', () => win?.webContents.send('window-maximized', false))
}

app.whenReady().then(() => { startBackends(); createWindow(); setupWindowStateListener() })
app.on('will-quit', () => stopBackends())
