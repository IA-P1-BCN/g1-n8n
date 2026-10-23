#!/usr/bin/env node
// Wrapper multiplataforma para lanzar n8n-mcp desde opencode (Windows / macOS).
//
// Estrategia:
//  1. Si n8n-mcp esta instalado global (`npm i -g n8n-mcp`), lanza su entrypoint
//     stdio con `node`. En Windows es lo recomendado: npx puede fallar (cache de
//     npm corrupta, p.ej. el bug de `ajv`, y los shims .cmd) y no usa shells.
//  2. Si no existe instalacion global (tipico en macOS), hace fallback a
//     `npx -y n8n-mcp`, que en macOS funciona sin necesidad de instalar nada.
//
// El resultado es que opencode solo necesita: ["node", ".opencode/mcp/n8n-mcp.cjs"]

const { spawn, spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

function resolveGlobalEntry() {
  const res = spawnSync("npm root -g", { shell: true, encoding: "utf8" });
  if (res.status !== 0 || !res.stdout) return null;
  const entry = path.join(
    res.stdout.trim(),
    "n8n-mcp",
    "dist",
    "mcp",
    "stdio-wrapper.js",
  );
  return fs.existsSync(entry) ? entry : null;
}

const globalEntry = resolveGlobalEntry();

const child = globalEntry
  ? spawn(process.execPath, [globalEntry], { stdio: "inherit", env: process.env })
  : spawn("npx -y n8n-mcp", { shell: true, stdio: "inherit", env: process.env });

child.on("exit", (code, signal) => {
  process.exit(signal ? 0 : (code ?? 1));
});

for (const sig of ["SIGINT", "SIGTERM"]) {
  process.on(sig, () => child.kill());
}
