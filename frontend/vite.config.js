import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Static app configuration - No backend proxy
export default defineConfig({
  plugins: [react()],
  base: '/xmlconverter/',
  server: {
    port: 4203,
    headers: {
      'Cache-Control': 'no-store, no-cache, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0',
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
