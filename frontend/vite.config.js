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
                manualChunks: function (id) {
                    // Core React vendor chunk
                    if (id.includes('node_modules/react/') ||
                        id.includes('node_modules/react-dom/') ||
                        id.includes('node_modules/react-router')) {
                        return 'vendor-react';
                    }
                    // Radix UI components chunk
                    if (id.includes('node_modules/@radix-ui/')) {
                        return 'vendor-ui';
                    }
                    // State management and utilities
                    if (id.includes('node_modules/zustand/') ||
                        id.includes('node_modules/clsx/') ||
                        id.includes('node_modules/tailwind-merge/') ||
                        id.includes('node_modules/class-variance-authority/')) {
                        return 'vendor-utils';
                    }
                    // Monitoring/analytics
                    if (id.includes('node_modules/@sentry/')) {
                        return 'vendor-monitoring';
                    }
                },
            },
        },
    },
});
