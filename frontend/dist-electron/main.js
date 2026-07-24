import { app as l, ipcMain as p, BrowserWindow as T, shell as L } from "electron";
import { createRequire as M } from "node:module";
import { fileURLToPath as N } from "node:url";
import i from "node:path";
import P from "node:crypto";
import s from "node:fs";
import { execSync as q, spawn as _ } from "node:child_process";
import C from "node:https";
import B from "node:http";
function z() {
  return i.join(l.getPath("appData"), "VoxAeterna");
}
function W() {
  return i.join(z(), "python");
}
function b() {
  return i.join(W(), "python.exe");
}
function I() {
  return i.join(z(), "models");
}
const H = "anmain001/VoxAeterna-Models", A = "https://modelscope.cn/api/v1/models/" + H + "/repo";
let g = !1;
function G() {
  g = !0;
}
function J() {
  g = !1;
}
function w(e, n) {
  e && !e.isDestroyed() && e.webContents.send("env-setup:progress", n);
}
function X() {
  try {
    return q("nvidia-smi", { timeout: 5e3, windowsHide: !0, stdio: "pipe" }), !0;
  } catch {
    return !1;
  }
}
function Y() {
  const e = I();
  if (!s.existsSync(e)) return !1;
  try {
    return s.readdirSync(e).some((n) => n.endsWith(".pth") || n.endsWith(".ckpt"));
  } catch {
    return !1;
  }
}
function V(e, n, r, h) {
  return new Promise((d) => {
    console.log("[VoxAeterna] Downloading: " + e);
    const m = (e.startsWith("https") ? C : B).get(e, {
      headers: { "User-Agent": "VoxAeterna/1.0" }
    }, (a) => {
      if (a.statusCode && a.statusCode >= 300 && a.statusCode < 400 && a.headers.location) {
        V(a.headers.location, n, r, h).then(d);
        return;
      }
      if (a.statusCode !== 200) {
        d({ success: !1, error: "HTTP " + a.statusCode });
        return;
      }
      const o = parseInt(a.headers["content-length"] || "0", 10);
      let u = 0, R = Date.now();
      const O = i.dirname(n);
      s.existsSync(O) || s.mkdirSync(O, { recursive: !0 });
      const S = s.createWriteStream(n);
      a.on("data", (y) => {
        u += y.length, S.write(y), Date.now() - R > 500 && (R = Date.now(), w(r, {
          phase: "downloading",
          label: h,
          downloaded: u,
          total: o,
          percent: o > 0 ? Math.round(u / o * 100) : 0
        }));
      }), a.on("end", () => {
        if (S.end(), g) {
          try {
            s.unlinkSync(n);
          } catch {
          }
          d({ success: !1, error: "用户取消" });
        } else
          d({ success: !0 });
      }), a.on("error", (y) => {
        S.close();
        try {
          s.unlinkSync(n);
        } catch {
        }
        d({ success: !1, error: y.message });
      });
    });
    m.on("error", (a) => d({ success: !1, error: a.message })), m.setTimeout(3e5, () => {
      m.destroy(), d({ success: !1, error: "下载超时" });
    });
  });
}
async function K(e) {
  J();
  const n = I();
  s.existsSync(n) || s.mkdirSync(n, { recursive: !0 });
  const r = await Q();
  if (r.length === 0) return { success: !1, error: "无法获取模型文件列表" };
  const h = r.reduce((c, m) => c + m.size, 0);
  let d = 0;
  for (const c of r) {
    if (g) return { success: !1, error: "用户取消" };
    const m = i.join(n, c.name), a = A + "/resolve/master/" + encodeURIComponent(c.name), o = await V(a, m, e, c.name);
    if (!o.success) return o;
    d++, w(e, {
      phase: "downloading",
      label: c.name,
      downloaded: d,
      total: r.length,
      percent: Math.round(d / r.length * 100)
    });
  }
  return w(e, {
    phase: "downloading",
    label: "模型下载完成",
    downloaded: h,
    total: h,
    percent: 100
  }), { success: !0 };
}
async function Q() {
  return new Promise((e) => {
    const n = A + "/files?Revision=master";
    C.get(n, { headers: { "User-Agent": "VoxAeterna/1.0" } }, (h) => {
      let d = "";
      h.on("data", (c) => {
        d += c.toString("utf-8");
      }), h.on("end", () => {
        var c;
        try {
          const a = (((c = JSON.parse(d).Data) == null ? void 0 : c.Files) || []).filter((o) => o.Name && /\.(pth|ckpt)$|profiles\.json/.test(o.Name)).map((o) => ({ name: o.Name, size: o.Size || 0 }));
          e(a);
        } catch {
          e([]);
        }
      });
    }).on("error", () => e([])).setTimeout(15e3, () => e([]));
  });
}
M(import.meta.url);
const v = i.dirname(N(import.meta.url));
process.env.APP_ROOT = i.join(v, "..");
const $ = process.env.VITE_DEV_SERVER_URL, me = i.join(process.env.APP_ROOT, "dist-electron"), F = i.join(process.env.APP_ROOT, "dist");
process.env.VITE_PUBLIC = $ ? i.join(process.env.APP_ROOT, "public") : F;
let t;
function E() {
  return l.isPackaged ? process.resourcesPath : i.resolve(v, "..", "..");
}
function Z() {
  if (l.isPackaged) {
    const n = i.join(i.dirname(process.resourcesPath), "python", "python.exe");
    if (s.existsSync(n)) return n;
    const r = b();
    return s.existsSync(r) ? r : n;
  }
  const e = i.join(E(), "venv", "Scripts", "python.exe");
  return s.existsSync(e) ? e : "python";
}
const x = E(), f = Z();
let D = null, k = null;
function j(e, n) {
  var m, a;
  const r = i.join(l.getPath("userData"), "backend.log");
  if (s.appendFileSync(r, `[${(/* @__PURE__ */ new Date()).toISOString()}] spawnBackend: ${e} module=${n} python=${f} cwd=${x}
`), !s.existsSync(f)) {
    const o = `[${(/* @__PURE__ */ new Date()).toISOString()}] PYTHON_EXE NOT FOUND: ${f}`;
    return s.appendFileSync(r, o + `
`), console.error("[VoxAeterna] " + o), _("cmd", ["/c", "echo Python runtime not found"], { stdio: "pipe", windowsHide: !0 });
  }
  const d = ["-c", `import sys, os; _sp = os.path.join(os.path.dirname(sys.executable), 'Lib', 'site-packages'); os.path.isdir(_sp) and _sp not in sys.path and sys.path.insert(0, _sp); import sys; sys.path.insert(0, r"${x}"); import runpy; runpy.run_module("${n}", run_name="__main__")`];
  console.log(`[VoxAeterna] start ${e}: ${f}`);
  const c = _(f, d, { cwd: x, stdio: "pipe", windowsHide: !0 });
  return (m = c.stdout) == null || m.on("data", (o) => {
    const u = o.toString().trim();
    console.log(`[${e}] ${u}`), s.appendFileSync(r, `[${e}] ${u}
`);
  }), (a = c.stderr) == null || a.on("data", (o) => {
    const u = o.toString().trim();
    console.error(`[${e}] ${u}`), s.appendFileSync(r, `[${e} stderr] ${u}
`);
  }), c.on("error", (o) => {
    console.error(`[${e}] error:`, o.message), s.appendFileSync(r, `[${(/* @__PURE__ */ new Date()).toISOString()}] ${e} error: ${o.message}
`);
  }), c.on("exit", (o, u) => {
    console.log(`[${e}] exit code=${o} signal=${u}`), s.appendFileSync(r, `[${(/* @__PURE__ */ new Date()).toISOString()}] ${e} exit: code=${o} signal=${u}
`);
  }), c;
}
function ee() {
  D = j("Inference", "backend.app.main"), k = j("Cloud", "cloud.main");
}
function ne() {
  for (const [e, n] of [["Inference", D], ["Cloud", k]])
    n && !n.killed && (console.log(`[VoxAeterna] stop ${e}...`), n.kill(), setTimeout(() => {
      n.killed || n.kill("SIGKILL");
    }, 5e3));
  D = null, k = null;
}
p.handle("env-setup:check", async () => {
  const e = s.existsSync(f), n = X();
  return l.isPackaged ? { python: e, pythonPath: f, gpu: n, deps: { ok: e, missing: e ? [] : ["Python runtime not found"] } } : { python: e, pythonPath: f, gpu: n, deps: { ok: !0, missing: [] } };
});
p.handle("env-setup:check-models", async () => Y());
p.handle("env-setup:download-models", async () => K(t));
p.handle("env-setup:cancel", async () => (G(), { message: "ok" }));
p.handle("env-setup:restart", async () => {
  l.relaunch(), l.exit(0);
});
p.handle("env-setup:check-torch", async () => !0);
p.handle("env-setup:torch-guide", async () => ({ cmd: "", size: "" }));
p.handle("env-setup:download-python", async () => ({ success: !1, error: "extract python-runtime.zip to app install dir/python/" }));
p.handle("env-setup:install", async () => ({ success: !1, error: "deps pre-installed in runtime zip" }));
function U() {
  const e = l.isPackaged ? i.join(process.resourcesPath, "favicon.ico") : i.join(E(), "favicon.ico");
  t = new T({ icon: e, frame: !1, titleBarStyle: "hidden", backgroundColor: "#0D0D0C", webPreferences: { preload: i.join(v, "preload.mjs") } }), t.webContents.on("did-finish-load", () => t == null ? void 0 : t.webContents.send("main-process-message", (/* @__PURE__ */ new Date()).toLocaleString())), $ ? t.loadURL($) : t.loadFile(i.join(F, "index.html"));
}
l.on("window-all-closed", () => {
  process.platform !== "darwin" && (l.quit(), t = null);
});
l.on("activate", () => {
  T.getAllWindows().length === 0 && U();
});
function te() {
  const e = l.getPath("userData"), n = i.join(e, ".device_fingerprint");
  try {
    if (s.existsSync(n)) return s.readFileSync(n, "utf-8").trim();
    const r = P.randomUUID();
    return s.writeFileSync(n, r, "utf-8"), r;
  } catch {
    try {
      return P.createHash("sha256").update(l.getPath("home")).digest("hex").slice(0, 32);
    } catch {
      return P.randomUUID();
    }
  }
}
p.handle("get-device-fingerprint", () => te());
p.handle("window-minimize", () => t == null ? void 0 : t.minimize());
p.handle("window-maximize", () => {
  t != null && t.isMaximized() ? t.unmaximize() : t == null || t.maximize();
});
p.handle("window-close", () => t == null ? void 0 : t.close());
p.handle("window-is-maximized", () => (t == null ? void 0 : t.isMaximized()) ?? !1);
p.handle("get-app-version", () => l.getVersion());
p.handle("open-external-url", (e, n) => L.openExternal(n));
function oe() {
  t == null || t.on("maximize", () => t == null ? void 0 : t.webContents.send("window-maximized", !0)), t == null || t.on("unmaximize", () => t == null ? void 0 : t.webContents.send("window-maximized", !1));
}
l.whenReady().then(() => {
  ee(), U(), oe();
});
l.on("will-quit", () => ne());
export {
  me as MAIN_DIST,
  F as RENDERER_DIST,
  $ as VITE_DEV_SERVER_URL
};
