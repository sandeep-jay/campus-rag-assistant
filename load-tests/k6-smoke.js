/**
 * Minimal smoke load test (~5 concurrent virtual users, ~45s).
 * Validates login-json cookie flow, CSRF header, session create, and chat send.
 *
 * Run (requires backend up + seeded users from users.json):
 *   BASE_URL=http://127.0.0.1:8000 k6 run load-tests/k6-smoke.js
 */
import http from "k6/http";
import { check, sleep } from "k6";
import { SharedArray } from "k6/data";
import exec from "k6/execution";

const baseUrl = __ENV.BASE_URL || "http://127.0.0.1:8000";

const users = new SharedArray("users", () => {
  const parsed = JSON.parse(open("./users.json"));
  return parsed.users;
});

export const options = {
  scenarios: {
    smoke_5vus: {
      executor: "constant-vus",
      vus: 5,
      duration: "45s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.15"],
    "checks{phase:auth}": ["rate>0.95"],
    "checks{phase:chat}": ["rate>0.90"],
    // Latency by phase: tight auth/session (app+bcrypt); chat bound by LLM+RAG + provider retries
    "http_req_duration{phase:auth}": ["p(95)<8000"],
    "http_req_duration{phase:session}": ["p(95)<5000"],
    "http_req_duration{phase:chat}": ["p(95)<25000"],
  },
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
  const cookie =
    res.cookies.access_token && res.cookies.access_token[0] && res.cookies.access_token[0].value;
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
    JSON.stringify({ title: `Smoke session vu=${__VU}` }),
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
  const messagePayload = JSON.stringify({
    content: `Smoke prompt vu=${__VU}`,
    session_id: session.id,
  });
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
