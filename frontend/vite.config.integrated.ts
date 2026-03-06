/**
 * Integrated Vite config — extends the base config with:
 *   1. API proxy to the FastAPI backend on localhost:8000
 *   2. Module aliases that redirect mock data / mock store imports
 *      to their API-connected replacements.
 *
 * Usage:
 *   npx vite --config vite.config.integrated.ts
 *
 * The original vite.config.ts is NOT modified.
 */

import { defineConfig } from 'vite';
import path from 'path';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: [
      { find: '@', replacement: path.resolve(__dirname, './src') },
      {
        find: /[/\\]store[/\\]engagementStore$/,
        replacement: path.resolve(__dirname, 'src/app/store/apiEngagementStore'),
      },
      {
        find: /[/\\]data[/\\]mockResults$/,
        replacement: path.resolve(__dirname, 'src/app/data/apiResults'),
      },
    ],
  },
  assetsInclude: ['**/*.svg', '**/*.csv'],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
