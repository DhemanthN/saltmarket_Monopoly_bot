/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

/**
 * Cross-origin isolation headers. They unlock SharedArrayBuffer, which runtime option A
 * (Pyodide in a Web Worker) needs. Every asset is self-hosted, so require-corp blocks nothing.
 * If the runtime spike picks option B, delete this constant and the two `headers` lines.
 */
const ISOLATION_HEADERS = {
  "Cross-Origin-Opener-Policy": "same-origin",
  "Cross-Origin-Embedder-Policy": "require-corp",
};

export default defineConfig({
  plugins: [react()],
  server: { headers: ISOLATION_HEADERS },
  preview: { headers: ISOLATION_HEADERS },
  test: { environment: "node", include: ["src/**/*.test.ts"] },
});
