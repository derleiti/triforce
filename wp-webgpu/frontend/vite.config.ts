import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    rollupOptions: {
      input: 'src/main.ts',
      output: { entryFileNames: 'assets/main.js', assetFileNames: 'assets/[name][extname]' }
    }
  }
});