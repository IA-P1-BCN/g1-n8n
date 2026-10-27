#!/usr/bin/env python3
"""Importa credenciales y flujos en n8n y activa los que queden inactivos (run: task importar).

Corre en el host con Python; orquesta el CLI de n8n (import:credentials, import:workflow,
export:workflow, publish:workflow) en contenedores one-shot de la imagen oficial que comparten
el volumen de datos. Para n8n al empezar y lo vuelve a arrancar al terminar.

Uso:  python scripts/n8n-importar.py
      variables: IMAGEN_N8N (docker.n8n.io/n8nio/n8n), VOLUMEN_N8N (paso-firme_n8n_data)
Exit code: 1 si la importación falla; 0 si termina bien (aunque un flujo siga sin activarse).
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
IMAGEN = os.environ.get("IMAGEN_N8N", "docker.n8n.io/n8nio/n8n")
VOLUMEN = os.environ.get("VOLUMEN_N8N", "paso-firme_n8n_data")


def comando(*args, check=True, capture=False):
    print("  $ " + " ".join(str(a) for a in args))
    return subprocess.run(list(args), cwd=RAIZ, check=check, capture_output=capture, text=True, encoding="utf-8", errors="replace")


def n8n_cli(dir_salida, subcomando, *args):
    monturas = [
        "-v", f"{RAIZ / 'credentials'}:/credentials:ro",
        "-v", f"{RAIZ / 'workflows'}:/workflows:ro",
        "-v", f"{VOLUMEN}:/home/node/.n8n",
    ]
    if dir_salida:
        monturas += ["-v", f"{dir_salida}:/out"]
    args_mount = ["docker", "run", "--rm", "--entrypoint", "n8n", *monturas, IMAGEN, subcomando, *args]
    return comando(*args_mount, capture=True)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("Importa credenciales y flujos en n8n (para y rearranca el contenedor n8n)")

    resultado = comando("docker", "compose", "stop", "n8n", check=False, capture=True)
    aviso = (resultado.stdout + resultado.stderr).strip()
    print("  " + (aviso.replace("\n", " · ") if aviso else "n8n no estaba levantado; importación en frío"))

    salida = tempfile.mkdtemp(prefix="paso-firme-import-")
    activados = 0
    try:
        print("· Importando credenciales…")
        for fichero in sorted((RAIZ / "credentials").glob("*.json")):
            n8n_cli(salida, "import:credentials", f"--input=/credentials/{fichero.name}").check_returncode()

        print("· Importando flujos…")
        for fichero in sorted((RAIZ / "workflows").glob("*.json")):
            n8n_cli(salida, "import:workflow", f"--input=/workflows/{fichero.name}").check_returncode()

        print("· Activando flujos…")
        n8n_cli(salida, "export:workflow", "--all", "--output=/out/export.json").check_returncode()
        flujos = json.loads((Path(salida) / "export.json").read_text(encoding="utf-8"))
        if not isinstance(flujos, list):
            print("  ERROR: la exportación de flujos no es una lista")
            return 1
        for flujo in flujos:
            if flujo.get("active"):
                print(f"  ya activo: {flujo['name']} ({flujo['id']})")
                continue
            n8n_cli(salida, "publish:workflow", f"--id={flujo['id']}").check_returncode()
            activados += 1
            print(f"  activado: {flujo['name']} ({flujo['id']})")
    except subprocess.CalledProcessError as e:
        print("  ERROR: la importación falló", file=sys.stderr)
        if e.stdout:
            print(e.stdout, file=sys.stderr)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        return 1
    finally:
        print("· Rearrancando n8n…")
        comando("docker", "compose", "up", "-d", "n8n")

    print(f"\nImportación completa · workflows reactivados esta vez: {activados}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
