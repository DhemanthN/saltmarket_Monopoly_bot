// Static dev server with the headers SharedArrayBuffer needs. `?cold=1` pages get no-store
// subresources, otherwise files are immutable like they would be on Vercel.
// Responses are brotli-compressed (cached in memory) to mimic real hosting transfer sizes.
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import zlib from "node:zlib";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT ?? 5199);
const TYPES = {
  ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript",
  ".wasm": "application/wasm", ".json": "application/json", ".zip": "application/zip",
};
const cache = new Map();
let cold = false;

http.createServer((req, res) => {
  const url = new URL(req.url, "http://x");
  if (url.pathname === "/mode") {
    cold = url.searchParams.get("cold") === "1";
    res.end(`cold=${cold}`);
    return;
  }
  const file = path.join(ROOT, decodeURIComponent(url.pathname === "/" ? "/index.html" : url.pathname));
  if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    res.writeHead(404).end("not found");
    return;
  }
  if (!cache.has(file)) {
    const raw = fs.readFileSync(file);
    cache.set(file, { raw, br: zlib.brotliCompressSync(raw, { params: { [zlib.constants.BROTLI_PARAM_QUALITY]: 5 } }) });
  }
  const { raw, br } = cache.get(file);
  const headers = {
    "Content-Type": TYPES[path.extname(file)] ?? "application/octet-stream",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Embedder-Policy": "require-corp",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Cache-Control": cold || /(index.html|worker.js)$/.test(file) ? "no-store" : "public, max-age=31536000, immutable",
  };
  const useBr = /\bbr\b/.test(req.headers["accept-encoding"] ?? "");
  if (useBr) headers["Content-Encoding"] = "br";
  headers["Content-Length"] = (useBr ? br : raw).length;
  res.writeHead(200, headers).end(useBr ? br : raw);
}).listen(PORT, () => console.log(`http://localhost:${PORT}/`));
