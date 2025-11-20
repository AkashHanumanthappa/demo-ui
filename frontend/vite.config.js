import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Static app configuration - No backend proxy
export default defineConfig({
  plugins: [react()],
  base: '/xmlconverter/',
  server: {
    port: 4202,
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
