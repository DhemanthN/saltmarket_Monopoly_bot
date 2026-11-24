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
  build: {
    rollupOptions: {
      output: {
        // Three.js and its React bindings are the bulk of the code, and the start screen needs none of it.
        manualChunks: (id: string) => {
          if (id.includes("node_modules/three/") || id.includes("@react-three/fiber") || id.includes("@react-three/drei")) return "three";
          return undefined;
        },
      },
    },
  },
  // data/board.json lives one level above web/.
  server: { headers: ISOLATION_HEADERS, fs: { allow: [".."] } },
  preview: { headers: ISOLATION_HEADERS },
  test: { environment: "node", include: ["src/**/*.test.ts"] },
});
