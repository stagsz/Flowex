// Lighthouse CI configuration for Flowex frontend
// https://github.com/GoogleChrome/lighthouse-ci

module.exports = {
  ci: {
    collect: {
      // URLs to test (can be overridden with --url)
      url: [
        'http://localhost:5173/',
        'http://localhost:5173/login',
        'http://localhost:5173/dashboard',
      ],
      // Number of runs per URL
      numberOfRuns: 3,
      // Start command for dev server
      startServerCommand: 'npm run dev',
      // Wait for server to be ready
      startServerReadyPattern: 'ready in',
      startServerReadyTimeout: 30000,
      // Chrome flags
      settings: {
        chromeFlags: '--no-sandbox --disable-gpu --headless',
        // Throttling preset
        preset: 'desktop',
        // Skip audits that require auth
        skipAudits: ['uses-http2'],
      },
    },
    assert: {
      // Performance budgets based on spec requirements
      assertions: {
        // Core Web Vitals
        'categories:performance': ['warn', { minScore: 0.8 }],
        'categories:accessibility': ['error', { minScore: 0.9 }],
        'categories:best-practices': ['warn', { minScore: 0.9 }],
        'categories:seo': ['warn', { minScore: 0.8 }],

        // Specific metrics (spec: initial load < 3 seconds)
        'first-contentful-paint': ['warn', { maxNumericValue: 2000 }],
        'largest-contentful-paint': ['error', { maxNumericValue: 3000 }],
        'cumulative-layout-shift': ['warn', { maxNumericValue: 0.1 }],
        'total-blocking-time': ['warn', { maxNumericValue: 300 }],
        'interactive': ['warn', { maxNumericValue: 3500 }],

        // Resource hints
        'uses-rel-preconnect': 'off',
        'uses-rel-preload': 'off',

        // Bundle size (keep JS under 500KB initial)
        'total-byte-weight': ['warn', { maxNumericValue: 1500000 }],

        // Render blocking resources
        'render-blocking-resources': ['warn', { maxLength: 2 }],
      },
    },
    upload: {
      // Upload to temporary public storage (for CI visibility)
      target: 'temporary-public-storage',
    },
  },
};
