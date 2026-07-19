import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      // 静态资源
      '/uploads': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // AI / RAG / 计划库 / 对话历史 — FastAPI 直接服务（无 Java 中间层）
      '/api/ai': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/rag': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/plans': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/orchestrator': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/conversations': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
