import { app, BrowserWindow, ipcMain, shell } from 'electron'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import crypto from 'node:crypto'
import fs from 'node:fs'
import { spawn, ChildProcess } from 'node:child_process'

const require = createRequire(import.meta.url)
const __dirname = path.dirname(fileURLToPath(import.meta.url))

// The built directory structure
//
// ├─┬─┬ dist
// │ │ └── index.html
// │ │
// │ ├─┬ dist-electron
// │ │ ├── main.js
// │ │ └── preload.mjs
// │
process.env.APP_ROOT = path.join(__dirname, '..')

// 🚧 Use ['ENV_NAME'] avoid vite:define plugin - Vite@2.x
export const VITE_DEV_SERVER_URL = process.env['VITE_DEV_SERVER_URL']
export const MAIN_DIST = path.join(process.env.APP_ROOT, 'dist-electron')
export const RENDERER_DIST = path.join(process.env.APP_ROOT, 'dist')

process.env.VITE_PUBLIC = VITE_DEV_SERVER_URL ? path.join(process.env.APP_ROOT, 'public') : RENDERER_DIST

let win: BrowserWindow | null

// ========== Python 后端子进程管理 ==========

/**
 * 开发模式下：项目根是 VoiceStudio/
 * 打包后：backend/、cloud/、.env 通过 extraResources 放在 resources/ 下
 */
function getProjectRoot(): string {
  if (app.isPackaged) {
    return process.resourcesPath
  }
  // 开发模式：__dirname = frontend/dist-electron/，向上 2 级 = VoiceStudio/
  return path.resolve(__dirname, '..', '..')
}

function getPythonExe(): string {
  // 打包后：尝试 resources/ 下的便携 Python，否则用系统 python
  if (app.isPackaged) {
    const bundled = path.join(process.resourcesPath, 'python', 'python.exe')
    if (fs.existsSync(bundled)) {
      return bundled
    }
    // 后备：系统 PATH 里的 python
    return 'python'
  }
  // 开发模式：项目 venv
  return path.join(getProjectRoot(), 'venv', 'Scripts', 'python.exe')
}

const PROJECT_ROOT = getProjectRoot()
const PYTHON_EXE = getPythonExe()

let inferenceProcess: ChildProcess | null = null
let cloudProcess: ChildProcess | null = null

function spawnBackend(label: string, module: string): ChildProcess {
  const args = ['-m', module]
  console.log(`[VoxAeterna] 启动 ${label}: ${PYTHON_EXE} ${args.join(' ')}`)
  const child = spawn(PYTHON_EXE, args, {
    cwd: PROJECT_ROOT,
    stdio: 'pipe',
    windowsHide: true,
  })
  child.stdout?.on('data', (data: Buffer) => {
    console.log(`[${label}] ${data.toString().trim()}`)
  })
  child.stderr?.on('data', (data: Buffer) => {
    console.error(`[${label}] ${data.toString().trim()}`)
  })
  child.on('error', (err) => {
    console.error(`[${label}] 进程错误:`, err.message)
  })
  child.on('exit', (code, signal) => {
    console.log(`[${label}] 进程退出, code=${code} signal=${signal}`)
  })
  return child
}

function startBackends() {
  // 推理后端: backend.app.main → 127.0.0.1:9880
  inferenceProcess = spawnBackend('Inference', 'backend.app.main')

  // 云端服务: cloud.main → 0.0.0.0:8000
  cloudProcess = spawnBackend('Cloud', 'cloud.main')
}

function stopBackends() {
  for (const [label, proc] of [['Inference', inferenceProcess], ['Cloud', cloudProcess]] as const) {
    if (proc && !proc.killed) {
      console.log(`[VoxAeterna] 停止 ${label}...`)
      // Windows 上 SIGTERM 等同于 taskkill，直接用 process.kill()
      proc.kill()
      // 强杀兜底
      setTimeout(() => {
        if (!proc.killed) {
          proc.kill('SIGKILL')
        }
      }, 5000)
    }
  }
  inferenceProcess = null
  cloudProcess = null
}

// ============================================================

function createWindow() {
  // 开发模式用项目根 icon.png，打包后用 resources/icon.png
  const iconPath = app.isPackaged
    ? path.join(process.resourcesPath, 'icon.png')
    : path.join(PROJECT_ROOT, 'icon.png')

  win = new BrowserWindow({
    icon: iconPath,
    frame: false,
    titleBarStyle: 'hidden',
    backgroundColor: '#0D0D0C',
    // 允许窗口背景色从渲染进程的 color-scheme / theme 继承
    // backgroundColor 是窗口创建瞬间的底色，之后被 web 页面覆盖
    webPreferences: {
      preload: path.join(__dirname, 'preload.mjs'),
    },
  })

  // Test active push message to Renderer-process.
  win.webContents.on('did-finish-load', () => {
    win?.webContents.send('main-process-message', (new Date).toLocaleString())
  })

  if (VITE_DEV_SERVER_URL) {
    win.loadURL(VITE_DEV_SERVER_URL)
  } else {
    // win.loadFile('dist/index.html')
    win.loadFile(path.join(RENDERER_DIST, 'index.html'))
  }
}

// Quit when all windows are closed, except on macOS. There, it's common
// for applications and their menu bar to stay active until the user quits
// explicitly with Cmd + Q.
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
    win = null
  }
})

app.on('activate', () => {
  // On OS X it's common to re-create a window in the app when the
  // dock icon is clicked and there are no other windows open.
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow()
  }
})

// 设备指纹 —— 持久化到 userData，每台机器首次安装后固定不变
function getDeviceFingerprint(): string {
  const fpDir = app.getPath('userData')
  const fpFile = path.join(fpDir, '.device_fingerprint')
  try {
    if (fs.existsSync(fpFile)) {
      return fs.readFileSync(fpFile, 'utf-8').trim()
    }
    const fp = crypto.randomUUID()
    fs.writeFileSync(fpFile, fp, 'utf-8')
    return fp
  } catch {
    // 权限不足时用 machineId 作为后备
    try {
      return crypto.createHash('sha256').update(app.getPath('home')).digest('hex').slice(0, 32)
    } catch {
      return crypto.randomUUID()
    }
  }
}

ipcMain.handle('get-device-fingerprint', () => getDeviceFingerprint())

// 窗口控制 IPC
ipcMain.handle('window-minimize', () => win?.minimize())
ipcMain.handle('window-maximize', () => {
  if (win?.isMaximized()) {
    win.unmaximize()
  } else {
    win?.maximize()
  }
})
ipcMain.handle('window-close', () => win?.close())
ipcMain.handle('window-is-maximized', () => win?.isMaximized() ?? false)

// 窗口最大化状态变化通知渲染进程

// 获取应用版本号
ipcMain.handle('get-app-version', () => app.getVersion())

// 打开外部链接
ipcMain.handle('open-external-url', (_event, url: string) => {
  return shell.openExternal(url)
})

function setupWindowStateListener() {
  win?.on('maximize', () => win?.webContents.send('window-maximized', true))
  win?.on('unmaximize', () => win?.webContents.send('window-maximized', false))
}

app.whenReady().then(() => {
  startBackends()
  createWindow()
  setupWindowStateListener()
})

app.on('will-quit', () => {
  stopBackends()
})
