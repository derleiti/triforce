import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: __dirname,
  publicDir: false,
  build: {
    outDir: 'dist',
    assetsDir: '.',
    emptyOutDir: false,
    cssCodeSplit: false,
    sourcemap: false,
    minify: 'esbuild',
    rollupOptions: {
       input: {
         app: resolve(__dirname, 'assets/js/app.js'),
         colorMode: resolve(__dirname, 'assets/js/color-mode.js'),
         customizer: resolve(__dirname, 'assets/js/customizer.js'),
         'mobile-menu': resolve(__dirname, 'assets/js/mobile-menu.js'),
         webgpu: resolve(__dirname, 'assets/js/webgpu.js'),
         style: resolve(__dirname, 'assets/scss/style.scss')
       },
      output: {
        entryFileNames: '[name].js',
        assetFileNames: '[name][extname]'
      }
    }
  },
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: '',
        includePaths: [resolve(__dirname, 'assets/scss')]
      }
    }
  }
});
