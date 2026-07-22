/**
 * api-config.ts
 * =============
 * Initializes the generated API client's base URL from the Vite env variable.
 * Import this module ONCE at the application root (e.g. main.tsx) so the
 * setBaseUrl() call fires before any API hook is used.
 *
 * The generated `setBaseUrl` function is provided by:
 *   @workspace/api-client-react → custom-fetch.ts
 *
 * Environment variable (set in .env.local):
 *   VITE_API_URL=http://localhost:8000
 *
 * If the variable is absent, defaults to "/api" (works when Vite proxies
 * requests, or when the app is served from the same origin as the API).
 */
import { setBaseUrl } from "@workspace/api-client-react";

const apiUrl = (import.meta.env.VITE_API_URL as string | undefined) ?? "/api";

// Strip trailing slash for safety
setBaseUrl(apiUrl.replace(/\/$/, ""));

export { apiUrl };
