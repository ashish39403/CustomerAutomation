/// <reference types="vitest/config" />
import { resolve } from "node:path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": resolve(import.meta.dirname, "./src"),
    },
  },
  server: {
    // Same-origin proxy so the session cookie works in dev without CORS.
    // The backend listens on 127.0.0.1 only, hence the IP (not localhost).
    // Port 8010 (not the default 8000): port 8000 is occupied on this machine
    // by an unrelated local service that answers with 401s.
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8010",
        changeOrigin: true,
      },
      // The public readiness probe lives in the root: /health, /health/ready.
      "/health": {
        target: "http://127.0.0.1:8010",
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
  },
})
