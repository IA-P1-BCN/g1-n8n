#!/usr/bin/env python3
"""Importa credenciales y flujos en n8n y activa los que queden inactivos (run: task importar).

Corre en el host con Python; orquesta el CLI de n8n (import:credentials, import:workflow,
export:workflow, publish:workflow) en contenedores one-shot del propio servicio `n8n` de
docker-compose, de modo que comparte su imagen y **su volumen de datos** (el que usa la
instancia, sin nombres de volumen a mano). Para n8n al empezar y lo vuelve a arrancar al terminar.

Uso:  python scripts/n8n-importar.py
Exit code: 1 si la importación falla; 0 si termina bien (aunque un flujo siga sin activarse).
"""

import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def comando(*args, check=True, capture=False):
    print("  $ " + " ".join(str(a) for a in args))
    return subprocess.run(list(args), cwd=RAIZ, check=check, capture_output=capture, text=True, encoding="utf-8", errors="replace")


def n8n_cli(subcomando, *args, montajes=()):
    """CLI de n8n en un contenedor one-shot con la imagen, el entorno y el volumen del servicio `n8n`."""
    orden = ["docker", "compose", "run", "--rm", "--no-deps", "--entrypoint", "n8n"]
    for montaje in montajes:
        orden += ["-v", montaje]
    orden += ["n8n", subcomando, *args]
    return comando(*orden, capture=True)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("Importa credenciales y flujos en n8n (para y rearranca el contenedor n8n)")

    resultado = comando("docker", "compose", "stop", "n8n", check=False, capture=True)
    aviso = (resultado.stdout + resultado.stderr).strip()
    print("  " + (aviso.replace("\n", " · ") if aviso else "n8n no estaba levantado; importación en frío"))

    activados = 0
    try:
        print("· Importando credenciales…")
        for fichero in sorted((RAIZ / "credentials").glob("*.json")):
            n8n_cli("import:credentials", f"--input=/credentials/{fichero.name}",
                    montajes=[f"{RAIZ / 'credentials'}:/credentials:ro"]).check_returncode()

        print("· Importando flujos…")
        for fichero in sorted((RAIZ / "workflows").glob("*.json")):
            n8n_cli("import:workflow", f"--input=/workflows/{fichero.name}",
                    montajes=[f"{RAIZ / 'workflows'}:/workflows:ro"]).check_returncode()

        print("· Activando flujos…")
        exportacion = n8n_cli("export:workflow", "--all", "--stdout")
        exportacion.check_returncode()
        flujos = json.loads(exportacion.stdout or "[]")
        if not isinstance(flujos, list):
            print("  ERROR: la exportación de flujos no es una lista")
            return 1
        for flujo in flujos:
            if flujo.get("active"):
                print(f"  ya activo: {flujo['name']} ({flujo['id']})")
                continue
            n8n_cli("publish:workflow", f"--id={flujo['id']}").check_returncode()
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
