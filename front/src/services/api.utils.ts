// Base URL for the API. Defaults to a relative "/api": same-origin in prod
// (the reverse proxy routes /api to the backend) and, in dev, proxied to the
// local API by Vite (see vite.config.ts) — no CORS either way. Override with
// VITE_API_ADDRESS (build-time) for setups that reach the API on another origin
// (e.g. a Docker Compose front without a reverse proxy: VITE_API_ADDRESS=http://localhost:8000).
export const API_ADDRESS: string = import.meta.env.VITE_API_ADDRESS ?? "/api";

export type ApiResponse<T> = {
  status: number
  reasons: string
  data: T
}

export type ApiError = ApiResponse<void> & { __typename: 'ApiError' }
