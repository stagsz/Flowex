import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            '@': path.resolve(__dirname, './src'),
        },
    },
    server: {
        port: 5173,
        proxy: {
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
        },
    },
    build: {
        rollupOptions: {
            output: {
                manualChunks: {
                    // Core React vendor chunk
                    'vendor-react': ['react', 'react-dom', 'react-router-dom'],
                    // UI library chunk
                    'vendor-ui': [
                        '@radix-ui/react-dialog',
                        '@radix-ui/react-dropdown-menu',
                        '@radix-ui/react-select',
                        '@radix-ui/react-tabs',
                        '@radix-ui/react-tooltip',
                        '@radix-ui/react-progress',
                        '@radix-ui/react-checkbox',
                        '@radix-ui/react-label',
                        '@radix-ui/react-slot',
                    ],
                    // State management and utilities
                    'vendor-utils': ['zustand', 'clsx', 'tailwind-merge', 'class-variance-authority'],
                    // Monitoring/analytics
                    'vendor-monitoring': ['@sentry/react'],
                },
            },
        },
    },
});
