// Relative path: same-origin in prod (reverse proxy routes /api to the backend),
// and in dev Vite proxies /api to the local API (see vite.config.ts) — no CORS either way.
export const API_ADDRESS: string = "/api";

export type ApiResponse<T> = {
  status: number
  reasons: string
  data: T
}

export type ApiError = ApiResponse<void> & { __typename: 'ApiError' }
