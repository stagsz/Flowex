// k6 shared configuration for Flowex load tests
// https://k6.io/docs/

export const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
export const API_PREFIX = '/api/v1';

// Test thresholds based on spec requirements
export const thresholds = {
  // HTTP request duration
  http_req_duration: ['p(95)<500', 'p(99)<1000'], // 95th < 500ms, 99th < 1s

  // Error rate
  http_req_failed: ['rate<0.01'], // <1% error rate

  // Specific endpoint thresholds
  'http_req_duration{endpoint:health}': ['p(95)<100'],
  'http_req_duration{endpoint:drawings_list}': ['p(95)<500'],
  'http_req_duration{endpoint:drawing_get}': ['p(95)<300'],
  'http_req_duration{endpoint:export_status}': ['p(95)<200'],
};

// Load profiles
export const profiles = {
  // Smoke test - minimal load to verify functionality
  smoke: {
    vus: 1,
    duration: '30s',
  },

  // Load test - normal expected load
  load: {
    stages: [
      { duration: '1m', target: 10 },  // Ramp up
      { duration: '3m', target: 10 },  // Stay at 10 users
      { duration: '1m', target: 0 },   // Ramp down
    ],
  },

  // Stress test - find breaking point
  stress: {
    stages: [
      { duration: '2m', target: 10 },
      { duration: '5m', target: 20 },
      { duration: '2m', target: 30 },
      { duration: '5m', target: 40 },
      { duration: '2m', target: 50 },
      { duration: '5m', target: 0 },
    ],
  },

  // Spike test - sudden load increase
  spike: {
    stages: [
      { duration: '30s', target: 5 },
      { duration: '1m', target: 50 },  // Spike
      { duration: '30s', target: 5 },
      { duration: '1m', target: 0 },
    ],
  },

  // Soak test - extended duration
  soak: {
    stages: [
      { duration: '2m', target: 10 },
      { duration: '30m', target: 10 },
      { duration: '2m', target: 0 },
    ],
  },
};

// Helper to get test options based on profile
export function getOptions(profileName = 'smoke') {
  const profile = profiles[profileName] || profiles.smoke;

  return {
    ...profile,
    thresholds,
    tags: {
      profile: profileName,
    },
  };
}

// Simulated auth token for testing (replace with real token in CI)
export function getAuthHeaders() {
  const token = __ENV.AUTH_TOKEN || 'test-token';
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
}
