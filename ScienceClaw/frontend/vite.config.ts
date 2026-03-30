import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import monacoEditorPlugin from 'vite-plugin-monaco-editor';
import { resolve } from 'path';

const CORE_PACKAGES = new Set([
  'vue',
  'vue-router',
  'vue-i18n',
  'axios',
  'mitt',
  '@microsoft/fetch-event-source',
]);

const UI_PACKAGES = new Set([
  '@vueuse/core',
  'lucide-vue-next',
  'reka-ui',
  'class-variance-authority',
  'clsx',
  'tailwind-merge',
  'tw-animate-css',
  'framer-motion',
]);

const MARKDOWN_PACKAGES = new Set([
  'marked',
  'highlight.js',
  'katex',
  'dompurify',
]);

const TERMINAL_PACKAGES = new Set([
  '@novnc/novnc',
  '@xterm/addon-fit',
  '@xterm/xterm',
]);

const DIAGRAM_PACKAGES = new Set([
  'mermaid',
  'cytoscape',
  'dagre',
  'dagre-d3-es',
  'elkjs',
  'khroma',
  'layout-base',
  'cose-base',
]);

function getPackageName(id: string): string | null {
  const nodeModulesIndex = id.lastIndexOf('node_modules/');
  if (nodeModulesIndex === -1) {
    return null;
  }

  const packagePath = id.slice(nodeModulesIndex + 'node_modules/'.length);
  const segments = packagePath.split('/');
  if (!segments.length) {
    return null;
  }

  return segments[0].startsWith('@')
    ? `${segments[0]}/${segments[1] ?? ''}`
    : segments[0];
}

function getManualChunk(id: string): string | undefined {
  if (!id.includes('node_modules/')) {
    return undefined;
  }

  const packageName = getPackageName(id);
  if (!packageName) {
    return undefined;
  }

  if (packageName === 'monaco-editor') {
    return 'vendor-monaco';
  }

  if (
    DIAGRAM_PACKAGES.has(packageName) ||
    packageName.startsWith('d3-') ||
    packageName === 'd3'
  ) {
    return 'vendor-diagrams';
  }

  if (MARKDOWN_PACKAGES.has(packageName)) {
    return 'vendor-markdown';
  }

  if (TERMINAL_PACKAGES.has(packageName)) {
    return 'vendor-terminal';
  }

  if (UI_PACKAGES.has(packageName)) {
    return 'vendor-ui';
  }

  if (CORE_PACKAGES.has(packageName)) {
    return 'vendor-core';
  }

  return 'vendor-misc';
}

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    (monacoEditorPlugin as any).default({})
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  optimizeDeps: {
    exclude: ['lucide-vue-next'],
  },
  build: {
    // The remaining heavy chunks are isolated lazy vendor bundles
    // (Monaco, diagramming, markdown tooling), not the initial app shell.
    chunkSizeWarningLimit: 2500,
    rollupOptions: {
      output: {
        manualChunks: getManualChunk,
      },
    },
  },
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.BACKEND_URL || 'http://localhost:12001',
        changeOrigin: true,
        ws: true,
      },
      '/task-service': {
        target: process.env.TASK_SERVICE_URL || 'http://localhost:12002',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/task-service/, ''),
      },
    },
  },
}); 
