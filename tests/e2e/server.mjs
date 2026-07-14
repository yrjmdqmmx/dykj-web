import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize, resolve } from "node:path";

const host = "127.0.0.1";
const port = Number(process.env.PORT || 4173);
const siteRoot = resolve(process.cwd(), "_site");
const projectPrefix = "/dykj-web";

const mimeTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".txt": "text/plain; charset=utf-8",
  ".webp": "image/webp",
  ".xml": "application/xml; charset=utf-8"
};

function sendFile(response, filePath, statusCode, method) {
  response.writeHead(statusCode, {
    "cache-control": "no-store",
    "content-length": statSync(filePath).size,
    "content-type": mimeTypes[extname(filePath).toLowerCase()] || "application/octet-stream"
  });
  if (method === "HEAD") response.end();
  else createReadStream(filePath).pipe(response);
}

function resolveRequestPath(pathname) {
  let deploymentPath = pathname;
  if (deploymentPath === projectPrefix) deploymentPath = "/";
  else if (deploymentPath.startsWith(projectPrefix + "/")) {
    deploymentPath = deploymentPath.slice(projectPrefix.length);
  }

  let relativePath = decodeURIComponent(deploymentPath).replace(/^\/+/, "");
  if (!relativePath || relativePath.endsWith("/")) relativePath += "index.html";
  const candidate = resolve(siteRoot, normalize(relativePath));
  return candidate.startsWith(siteRoot + "/") ? candidate : null;
}

const server = createServer((request, response) => {
  if (request.method !== "GET" && request.method !== "HEAD") {
    response.writeHead(405, { allow: "GET, HEAD" });
    response.end();
    return;
  }

  let pathname;
  try {
    pathname = new URL(request.url, `http://${host}:${port}`).pathname;
  } catch {
    response.writeHead(400);
    response.end();
    return;
  }

  let candidate;
  try {
    candidate = resolveRequestPath(pathname);
  } catch {
    candidate = null;
  }

  if (candidate && existsSync(candidate) && statSync(candidate).isFile()) {
    sendFile(response, candidate, 200, request.method);
    return;
  }

  const notFound = join(siteRoot, "404.html");
  if (existsSync(notFound)) sendFile(response, notFound, 404, request.method);
  else {
    response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
    response.end("Not found");
  }
});

server.listen(port, host, () => {
  process.stdout.write(`Dingyi browser QA server listening on http://${host}:${port}\n`);
});

function close() {
  server.close(() => process.exit(0));
}

process.on("SIGINT", close);
process.on("SIGTERM", close);
