<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const canvasRef = ref<HTMLCanvasElement | null>(null)
let animationId = 0
let mouseX = -1000
let mouseY = -1000
let targetMouseX = -1000
let targetMouseY = -1000

const LINE_GAP = 44       // 线间距（横竖一致）
const GLOW_R = 88         // 光波影响半径 = 两个间隙
const BASE_A = 0.018      // 基础线透明度
const PEAK_A = 0.12       // 光波峰值透明度

function onMouseMove(e: MouseEvent) {
  targetMouseX = e.clientX
  targetMouseY = e.clientY
}

function onMouseLeave() {
  targetMouseX = -1000
  targetMouseY = -1000
}

function isDarkMode(): boolean {
  return document.documentElement.getAttribute('data-theme') !== 'light'
}

function draw() {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const dark = isDarkMode()
  const lineR = dark ? 255 : 0
  const lineG = dark ? 255 : 0
  const lineB = dark ? 255 : 0

  const dpr = window.devicePixelRatio || 1
  const w = window.innerWidth
  const h = window.innerHeight

  if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
    canvas.width = w * dpr
    canvas.height = h * dpr
    canvas.style.width = w + 'px'
    canvas.style.height = h + 'px'
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

  // 平滑追踪鼠标（lerp）
  mouseX += (targetMouseX - mouseX) * 0.1
  mouseY += (targetMouseY - mouseY) * 0.1

  ctx.clearRect(0, 0, w, h)

  const totalH = Math.ceil(h / LINE_GAP)
  const totalW = Math.ceil(w / LINE_GAP)

  // ── 横线 ──
  for (let i = 0; i <= totalH; i++) {
    const y = i * LINE_GAP
    const dy = Math.abs(y - mouseY)

    // 基础线
    ctx.strokeStyle = `rgba(${lineR}, ${lineG}, ${lineB}, ${BASE_A})`
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(w, y)
    ctx.stroke()

    if (dy < GLOW_R) {
      const t = dy / GLOW_R
      const intensity = Math.cos(t * Math.PI / 2) * Math.pow(1 - t, 0.6)
      const alpha = PEAK_A * intensity
      if (alpha >= 0.008) {
        const dx = mouseX
        const xRatio = 1 - Math.abs(dx - w / 2) / (w / 2) * 0.2

        ctx.strokeStyle = `rgba(124, 252, 0, ${alpha * 0.35 * xRatio})`
        ctx.lineWidth = 3
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke()

        ctx.strokeStyle = `rgba(124, 252, 0, ${alpha * 0.55 * xRatio})`
        ctx.lineWidth = 1.5
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke()

        ctx.strokeStyle = `rgba(180, 255, 80, ${alpha * 0.8 * xRatio})`
        ctx.lineWidth = 1
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke()
      }
    }
  }

  // ── 竖线 ──
  for (let i = 0; i <= totalW; i++) {
    const x = i * LINE_GAP
    const dx = Math.abs(x - mouseX)

    // 基础线
    ctx.strokeStyle = `rgba(${lineR}, ${lineG}, ${lineB}, ${BASE_A})`
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(x, 0)
    ctx.lineTo(x, h)
    ctx.stroke()

    if (dx < GLOW_R) {
      const t = dx / GLOW_R
      const intensity = Math.cos(t * Math.PI / 2) * Math.pow(1 - t, 0.6)
      const alpha = PEAK_A * intensity
      if (alpha >= 0.008) {
        const yRatio = 1 - Math.abs(mouseY - h / 2) / (h / 2) * 0.2

        ctx.strokeStyle = `rgba(124, 252, 0, ${alpha * 0.35 * yRatio})`
        ctx.lineWidth = 3
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke()

        ctx.strokeStyle = `rgba(124, 252, 0, ${alpha * 0.55 * yRatio})`
        ctx.lineWidth = 1.5
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke()

        ctx.strokeStyle = `rgba(180, 255, 80, ${alpha * 0.8 * yRatio})`
        ctx.lineWidth = 1
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke()
      }
    }
  }

  animationId = requestAnimationFrame(draw)
}

onMounted(() => {
  window.addEventListener('mousemove', onMouseMove, { passive: true })
  window.addEventListener('mouseleave', onMouseLeave)
  animationId = requestAnimationFrame(draw)
})

onUnmounted(() => {
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseleave', onMouseLeave)
  cancelAnimationFrame(animationId)
})
</script>

<template>
  <canvas ref="canvasRef" class="bg-wave"></canvas>
</template>

<style scoped>
.bg-wave {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}
</style>
