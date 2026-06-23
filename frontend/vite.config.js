import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      // Sin rewrite: nginx en producción ya espera el prefijo /api y lo
      // saca él mismo antes de mandarlo a la API — si lo sacamos acá también,
      // la request le llega a la raíz, que ahora la sirve el frontend, no la API.
      '/api': {
        target: 'https://soagmr.mooo.com',
        changeOrigin: true,
      },
    },
  },
})
