// k6 load tests for Flowex API endpoints
// Run: k6 run perf/k6/api-endpoints.js
// With profile: k6 run -e PROFILE=load perf/k6/api-endpoints.js

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';
import { BASE_URL, API_PREFIX, getOptions, getAuthHeaders } from './config.js';

// Custom metrics
const errorRate = new Rate('errors');
const healthCheckDuration = new Trend('health_check_duration');
const drawingsListDuration = new Trend('drawings_list_duration');
const drawingGetDuration = new Trend('drawing_get_duration');
const exportStatusDuration = new Trend('export_status_duration');

// Get options from profile
const profileName = __ENV.PROFILE || 'smoke';
export const options = getOptions(profileName);

// Test data (would come from environment in real tests)
const TEST_PROJECT_ID = __ENV.TEST_PROJECT_ID || '00000000-0000-0000-0000-000000000001';
const TEST_DRAWING_ID = __ENV.TEST_DRAWING_ID || '00000000-0000-0000-0000-000000000001';

export default function () {
  const headers = getAuthHeaders();

  // Health check endpoint
  group('Health Check', function () {
    const res = http.get(`${BASE_URL}/health`, {
      tags: { endpoint: 'health' },
    });

    healthCheckDuration.add(res.timings.duration);

    const success = check(res, {
      'health check status is 200': (r) => r.status === 200,
      'health check response time < 100ms': (r) => r.timings.duration < 100,
    });

    errorRate.add(!success);
  });

  sleep(0.5);

  // Drawings list endpoint
  group('List Drawings', function () {
    const res = http.get(
      `${BASE_URL}${API_PREFIX}/drawings/project/${TEST_PROJECT_ID}?skip=0&limit=100`,
      {
        headers,
        tags: { endpoint: 'drawings_list' },
      }
    );

    drawingsListDuration.add(res.timings.duration);

    const success = check(res, {
      'drawings list status is 200 or 401/403': (r) =>
        r.status === 200 || r.status === 401 || r.status === 403 || r.status === 404,
      'drawings list response time < 500ms': (r) => r.timings.duration < 500,
    });

    errorRate.add(!success);
  });

  sleep(0.5);

  // Get single drawing endpoint
  group('Get Drawing', function () {
    const res = http.get(`${BASE_URL}${API_PREFIX}/drawings/${TEST_DRAWING_ID}`, {
      headers,
      tags: { endpoint: 'drawing_get' },
    });

    drawingGetDuration.add(res.timings.duration);

    const success = check(res, {
      'get drawing status is 200 or 401/403/404': (r) =>
        r.status === 200 || r.status === 401 || r.status === 403 || r.status === 404,
      'get drawing response time < 300ms': (r) => r.timings.duration < 300,
    });

    errorRate.add(!success);
  });

  sleep(0.5);

  // Export status endpoint (simulated job ID)
  group('Export Status', function () {
    const jobId = '00000000-0000-0000-0000-000000000001';
    const res = http.get(`${BASE_URL}${API_PREFIX}/exports/jobs/${jobId}/status`, {
      headers,
      tags: { endpoint: 'export_status' },
    });

    exportStatusDuration.add(res.timings.duration);

    const success = check(res, {
      'export status returns valid response': (r) =>
        r.status === 200 || r.status === 401 || r.status === 403 || r.status === 404,
      'export status response time < 200ms': (r) => r.timings.duration < 200,
    });

    errorRate.add(!success);
  });

  sleep(1);
}

// Setup - runs once before tests
export function setup() {
  console.log(`Running ${profileName} test against ${BASE_URL}`);
  console.log(`Test project ID: ${TEST_PROJECT_ID}`);
  console.log(`Test drawing ID: ${TEST_DRAWING_ID}`);

  // Verify API is reachable
  const res = http.get(`${BASE_URL}/health`);
  if (res.status !== 200) {
    console.error(`API health check failed: ${res.status}`);
  }

  return { startTime: new Date().toISOString() };
}

// Teardown - runs once after tests
export function teardown(data) {
  console.log(`Test completed. Started at: ${data.startTime}`);
}

// Summary handler
export function handleSummary(data) {
  const summary = {
    timestamp: new Date().toISOString(),
    profile: profileName,
    metrics: {
      http_reqs: data.metrics.http_reqs?.values?.count || 0,
      http_req_duration_avg: data.metrics.http_req_duration?.values?.avg || 0,
      http_req_duration_p95: data.metrics.http_req_duration?.values?.['p(95)'] || 0,
      http_req_failed: data.metrics.http_req_failed?.values?.rate || 0,
      errors: data.metrics.errors?.values?.rate || 0,
    },
    thresholds_passed: Object.entries(data.root_group?.checks || {}).every(
      ([_, v]) => v.passes === v.fails + v.passes
    ),
  };

  return {
    'perf/k6/results/api-summary.json': JSON.stringify(summary, null, 2),
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
  };
}

// Text summary helper
function textSummary(data, options) {
  const indent = options.indent || '';
  const lines = [
    '',
    `${indent}Flowex API Load Test Results`,
    `${indent}============================`,
    `${indent}Profile: ${profileName}`,
    `${indent}`,
    `${indent}HTTP Requests:`,
    `${indent}  Total: ${data.metrics.http_reqs?.values?.count || 0}`,
    `${indent}  Failed: ${(data.metrics.http_req_failed?.values?.rate * 100 || 0).toFixed(2)}%`,
    `${indent}`,
    `${indent}Response Times:`,
    `${indent}  avg: ${(data.metrics.http_req_duration?.values?.avg || 0).toFixed(2)}ms`,
    `${indent}  p(95): ${(data.metrics.http_req_duration?.values?.['p(95)'] || 0).toFixed(2)}ms`,
    `${indent}  p(99): ${(data.metrics.http_req_duration?.values?.['p(99)'] || 0).toFixed(2)}ms`,
    `${indent}`,
    `${indent}Custom Metrics:`,
    `${indent}  Health Check avg: ${(data.metrics.health_check_duration?.values?.avg || 0).toFixed(2)}ms`,
    `${indent}  Drawings List avg: ${(data.metrics.drawings_list_duration?.values?.avg || 0).toFixed(2)}ms`,
    `${indent}  Drawing Get avg: ${(data.metrics.drawing_get_duration?.values?.avg || 0).toFixed(2)}ms`,
    `${indent}  Export Status avg: ${(data.metrics.export_status_duration?.values?.avg || 0).toFixed(2)}ms`,
    '',
  ];

  return lines.join('\n');
}
