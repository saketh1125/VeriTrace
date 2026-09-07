import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// @ts-expect-error vitest types resolve after install
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173 },
  test: { environment: 'jsdom', setupFiles: ['./src/test-setup.ts'] },
});
