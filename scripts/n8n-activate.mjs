// Activa los workflows importados en n8n despues de `n8n export:workflow --all`.
// Se ejecuta dentro del contenedor one-shot n8n-import con node.
// Si un flujo no se puede activar (p.ej. credential inexistente), no corta el arranque.

import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";

const workflows = JSON.parse(readFileSync("/tmp/export.json", "utf8"));
if (!Array.isArray(workflows)) {
  throw new Error("La exportacion de workflows no es un array");
}

let activados = 0;
for (const wf of workflows) {
  if (wf.active) {
    console.log(`Ya activo: ${wf.name} (${wf.id})`);
    continue;
  }
  try {
    execFileSync("n8n", ["publish:workflow", `--id=${wf.id}`], {
      stdio: ["ignore", "inherit", "inherit"],
    });
    console.log(`Activado: ${wf.name} (${wf.id})`);
    activados++;
  } catch (err) {
    console.log(
      `No se pudo activar ${wf.name} (${wf.id}): ${String(err.message).split("\n")[0]}`,
    );
  }
}
console.log(`Workflows activados: ${activados}`);
