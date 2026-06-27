import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import UnoCSS from 'unocss/vite'
import { realpathSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const frontendRoot = realpathSync(fileURLToPath(new URL('./src/frontend', import.meta.url)))

export default defineConfig({
  root: frontendRoot,
  base: './',
  plugins: [vue(), UnoCSS()],
  build: {
    outDir: 'dist'
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
