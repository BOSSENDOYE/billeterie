import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: true,
    // Le backend Django tourne sur :8000 (API, admin Django et ses fichiers statiques)
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/django-admin': 'http://127.0.0.1:8000',
      '/static': 'http://127.0.0.1:8000',
    },
  },
})
