#!/usr/bin/env python3
"""Ejecuta todas las suites e2e de tests/ (una por historia, tests/us-NN/escenario-*.py).

Uso:  python scripts/ejecutar-tests.py            # todas las suites
      python scripts/ejecutar-tests.py us-05      # solo una suite
Cada test corre con el intérprete actual y su propia salida; el runner agrega PASS/FAIL
por suite y termina con exit code 0 solo si todas las suites pasan.
"""

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
TESTS = RAIZ / "tests"


def suites(filtro):
    for carpeta in sorted(TESTS.iterdir()):
        if not carpeta.is_dir() or not carpeta.name.startswith("us-"):
            continue
        if filtro and filtro != carpeta.name:
            continue
        pruebas = sorted(carpeta.glob("escenario-*.py"))
        if pruebas:
            yield carpeta, pruebas


def principal():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    filtro = sys.argv[1] if len(sys.argv) > 1 else ""
    fallidos = []
    for carpeta, pruebas in suites(filtro):
        print(f"== Suite {carpeta.name} ==")
        for prueba in pruebas:
            resultado = subprocess.run(
                [sys.executable, str(prueba)],
                cwd=RAIZ,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            ok = resultado.returncode == 0
            resumen = "sin resumen"
            for linea in reversed((resultado.stdout or "").splitlines()):
                if linea.startswith("resumen:"):
                    resumen = linea[len("resumen:"):].strip()
                    break
            print(f"  [{'PASS' if ok else 'FAIL'}] {prueba.name} — {resumen}")
            if ok:
                continue
            fallidos.append(prueba)
            print(resultado.stdout or "")
            print(resultado.stderr or "", file=sys.stderr)
    if fallidos:
        print(f"runner: {len(fallidos)} test(s) FALLAN")
        return 1
    print("runner: todas las suites pasan")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
