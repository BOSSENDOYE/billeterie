import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: true,
    // Le backend Django tourne sur :8000 (API, admin Django et ses fichiers statiques).
    // API_PROXY permet de viser un autre port, ex. API_PROXY=http://127.0.0.1:8002
    proxy: {
      '/api': process.env.API_PROXY || 'http://127.0.0.1:8000',
      '/django-admin': process.env.API_PROXY || 'http://127.0.0.1:8000',
      '/static': process.env.API_PROXY || 'http://127.0.0.1:8000',
    },
  },
})
