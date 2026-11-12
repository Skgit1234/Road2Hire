import { spawn } from "node:child_process";
import { once } from "node:events";
import { fileURLToPath } from "node:url";
import path from "node:path";

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const serverPort = process.env.PLAYWRIGHT_PORT ?? "3100";
let serverUrl = `http://127.0.0.1:${serverPort}`;

let server;
let stopping = false;

async function isServerReady(url) {
  try {
    const response = await fetch(url);
    return response.status < 500;
  } catch {
    return false;
  }
}

function startServer() {
  server = spawn(
    process.execPath,
    ["./node_modules/next/dist/bin/next", "dev", "--hostname", "127.0.0.1", "--port", serverPort],
    {
      cwd: frontendRoot,
      env: process.env,
      stdio: "ignore",
    },
  );
}

async function waitForServer() {
  const deadline = Date.now() + 120_000;
  while (Date.now() < deadline) {
    if (server?.exitCode !== null && server?.exitCode !== undefined) {
      throw new Error(`Next server exited before ${serverUrl} was ready.`);
    }

    if (await isServerReady(serverUrl)) return;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }

  throw new Error(`Timed out waiting for ${serverUrl}.`);
}

async function startOrReuseServer() {
  if (await isServerReady(serverUrl)) return;

  // Next dev uses one .next development lock per project. Reuse the project's
  // conventional local server when it is already running instead of trying to
  // launch a second dev server that will exit on that lock.
  if (!process.env.PLAYWRIGHT_PORT) {
    const conventionalServerUrl = "http://localhost:3000";
    if (await isServerReady(conventionalServerUrl)) {
      serverUrl = conventionalServerUrl;
      return;
    }
  }

  startServer();
  await waitForServer();
}

function runPlaywright() {
  const playwright = spawn(
    process.execPath,
    ["./node_modules/@playwright/test/cli.js", "test"],
    {
      cwd: frontendRoot,
      env: { ...process.env, PLAYWRIGHT_BASE_URL: serverUrl },
      stdio: ["ignore", "inherit", "inherit"],
    },
  );

  return once(playwright, "exit").then(([code]) => code ?? 1);
}

async function stopServer() {
  if (stopping || server === undefined || server.exitCode !== null || server.pid === undefined) return;
  stopping = true;

  if (process.platform === "win32") {
    const taskkill = spawn("taskkill", ["/pid", String(server.pid), "/t", "/f"], {
      stdio: "ignore",
    });
    await Promise.race([
      once(taskkill, "exit"),
      new Promise((resolve) => setTimeout(resolve, 5_000)),
    ]);
    server.unref();
    return;
  }

  server.kill("SIGTERM");
  await Promise.race([
    once(server, "exit"),
    new Promise((resolve) => setTimeout(resolve, 5_000)),
  ]);
  if (server.exitCode === null) server.kill("SIGKILL");
  server.unref();
}

try {
  await startOrReuseServer();
  process.exitCode = await runPlaywright();
} catch (error) {
  console.error(error);
  process.exitCode = 1;
} finally {
  await stopServer();
}
