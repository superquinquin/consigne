/// <reference types="vite/client" />

interface ImportMetaEnv {
  // Optional override for the API base URL. Defaults to "/api" (same-origin
  // in prod, proxied to the local API in dev — see vite.config.ts).
  readonly VITE_API_ADDRESS?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
