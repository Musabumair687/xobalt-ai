/**
 * Resilient API client for Xobalt AI backend.
 * Automatically handles Windows localhost / 127.0.0.1 IPv4/IPv6 resolution.
 */

const BACKEND_URLS = ["http://127.0.0.1:8000", "http://localhost:8000"];
const ACCESS_TOKEN_KEY = "xobalt_access_token";

export function storeAccessToken(token: string): void {
  window.sessionStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function clearAccessToken(): void {
  window.sessionStorage.removeItem(ACCESS_TOKEN_KEY);
}

export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  let lastError: any = null;

  for (const base of BACKEND_URLS) {
    try {
      const url = `${base}${path}`;
      const headers = new Headers(options.headers);
      const token = typeof window === "undefined"
        ? null
        : window.sessionStorage.getItem(ACCESS_TOKEN_KEY);
      if (token && !headers.has("Authorization")) {
        headers.set("Authorization", `Bearer ${token}`);
      }

      const res = await fetch(url, { ...options, headers });
      if (
        res.status === 401 &&
        path !== "/api/v1/auth/login" &&
        typeof window !== "undefined" &&
        window.location.pathname !== "/login"
      ) {
        clearAccessToken();
        window.location.assign("/login");
      }
      return res;
    } catch (err) {
      lastError = err;
    }
  }

  throw lastError || new Error("Failed to connect to backend on port 8000");
}
