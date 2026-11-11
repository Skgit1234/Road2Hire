import assert from "node:assert/strict";
import test from "node:test";
import {
  getCurrentProfile,
  loginUser,
  registerUser,
  updateCurrentProfile,
} from "../lib/api-client.ts";

test("register sends the backend request fields and parses the returned user", async () => {
  let request;
  const user = await registerUser({ name: "Riya Singh", email: "riya@example.com", password: "secret" }, async (url, options) => {
    request = { url, options };
    return Response.json({ id: 7, name: "Riya Singh", email: "riya@example.com" });
  });

  assert.equal(request.url.endsWith("/auth/register"), true);
  assert.equal(request.options.method, "POST");
  assert.deepEqual(JSON.parse(request.options.body), { name: "Riya Singh", email: "riya@example.com", password: "secret" });
  assert.deepEqual(user, { id: 7, name: "Riya Singh", email: "riya@example.com" });
});

test("login parses the backend bearer token response", async () => {
  let request;
  const result = await loginUser({ email: "riya@example.com", password: "secret" }, async (url, options) => {
    request = { url, options };
    return Response.json({ access_token: "test-token", token_type: "bearer" });
  });

  assert.equal(request.url.endsWith("/auth/login"), true);
  assert.deepEqual(JSON.parse(request.options.body), { email: "riya@example.com", password: "secret" });
  assert.deepEqual(result, { access_token: "test-token", token_type: "bearer" });
});

test("failed login surfaces FastAPI detail without exposing credentials", async () => {
  await assert.rejects(
    loginUser({ email: "riya@example.com", password: "private-password" }, async () =>
      Response.json({ detail: "Invalid email or password" }, { status: 401 })),
    (error) => {
      assert.equal(error.status, 401);
      assert.equal(error.message, "Invalid email or password");
      assert.equal(error.message.includes("private-password"), false);
      return true;
    },
  );
});

test("profile request sends the bearer token and validates the profile response", async () => {
  let request;
  const profile = await getCurrentProfile("test-token", async (url, options) => {
    request = { url, options };
    return Response.json({ id: 7, name: "Riya Singh", email: "riya@example.com" });
  });

  assert.equal(request.url.endsWith("/profile"), true);
  assert.equal(request.options.method, "GET");
  assert.equal(request.options.headers.Authorization, "Bearer test-token");
  assert.deepEqual(profile, { id: 7, name: "Riya Singh", email: "riya@example.com" });
});

test("profile update sends only supplied fields with bearer authorization", async () => {
  let request;
  const profile = await updateCurrentProfile({ name: "Riya Singh" }, "test-token", async (url, options) => {
    request = { url, options };
    return Response.json({ id: 7, name: "Riya Singh", email: "riya@example.com" });
  });

  assert.ok(request.url.endsWith("/profile"));
  assert.equal(request.options.method, "PATCH");
  assert.equal(request.options.headers.Authorization, "Bearer test-token");
  assert.equal(request.options.headers["Content-Type"], "application/json");
  assert.deepEqual(JSON.parse(request.options.body), { name: "Riya Singh" });
  assert.deepEqual(profile, { id: 7, name: "Riya Singh", email: "riya@example.com" });
});

test("profile update validates authentication and fields and surfaces FastAPI errors", async () => {
  await assert.rejects(updateCurrentProfile({ name: "Riya" }, ""), /sign in/i);
  await assert.rejects(updateCurrentProfile({}, "test-token"), /provide a non-empty/i);
  await assert.rejects(updateCurrentProfile({ name: "  " }, "test-token"), /provide a non-empty/i);
  await assert.rejects(
    updateCurrentProfile({ email: "taken@example.com" }, "test-token", async () =>
      Response.json({ detail: "Email already registered" }, { status: 409 })),
    (error) => error.status === 409 && error.message === "Email already registered",
  );
});

test("FastAPI validation detail arrays are summarized without echoing input fields", async () => {
  await assert.rejects(
    registerUser({ name: "Riya", email: "bad", password: "secret" }, async () =>
      Response.json({ detail: [{ loc: ["body", "email"], msg: "value is not a valid email address", input: "bad" }] }, { status: 422 })),
    { message: "value is not a valid email address" },
  );
});
