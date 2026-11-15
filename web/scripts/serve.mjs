import { createServer } from "node:http";
import { readFile, realpath, stat } from "node:fs/promises";
import { extname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../", import.meta.url));
const port = Number(process.env.ACCESS_KIT_DEMO_PORT || 4173);
const types = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".woff2": "font/woff2", ".woff": "font/woff", ".map": "application/json" };
const server = createServer(async (request, response) => {
  try {
    if (!["GET", "HEAD"].includes(request.method)) { response.writeHead(405).end(); return; }
    const path = decodeURIComponent(new URL(request.url, "http://localhost").pathname);
    const filename = await realpath(resolve(root, `.${path === "/" ? "/demo/index.html" : path}`));
    if (!filename.startsWith(root.endsWith(sep) ? root : root + sep) || !(await stat(filename)).isFile()) { response.writeHead(404).end(); return; }
    const body = await readFile(filename);
    response.writeHead(200, { "Content-Type": types[extname(filename)] || "application/octet-stream", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" });
    response.end(request.method === "HEAD" ? undefined : body);
  } catch { response.writeHead(404).end("Not found"); }
});
server.listen(port, "127.0.0.1", () => console.log(`access-kit demo: http://127.0.0.1:${port}`));
for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => server.close());
