import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import UnoCSS from 'unocss/vite'

export default defineConfig({
  base: './',
  plugins: [vue(), UnoCSS()],
  build: {
    outDir: 'dist'
  },
  server: {
    // 开发服务器代理配置 - 将/api请求代理到后端
    proxy: {
      '/api': {
        target: `http://localhost:${process.env.BACKEND_PORT || 8000}`,  // 后端地址
        changeOrigin: true  // 修改Origin为目标地址
      }
    }
  }
})
