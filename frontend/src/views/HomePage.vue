<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import gsap from 'gsap'

const router = useRouter()
const heroRef = ref<HTMLElement | null>(null)
const isHovering = ref(false)

onMounted(() => {
  if (!heroRef.value) return
  const tl = gsap.timeline({ defaults: { ease: 'power3.out' } })
  const children = heroRef.value.querySelectorAll('.hero-item')
  tl.fromTo(children, { opacity: 0, y: 28 }, { opacity: 1, y: 0, stagger: 0.12, duration: 0.8 })
})

function goWorkspace() {
  router.push('/workspace')
}
</script>

<template>
  <div class="home">
    <!-- 背景装饰：低频发光的球体 -->
    <div class="bg-orb"></div>
    <div class="bg-orb secondary"></div>
    <div class="bg-grid"></div>

    <div ref="heroRef" class="hero">
      <img src="/icon.png" alt="VoxAeterna" class="hero-logo hero-item" />
      <div class="hero-badge hero-item">GPT-SoVITS · V2 Pro Engine</div>
      <h1 class="hero-title hero-item">VoxAeterna</h1>
      <p class="hero-desc hero-item">
        本地 AI 语音工作站。上传声音模型，输入文字，即刻生成自然流畅的语音。
        支持中英混合合成，深色仪表盘界面，所见即所得。
      </p>
      <div class="hero-features hero-item">
        <div class="feature">
          <span class="feature-num">v2</span>
          <span class="feature-label">Pro 引擎</span>
        </div>
        <span class="feature-sep">·</span>
        <div class="feature">
          <span class="feature-num">本地</span>
          <span class="feature-label">离线推理</span>
        </div>
        <span class="feature-sep">·</span>
        <div class="feature">
          <span class="feature-num">波形</span>
          <span class="feature-label">可视化编辑</span>
        </div>
      </div>

      <button
        class="btn btn-primary btn-lg hero-cta hero-item"
        :class="{ hovering: isHovering }"
        @mouseenter="isHovering = true"
        @mouseleave="isHovering = false"
        @click="goWorkspace"
      >
        <span class="cta-icon">+</span>
        创建项目
      </button>
      <p class="hero-version hero-item">本地推理 · 需要 NVIDIA GPU · 首次加载约 30 秒</p>
    </div>
  </div>
</template>

<style scoped>
.home {
  height: 100%;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background: var(--c-bg);
}

/* ---- 背景：低频发光球体 ---- */
.bg-orb {
  position: absolute;
  width: 600px;
  height: 600px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(124, 252, 0, 0.06) 0%, transparent 70%);
  top: -10%;
  left: -5%;
  animation: orb-breathe 8s ease-in-out infinite;
}
.bg-orb.secondary {
  width: 400px;
  height: 400px;
  top: 60%;
  left: auto;
  right: -8%;
  animation-delay: 4s;
  opacity: 0.5;
}
@keyframes orb-breathe {
  0%, 100% { transform: scale(1); opacity: 0.6; }
  50% { transform: scale(1.2); opacity: 1; }
}

/* ---- 背景微网格 ---- */
.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px);
  background-size: 60px 60px;
  mask-image: radial-gradient(ellipse at center, black 30%, transparent 70%);
}

/* ---- Hero ---- */
.hero {
  position: relative;
  z-index: 1;
  text-align: center;
  max-width: 500px;
  padding: 48px 32px;
}

.hero-logo {
  width: 80px;
  height: 80px;
  margin-bottom: 24px;
  filter: drop-shadow(0 0 24px var(--c-accent-glow));
}

.hero-badge {
  display: inline-block;
  padding: 5px 16px;
  border-radius: 100px;
  background: rgba(124, 252, 0, 0.08);
  color: var(--c-accent);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 24px;
  border: 1px solid rgba(124, 252, 0, 0.15);
}

.hero-title {
  font-family: var(--font-display);
  font-size: 56px;
  font-weight: 700;
  line-height: 1.05;
  letter-spacing: -0.03em;
  color: var(--c-text);
  margin-bottom: 20px;
}

.hero-desc {
  font-size: 15px;
  line-height: 1.8;
  color: var(--c-text-secondary);
  margin-bottom: 32px;
}

.hero-features {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-bottom: 40px;
  font-size: 13px;
  color: var(--c-text-secondary);
}

.feature { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.feature-num {
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 600;
  color: var(--c-text);
}
.feature-label { font-size: 11px; color: var(--c-text-muted); }
.feature-sep { color: var(--c-text-muted); }

.hero-cta {
  margin-bottom: 16px;
  transition: all 0.4s var(--ease-out);
}
.hero-cta.hovering { transform: scale(1.04); }
.cta-icon {
  font-size: 18px;
  font-weight: 300;
  margin-right: 2px;
}

.hero-version {
  font-size: 11px;
  color: var(--c-text-muted);
  opacity: 0.5;
  letter-spacing: 0.03em;
}
</style>
