import { API_BASE_URL } from "./api-config.ts";

export type BackendHealthResponse = {
  status: "healthy";
};

const HEALTH_CHECK_TIMEOUT_MS = 8_000;

export async function checkBackendHealth(
  fetchRequest: typeof fetch = fetch,
): Promise<BackendHealthResponse> {
  let response: Response;

  try {
    response = await fetchRequest(`${API_BASE_URL}/health`, {
      method: "GET",
      signal: AbortSignal.timeout(HEALTH_CHECK_TIMEOUT_MS),
    });
  } catch (error) {
    if (error instanceof Error && error.name === "TimeoutError") {
      throw new Error("The backend health check timed out after 8 seconds.");
    }
    throw new Error(
      "Could not connect to the backend. Check that it is running and that NEXT_PUBLIC_API_BASE_URL is correct.",
    );
  }

  if (!response.ok) {
    throw new Error(`The backend health check returned HTTP ${response.status}.`);
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new Error("The backend health check returned invalid JSON.");
  }

  if (
    typeof payload !== "object" ||
    payload === null ||
    !("status" in payload) ||
    payload.status !== "healthy"
  ) {
    throw new Error("The backend health check returned an unexpected response.");
  }

  return { status: "healthy" };
}
