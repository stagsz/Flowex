// k6 stress test for file upload endpoint
// Tests concurrent upload handling (spec requirement: 10 concurrent uploads)
// Run: k6 run perf/k6/upload-stress.js

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { BASE_URL, API_PREFIX, getAuthHeaders } from './config.js';

// Custom metrics for upload testing
const uploadDuration = new Trend('upload_duration');
const uploadSuccess = new Rate('upload_success');
const uploadErrors = new Counter('upload_errors');

// Upload stress test options
// Target: Handle 10 concurrent uploads per spec requirement
export const options = {
  scenarios: {
    // Ramp up to 10 concurrent uploaders
    upload_stress: {
      executor: 'ramping-vus',
      startVUs: 1,
      stages: [
        { duration: '30s', target: 5 },   // Warm up
        { duration: '1m', target: 10 },   // Target concurrent uploads
        { duration: '2m', target: 10 },   // Sustain
        { duration: '30s', target: 0 },   // Ramp down
      ],
      gracefulRampDown: '10s',
    },
  },
  thresholds: {
    // Upload should complete within 30 seconds for small files
    upload_duration: ['p(95)<30000'],
    // Success rate should be >95%
    upload_success: ['rate>0.95'],
    // Overall error rate
    http_req_failed: ['rate<0.05'],
  },
};

// Small test PDF content (minimal valid PDF)
const SMALL_PDF_CONTENT = `%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<< /Size 4 /Root 1 0 R >>
startxref
198
%%EOF`;

// Test project ID (must exist in test environment)
const TEST_PROJECT_ID = __ENV.TEST_PROJECT_ID || '00000000-0000-0000-0000-000000000001';

export default function () {
  const headers = getAuthHeaders();

  // Create multipart form data with small PDF
  const filename = `test-upload-${__VU}-${__ITER}.pdf`;
  const data = {
    file: http.file(SMALL_PDF_CONTENT, filename, 'application/pdf'),
  };

  // Upload file
  const uploadUrl = `${BASE_URL}${API_PREFIX}/drawings/upload/${TEST_PROJECT_ID}`;
  const res = http.post(uploadUrl, data, {
    headers: {
      'Authorization': headers['Authorization'],
      // Content-Type is set automatically for multipart
    },
    timeout: '60s',
    tags: { endpoint: 'upload' },
  });

  uploadDuration.add(res.timings.duration);

  const success = check(res, {
    'upload returns 201 or auth error': (r) =>
      r.status === 201 || r.status === 401 || r.status === 403 || r.status === 404,
    'upload completes within 30s': (r) => r.timings.duration < 30000,
  });

  if (success && res.status === 201) {
    uploadSuccess.add(1);

    // Parse response to verify structure
    try {
      const body = JSON.parse(res.body);
      check(body, {
        'response has drawing_id': (b) => b.id !== undefined,
        'response has status': (b) => b.status !== undefined,
      });
    } catch (e) {
      uploadErrors.add(1);
    }
  } else {
    uploadSuccess.add(0);
    if (res.status >= 500) {
      uploadErrors.add(1);
    }
  }

  // Small delay between uploads
  sleep(2);
}

export function setup() {
  console.log('Starting upload stress test');
  console.log(`Target: 10 concurrent uploads`);
  console.log(`Project ID: ${TEST_PROJECT_ID}`);

  // Verify API is reachable
  const res = http.get(`${BASE_URL}/health`);
  if (res.status !== 200) {
    console.error('API is not reachable');
  }

  return {};
}

export function handleSummary(data) {
  const summary = {
    test: 'upload-stress',
    timestamp: new Date().toISOString(),
    metrics: {
      total_uploads: data.metrics.http_reqs?.values?.count || 0,
      upload_duration_avg: data.metrics.upload_duration?.values?.avg || 0,
      upload_duration_p95: data.metrics.upload_duration?.values?.['p(95)'] || 0,
      upload_success_rate: data.metrics.upload_success?.values?.rate || 0,
      upload_errors: data.metrics.upload_errors?.values?.count || 0,
    },
  };

  return {
    'perf/k6/results/upload-stress-summary.json': JSON.stringify(summary, null, 2),
    stdout: JSON.stringify(summary, null, 2),
  };
}
