import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      // 静态资源（头像等）
      '/uploads': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // AI + RAG 接口（FastAPI 直接服务）
      '/api/ai': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // 计划预览 HTML 文件
      '/orchestrator': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
