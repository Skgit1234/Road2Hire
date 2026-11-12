import assert from "node:assert/strict";
import test from "node:test";
import { normalizeApiBaseUrl } from "../lib/api-config.ts";
import { checkBackendHealth } from "../lib/health-check.ts";

test("normalizes the API base URL by removing trailing slashes", () => {
  assert.equal(normalizeApiBaseUrl(" https://api.example.test/// "), "https://api.example.test");
});

test("accepts a healthy backend response and sends an unauthenticated GET", async () => {
  let requestedUrl;
  let requestedOptions;
  const result = await checkBackendHealth(async (url, options) => {
    requestedUrl = url;
    requestedOptions = options;
    return new Response(JSON.stringify({ status: "healthy" }), { status: 200 });
  });

  assert.deepEqual(result, { status: "healthy" });
  assert.match(requestedUrl, /\/health$/);
  assert.equal(requestedOptions.method, "GET");
  assert.equal(Object.hasOwn(requestedOptions, "headers"), false);
  assert.ok(requestedOptions.signal instanceof AbortSignal);
});

test("reports non-success HTTP responses without reading their bodies", async () => {
  await assert.rejects(
    checkBackendHealth(async () => new Response("private response details", { status: 503 })),
    { message: "The backend health check returned HTTP 503." },
  );
});

test("reports network failures with a safe connection message", async () => {
  await assert.rejects(
    checkBackendHealth(async () => { throw new TypeError("socket detail"); }),
    { message: /Could not connect to the backend/ },
  );
});

test("reports invalid JSON and unexpected response shapes", async (t) => {
  await t.test("invalid JSON", async () => {
    await assert.rejects(
      checkBackendHealth(async () => new Response("not json", { status: 200 })),
      { message: "The backend health check returned invalid JSON." },
    );
  });

  await t.test("unexpected shape", async () => {
    await assert.rejects(
      checkBackendHealth(async () => new Response(JSON.stringify({ status: "running" }), { status: 200 })),
      { message: "The backend health check returned an unexpected response." },
    );
  });
});
