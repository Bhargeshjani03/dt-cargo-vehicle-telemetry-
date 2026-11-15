import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  root: resolve(projectRoot, 'client'),
  publicDir: resolve(projectRoot, 'static'),
  plugins: [react()],
  build: {
    outDir: resolve(projectRoot, 'client/dist'),
    emptyOutDir: true,
    sourcemap: false,
  },
});
