import { defineConfig, type Plugin } from 'vite'
import path from 'path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'

function redirectMocks(): Plugin {
  const storeTarget = path.resolve(__dirname, 'src/app/store/apiEngagementStore.ts')
  const dataTarget = path.resolve(__dirname, 'src/app/data/apiResults.ts')

  return {
    name: 'redirect-mocks-to-api',
    enforce: 'pre',
    resolveId(source, importer) {
      if (!importer) return null
      // Skip if the importer is already one of our replacement files
      if (importer.includes('apiEngagementStore') || importer.includes('apiResults')) return null

      if (source.endsWith('store/engagementStore') || source.endsWith('store\\engagementStore')) {
        return storeTarget
      }
      if (source.endsWith('data/mockResults') || source.endsWith('data\\mockResults')) {
        return dataTarget
      }
      return null
    },
  }
}

export default defineConfig({
  plugins: [
    redirectMocks(),
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },

  // File types to support raw imports. Never add .css, .tsx, or .ts files to this.
  assetsInclude: ['**/*.svg', '**/*.csv'],

  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
