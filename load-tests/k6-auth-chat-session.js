/**
 * Full ramp load test (~100 VUs). After smoke passes, run this with same BASE_URL and seeded users.
 *
 * Latency thresholds:
 * - Default (`K6_LATENCY_PROFILE` unset or `live`): phase-split caps suited to real LLM+RAG (Azure, retries).
 * - `K6_LATENCY_PROFILE=mock`: strict global HTTP latency (sub-second p95) when the API uses mock/fast providers.
 *
 * Run:
 *   BASE_URL=http://127.0.0.1:8000 k6 run load-tests/k6-auth-chat-session.js
 *   K6_LATENCY_PROFILE=mock BASE_URL=... k6 run load-tests/k6-auth-chat-session.js
 */
import http from "k6/http";
import { check, sleep } from "k6";
import { SharedArray } from "k6/data";
import exec from "k6/execution";

const baseUrl = __ENV.BASE_URL || "http://127.0.0.1:8000";
const latencyProfile = (__ENV.K6_LATENCY_PROFILE || "live").toLowerCase();

const users = new SharedArray("users", () => {
  const parsed = JSON.parse(open("./users.json"));
  return parsed.users;
});

function buildThresholds() {
  const checks = {
    http_req_failed: ["rate<0.02"],
    "checks{phase:auth}": ["rate>0.99"],
    "checks{phase:chat}": ["rate>0.98"],
  };
  if (latencyProfile === "mock") {
    return {
      ...checks,
      http_req_duration: ["p(95)<1200", "p(99)<2500"],
    };
  }
  return {
    ...checks,
    // Live providers: same phase tags as smoke; chat cap slightly higher for 100-VU ramp + 429 retries
    "http_req_duration{phase:auth}": ["p(95)<8000"],
    "http_req_duration{phase:session}": ["p(95)<5000"],
    "http_req_duration{phase:chat}": ["p(95)<45000"],
  };
}

export const options = {
  scenarios: {
    steady_users: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "2m", target: 30 },
        { duration: "5m", target: 100 },
        { duration: "3m", target: 100 },
        { duration: "2m", target: 0 },
      ],
      gracefulRampDown: "30s",
    },
  },
  thresholds: buildThresholds(),
};

function assertLoadTestBackendOrAbort() {
  const allow = __ENV.K6_ALLOW_NON_TEST_BACKEND === "1";
  const res = http.get(`${baseUrl}/api/health`);
  if (res.status !== 200) {
    exec.test.abort(`Refusing load test: GET /api/health returned HTTP ${res.status}`);
  }
  let body;
  try {
    body = JSON.parse(res.body);
  } catch {
    exec.test.abort("Refusing load test: /api/health returned non-JSON body");
  }
  if (!allow && body.app_env !== "test") {
    exec.test.abort(
      `Refusing load test: app_env=${JSON.stringify(body.app_env)} environment=${JSON.stringify(body.environment)}. ` +
        "Start ./scripts/run-backend-loadtest.sh (APP_ENV=test + test DATABASE_URL). " +
        "Override intentionally with K6_ALLOW_NON_TEST_BACKEND=1."
    );
  }
}

export function setup() {
  assertLoadTestBackendOrAbort();
  return {};
}

function authAndGetSession(user) {
  const payload = JSON.stringify({ username: user.username, password: user.password });
  const res = http.post(`${baseUrl}/api/auth/login-json`, payload, {
    headers: { "Content-Type": "application/json" },
    tags: { phase: "auth" },
  });
  check(
    res,
    {
      "login status is 200": (r) => r.status === 200,
      "session cookie set": (r) => !!r.cookies.access_token,
    },
    { phase: "auth" }
  );
  const cookie = res.cookies.access_token && res.cookies.access_token[0] && res.cookies.access_token[0].value;
  let csrfToken;
  try {
    const body = res.json();
    csrfToken = body && body.csrf_token;
  } catch {
    csrfToken = undefined;
  }
  return { cookie, csrfToken };
}

export default function () {
  const user = users[(__VU - 1) % users.length];
  const sessionAuth = authAndGetSession(user);
  if (!sessionAuth.cookie || !sessionAuth.csrfToken) {
    sleep(1);
    return;
  }

  const sessionRes = http.post(
    `${baseUrl}/api/chat/sessions`,
    JSON.stringify({ title: `Load test session ${__VU}` }),
    {
      headers: {
        "Content-Type": "application/json",
        Cookie: `access_token=${sessionAuth.cookie}`,
        "X-CSRF-Token": sessionAuth.csrfToken,
      },
      tags: { phase: "session" },
    }
  );

  const sessionOk = check(sessionRes, {
    "session create status 200": (r) => r.status === 200,
  });
  if (!sessionOk) {
    sleep(1);
    return;
  }

  const session = sessionRes.json();
  const messagePayload = JSON.stringify({ content: `Load test prompt from vu=${__VU}`, session_id: session.id });
  const chatRes = http.post(`${baseUrl}/api/chat/chat`, messagePayload, {
    headers: {
      "Content-Type": "application/json",
      Cookie: `access_token=${sessionAuth.cookie}`,
      "X-CSRF-Token": sessionAuth.csrfToken,
    },
    tags: { phase: "chat" },
  });

  check(
    chatRes,
    {
      "chat status is 200": (r) => r.status === 200,
      "assistant message returned": (r) => {
        try {
          const body = r.json();
          return !!(body && body.assistant_message && body.assistant_message.content);
        } catch {
          return false;
        }
      },
    },
    { phase: "chat" }
  );

  sleep(1);
}
