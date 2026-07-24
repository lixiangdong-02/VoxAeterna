/**
 * VoxAeterna 环境初始化模块
 * 策略：嵌入版 Python（用户自行解压 python-runtime.zip）→ 下载模型
 */
import { app, BrowserWindow } from "electron"
import fs from "node:fs"
import path from "node:path"
import https from "node:https"
import http from "node:http"
import { execSync, ChildProcess } from "node:child_process"

// ===================== 常量 =====================

function getAppDataDir(): string {
  return path.join(app.getPath("appData"), "VoxAeterna")
}

export function getPythonDir(): string {
  return path.join(getAppDataDir(), "python")
}

export function getPythonExe(): string {
  return path.join(getPythonDir(), "python.exe")
}

export function getModelsDir(): string {
  return path.join(getAppDataDir(), "models")
}

export function getPretrainedModelsDir(): string {
  return path.join(getAppDataDir(), "pretrained_models")
}

const MODEL_REPO = "anmain001/VoxAeterna-Models"
const MODEL_BASE = "https://modelscope.cn/api/v1/models/" + MODEL_REPO + "/repo"

// ===================== 取消机制 =====================

let cancelRequested = false

export function requestCancel(): void { cancelRequested = true }

export function resetCancel(): void { cancelRequested = false }

// ===================== 进度推送 =====================

function sendProgress(win: BrowserWindow | null, data: Record<string, unknown>): void {
  if (win && !win.isDestroyed()) win.webContents.send("env-setup:progress", data)
}

// ===================== 基础检测 =====================

export function checkPython(): boolean {
  return fs.existsSync(getPythonExe())
}

export function checkGPU(): boolean {
  try {
    execSync("nvidia-smi", { timeout: 5000, windowsHide: true, stdio: "pipe" })
    return true
  } catch { return false }
}

export function checkModels(): boolean {
  const dir = getModelsDir()
  if (!fs.existsSync(dir)) return false
  try {
    return fs.readdirSync(dir).some(f => f.endsWith(".pth") || f.endsWith(".ckpt"))
  } catch { return false }
}

export function checkPretrainedModels(): boolean {
  const dir = getPretrainedModelsDir()
  if (!fs.existsSync(dir)) return false
  try {
    return fs.readdirSync(dir).length > 0
  } catch { return false }
}

// ===================== 文件下载 =====================

function downloadFile(url: string, dest: string, win: BrowserWindow | null, label: string): Promise<{ success: boolean; error?: string }> {
  return new Promise(_resolve => {
    console.log("[VoxAeterna] Downloading: " + url)
    const proto = url.startsWith("https") ? https : http
    const req = proto.get(url, {
      headers: { "User-Agent": "VoxAeterna/1.0" }
    }, res => {
      if (res.statusCode && res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        downloadFile(res.headers.location, dest, win, label).then(_resolve)
        return
      }
      if (res.statusCode !== 200) {
        _resolve({ success: false, error: "HTTP " + res.statusCode })
        return
      }
      const total = parseInt(res.headers["content-length"] || "0", 10)
      let downloaded = 0
      let lastTime = Date.now()
      const dir = path.dirname(dest)
      if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true })
      const ws = fs.createWriteStream(dest)
      res.on("data", (chunk: Buffer) => {
        downloaded += chunk.length
        ws.write(chunk)
        if (Date.now() - lastTime > 500) {
          lastTime = Date.now()
          sendProgress(win, {
            phase: "downloading",
            label,
            downloaded,
            total,
            percent: total > 0 ? Math.round(downloaded / total * 100) : 0
          })
        }
      })
      res.on("end", () => {
        ws.end()
        if (cancelRequested) {
          try { fs.unlinkSync(dest) } catch {}
          _resolve({ success: false, error: "用户取消" })
        } else {
          _resolve({ success: true })
        }
      })
      res.on("error", (e: Error) => {
        ws.close()
        try { fs.unlinkSync(dest) } catch {}
        _resolve({ success: false, error: e.message })
      })
    })
    req.on("error", (e: Error) => _resolve({ success: false, error: e.message }))
    req.setTimeout(300000, () => { req.destroy(); _resolve({ success: false, error: "下载超时" }) })
  })
}

// ===================== 模型下载 =====================

export async function downloadModels(win: BrowserWindow | null): Promise<{ success: boolean; error?: string }> {
  resetCancel()
  const dir = getModelsDir()
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true })

  const files = await fetchModelList()
  if (files.length === 0) return { success: false, error: "无法获取模型文件列表" }

  const totalSize = files.reduce((s, f) => s + f.size, 0)
  let downloadedCount = 0

  for (const f of files) {
    if (cancelRequested) return { success: false, error: "用户取消" }
    const dest = path.join(dir, f.name)
    const url = MODEL_BASE + "/resolve/master/" + encodeURIComponent(f.name)
    const r = await downloadFile(url, dest, win, f.name)
    if (!r.success) return r
    downloadedCount++
    sendProgress(win, {
      phase: "downloading",
      label: f.name,
      downloaded: downloadedCount,
      total: files.length,
      percent: Math.round(downloadedCount / files.length * 100)
    })
  }

  sendProgress(win, {
    phase: "downloading",
    label: "模型下载完成",
    downloaded: totalSize,
    total: totalSize,
    percent: 100
  })
  return { success: true }
}

async function fetchModelList(): Promise<{ name: string; size: number }[]> {
  return new Promise(_resolve => {
    const url = MODEL_BASE + "/files?Revision=master"
    const req = https.get(url, { headers: { "User-Agent": "VoxAeterna/1.0" } }, res => {
      let body = ""
      res.on("data", d => { body += d.toString("utf-8") })
      res.on("end", () => {
        try {
          const data = JSON.parse(body)
          const files = (data.Data?.Files || [])
            .filter((f: any) => f.Name && /\.(pth|ckpt)$|profiles\.json/.test(f.Name))
            .map((f: any) => ({ name: f.Name, size: f.Size || 0 }))
          _resolve(files)
        } catch { _resolve([]) }
      })
    }).on("error", () => _resolve([]))
    req.setTimeout(15000, () => _resolve([]))
  })
}

export async function downloadPretrainedModels(win: BrowserWindow | null): Promise<{ success: boolean; error?: string }> {
  resetCancel()
  const dir = getPretrainedModelsDir()
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true })

  const files = await fetchPretrainedModelList()
  if (files.length === 0) return { success: false, error: "无法获取预训练模型列表" }

  const totalSize = files.reduce((s, f) => s + f.size, 0)
  let totalDownloaded = 0

  for (const f of files) {
    if (cancelRequested) return { success: false, error: "用户取消" }
    const dest = path.join(dir, f.name)
    const subdir = path.dirname(dest)
    if (!fs.existsSync(subdir)) fs.mkdirSync(subdir, { recursive: true })
    const url = MODEL_BASE + "/resolve/master/pretrained_models/" + encodeURIComponent(f.name)
    const r = await downloadFile(url, dest, win, f.name)
    if (!r.success) return r
    totalDownloaded += f.size
    sendProgress(win, {
      phase: "downloading",
      label: f.name,
      downloaded: totalDownloaded,
      total: totalSize,
      percent: totalSize > 0 ? Math.round(totalDownloaded / totalSize * 100) : 0
    })
  }

  sendProgress(win, {
    phase: "downloading",
    label: "预训练模型下载完成",
    downloaded: totalDownloaded,
    total: totalSize,
    percent: 100
  })
  return { success: true }
}

async function fetchPretrainedModelList(): Promise<{ name: string; size: number }[]> {
  const topFiles = await fetchDirFiles("pretrained_models/")
  return topFiles
}

async function fetchDirFiles(dirPath: string): Promise<{ name: string; size: number }[]> {
  return new Promise(_resolve => {
    const url = MODEL_BASE + "/files?Revision=master&FilePath=" + encodeURIComponent(dirPath)
    const req = https.get(url, { headers: { "User-Agent": "VoxAeterna/1.0" } }, res => {
      let body = ""
      res.on("data", d => { body += d.toString("utf-8") })
      res.on("end", async () => {
        try {
          const data = JSON.parse(body)
          const files: { name: string; size: number }[] = []
          for (const f of (data.Data?.Files || [])) {
            if (f.Type === "blob" && f.Name !== ".gitignore") {
              files.push({ name: dirPath.replace("pretrained_models/", "") + f.Name, size: f.Size || 0 })
            } else if (f.Type === "tree") {
              const subFiles = await fetchDirFiles(dirPath + f.Name + "/")
              files.push(...subFiles)
            }
          }
          _resolve(files)
        } catch { _resolve([]) }
      })
    }).on("error", () => _resolve([]))
    req.setTimeout(15000, () => _resolve([]))
  })
}
