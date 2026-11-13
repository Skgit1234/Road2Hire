const LOCAL_API_BASE_URL = "http://127.0.0.1:8001";

export function normalizeApiBaseUrl(baseUrl: string): string {
  return baseUrl.trim().replace(/\/+$/, "");
}

export const API_BASE_URL = normalizeApiBaseUrl(
  process.env.NEXT_PUBLIC_API_BASE_URL || LOCAL_API_BASE_URL,
);
