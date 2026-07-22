import { app, BrowserWindow, ipcMain } from "electron";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import path from "node:path";
import crypto from "node:crypto";
import fs from "node:fs";
import { spawn } from "node:child_process";
createRequire(import.meta.url);
const __dirname$1 = path.dirname(fileURLToPath(import.meta.url));
process.env.APP_ROOT = path.join(__dirname$1, "..");
const VITE_DEV_SERVER_URL = process.env["VITE_DEV_SERVER_URL"];
const MAIN_DIST = path.join(process.env.APP_ROOT, "dist-electron");
const RENDERER_DIST = path.join(process.env.APP_ROOT, "dist");
process.env.VITE_PUBLIC = VITE_DEV_SERVER_URL ? path.join(process.env.APP_ROOT, "public") : RENDERER_DIST;
let win;
function getProjectRoot() {
  if (app.isPackaged) {
    return process.resourcesPath;
  }
  return path.resolve(__dirname$1, "..", "..");
}
function getPythonExe() {
  if (app.isPackaged) {
    const bundled = path.join(process.resourcesPath, "python", "python.exe");
    if (fs.existsSync(bundled)) {
      return bundled;
    }
    return "python";
  }
  return path.join(getProjectRoot(), "venv", "Scripts", "python.exe");
}
const PROJECT_ROOT = getProjectRoot();
const PYTHON_EXE = getPythonExe();
let inferenceProcess = null;
let cloudProcess = null;
function spawnBackend(label, module) {
  var _a, _b;
  const args = ["-m", module];
  console.log(`[VoxAeterna] 启动 ${label}: ${PYTHON_EXE} ${args.join(" ")}`);
  const child = spawn(PYTHON_EXE, args, {
    cwd: PROJECT_ROOT,
    stdio: "pipe",
    windowsHide: true
  });
  (_a = child.stdout) == null ? void 0 : _a.on("data", (data) => {
    console.log(`[${label}] ${data.toString().trim()}`);
  });
  (_b = child.stderr) == null ? void 0 : _b.on("data", (data) => {
    console.error(`[${label}] ${data.toString().trim()}`);
  });
  child.on("error", (err) => {
    console.error(`[${label}] 进程错误:`, err.message);
  });
  child.on("exit", (code, signal) => {
    console.log(`[${label}] 进程退出, code=${code} signal=${signal}`);
  });
  return child;
}
function startBackends() {
  inferenceProcess = spawnBackend("Inference", "backend.app.main");
  cloudProcess = spawnBackend("Cloud", "cloud.main");
}
function stopBackends() {
  for (const [label, proc] of [["Inference", inferenceProcess], ["Cloud", cloudProcess]]) {
    if (proc && !proc.killed) {
      console.log(`[VoxAeterna] 停止 ${label}...`);
      proc.kill();
      setTimeout(() => {
        if (!proc.killed) {
          proc.kill("SIGKILL");
        }
      }, 5e3);
    }
  }
  inferenceProcess = null;
  cloudProcess = null;
}
function createWindow() {
  const iconPath = app.isPackaged ? path.join(process.resourcesPath, "icon.png") : path.join(PROJECT_ROOT, "icon.png");
  win = new BrowserWindow({
    icon: iconPath,
    frame: false,
    titleBarStyle: "hidden",
    backgroundColor: "#0D0D0C",
    // 允许窗口背景色从渲染进程的 color-scheme / theme 继承
    // backgroundColor 是窗口创建瞬间的底色，之后被 web 页面覆盖
    webPreferences: {
      preload: path.join(__dirname$1, "preload.mjs")
    }
  });
  win.webContents.on("did-finish-load", () => {
    win == null ? void 0 : win.webContents.send("main-process-message", (/* @__PURE__ */ new Date()).toLocaleString());
  });
  if (VITE_DEV_SERVER_URL) {
    win.loadURL(VITE_DEV_SERVER_URL);
  } else {
    win.loadFile(path.join(RENDERER_DIST, "index.html"));
  }
}
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
    win = null;
  }
});
app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
function getDeviceFingerprint() {
  const fpDir = app.getPath("userData");
  const fpFile = path.join(fpDir, ".device_fingerprint");
  try {
    if (fs.existsSync(fpFile)) {
      return fs.readFileSync(fpFile, "utf-8").trim();
    }
    const fp = crypto.randomUUID();
    fs.writeFileSync(fpFile, fp, "utf-8");
    return fp;
  } catch {
    try {
      return crypto.createHash("sha256").update(app.getPath("home")).digest("hex").slice(0, 32);
    } catch {
      return crypto.randomUUID();
    }
  }
}
ipcMain.handle("get-device-fingerprint", () => getDeviceFingerprint());
ipcMain.handle("window-minimize", () => win == null ? void 0 : win.minimize());
ipcMain.handle("window-maximize", () => {
  if (win == null ? void 0 : win.isMaximized()) {
    win.unmaximize();
  } else {
    win == null ? void 0 : win.maximize();
  }
});
ipcMain.handle("window-close", () => win == null ? void 0 : win.close());
ipcMain.handle("window-is-maximized", () => (win == null ? void 0 : win.isMaximized()) ?? false);
function setupWindowStateListener() {
  win == null ? void 0 : win.on("maximize", () => win == null ? void 0 : win.webContents.send("window-maximized", true));
  win == null ? void 0 : win.on("unmaximize", () => win == null ? void 0 : win.webContents.send("window-maximized", false));
}
app.whenReady().then(() => {
  startBackends();
  createWindow();
  setupWindowStateListener();
});
app.on("will-quit", () => {
  stopBackends();
});
export {
  MAIN_DIST,
  RENDERER_DIST,
  VITE_DEV_SERVER_URL
};
