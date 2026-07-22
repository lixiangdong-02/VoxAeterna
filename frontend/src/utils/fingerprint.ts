/** 设备指纹工具 —— 用于试用次数追踪 */

export async function getDeviceFingerprint(): Promise<string> {
  // Electron 环境
  if ((window as any).deviceFingerprint?.get) {
    return (window as any).deviceFingerprint.get()
  }
  // 浏览器降级：用 localStorage 持久化一个随机 fingerprint
  const key = 'vox_device_fingerprint'
  let fp = localStorage.getItem(key)
  if (!fp) {
    fp = crypto.randomUUID()
    localStorage.setItem(key, fp)
  }
  return fp
}
