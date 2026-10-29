"""Cierre diario · US-04 (Flujo 05 · Cierre diario) contra el stack local.

Suite de `tests/us-04/`, un script por escenario de aceptación de la historia #16.
Ejecuta el flujo por CLI en el contenedor de n8n (`n8n execute --id=pFlujo05CierreDiario`), registra
ventas y abonos del día por la API de la tienda (`http://localhost:8000`) y comprueba el correo del
cierre en Mailpit (`http://localhost:8025`). La evidencia queda versionada en `docs/evidencia/us-04/`.
"""

import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

FLUJO_ID = os.environ.get("N8N_FLUJO_05_ID", "pFlujo05CierreDiario")
API_URL = (os.environ.get("API_URL") or "http://localhost:8000").rstrip("/")
MAILPIT_URL = (os.environ.get("MAILPIT_URL") or "http://localhost:8025").rstrip("/")
MARCA_ASUNTO = "Cierre de caja"
RAIZ = pathlib.Path(__file__).resolve().parents[2]
SALIDA = RAIZ / "docs" / "evidencia" / "us-04"

resultados = []


def apuntar(prueba, criterio, ok, detalle=""):
    resultados.append({"prueba": prueba, "criterio": criterio, "resultado": "PASS" if ok else "FAIL", "detalle": str(detalle)})
    print(f"  [{'PASS' if ok else 'FAIL'}] {prueba} · {criterio}" + (f" — {detalle}" if detalle else ""))


def clave_api():
    """Clave de la API de la tienda: entorno o `.env` del repo (nunca escrita en el test)."""
    if os.environ.get("API_KEY"):
        return os.environ["API_KEY"].strip()
    fichero = RAIZ / ".env"
    if fichero.exists():
        for linea in fichero.read_text(encoding="utf-8").splitlines():
            if linea.strip().startswith("#") or "=" not in linea:
                continue
            nombre, valor = linea.split("=", 1)
            if nombre.strip() == "API_KEY" and valor.strip():
                return valor.strip()
    return ""


def http_json(url, metodo="GET", datos=None, cabeceras=None):
    cuerpo = None
    cabeceras = dict(cabeceras or {})
    if datos is not None:
        cuerpo = datos if isinstance(datos, bytes) else json.dumps(datos, ensure_ascii=False).encode()
        cabeceras["Content-Type"] = "application/json"
    peticion = urllib.request.Request(url, cuerpo, cabeceras, method=metodo)
    try:
        with urllib.request.urlopen(peticion, timeout=10) as r:
            estado, texto = r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        estado, texto = e.code, e.read().decode()
    except Exception as e:
        return 0, {"error": str(e)}
    try:
        return estado, json.loads(texto or "{}")
    except json.JSONDecodeError:
        return estado, {"texto": texto}


def api_tienda(ruta, metodo="GET", datos=None):
    return http_json(f"{API_URL}{ruta}", metodo=metodo, datos=datos, cabeceras={"X-API-Key": clave_api()})


def crear_venta(concepto, importe, forma_pago):
    estado, resp = api_tienda("/api/ventas", "POST", {"concepto": concepto, "importe": importe, "forma_pago": forma_pago})
    if estado != 201:
        raise RuntimeError(f"no se pudo crear la venta {concepto} ({estado}): {resp}")
    return resp


def crear_apartado(cliente, producto, precio, abono_inicial, forma_pago):
    """Crea un apartado hoy; su abono inicial cuenta como cobro del día."""
    datos = {"cliente": cliente, "email": f"{cliente.split()[0].lower()}@prueba.local", "producto": producto,
             "talla": "38", "precio": precio, "abono_inicial": abono_inicial, "forma_pago": forma_pago}
    estado, resp = api_tienda("/api/apartados", "POST", datos)
    if estado != 201:
        raise RuntimeError(f"no se pudo crear el apartado de {cliente} ({estado}): {resp}")
    return resp


def registrar_abono(apartado_id, importe, forma_pago):
    estado, resp = api_tienda(f"/api/apartados/{apartado_id}/abonos", "POST", {"importe": importe, "forma_pago": forma_pago})
    if estado != 201:
        raise RuntimeError(f"no se pudo registrar el abono ({estado}): {resp}")
    return resp


def limpiar_base():
    """Vacía apartados, abonos, ventas y vales en el contenedor `tienda` (sin tocar n8n)."""
    orden = ["docker", "compose", "exec", "-T", "tienda", "python", "-c",
             "import sqlite3, config; con = sqlite3.connect(config.DB_PATH); "
             "con.executescript('DELETE FROM vales; DELETE FROM abonos; DELETE FROM ventas; DELETE FROM apartados;'); "
             "con.commit(); con.close()"]
    proceso = subprocess.run(orden, cwd=RAIZ, capture_output=True, text=True, timeout=30)
    if proceso.returncode != 0:
        raise RuntimeError(proceso.stderr.strip() or proceso.stdout.strip() or "no se pudo limpiar la base de datos")


def limpiar_buzon():
    http_json(f"{MAILPIT_URL}/api/v1/messages", metodo="DELETE")


def ejecutar_flujo():
    """Dispara el Flujo 05 en el contenedor `n8n` mediante el CLI de n8n."""
    orden = ["docker", "compose", "exec", "-T", "-e", "N8N_RUNNERS_BROKER_PORT=5689",
             "n8n", "n8n", "execute", f"--id={FLUJO_ID}"]
    proceso = subprocess.run(orden, cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
    salida = (proceso.stdout or "") + ("\n" + proceso.stderr if proceso.stderr else "")
    return proceso.returncode == 0, salida.strip()


def _id(m):
    return m.get("ID") or m.get("Id")


def esperar_cierre(conocidos, timeout=25):
    """Primer correo nuevo cuyo asunto sea el del cierre de caja (None si no llega)."""
    fin = time.time() + timeout
    while time.time() < fin:
        _, lista = http_json(f"{MAILPIT_URL}/api/v1/messages?limit=200")
        for m in (lista or {}).get("messages", []):
            if _id(m) in conocidos:
                continue
            if MARCA_ASUNTO in (m.get("Subject") or ""):
                _, detalle = http_json(f"{MAILPIT_URL}/api/v1/message/{_id(m)}")
                return detalle or m
        time.sleep(1)
    return None


def mensajes_actuales():
    _, lista = http_json(f"{MAILPIT_URL}/api/v1/messages?limit=200")
    return {_id(m) for m in (lista or {}).get("messages", [])}


def guardar(nombre, contenido):
    fichero = SALIDA / nombre
    fichero.parent.mkdir(parents=True, exist_ok=True)
    fichero.write_text(
        json.dumps(contenido, ensure_ascii=False, indent=2) if isinstance(contenido, (dict, list)) else str(contenido),
        encoding="utf-8")


def finalizar(nombre_resumen):
    total_pass = sum(1 for r in resultados if r["resultado"] == "PASS")
    total_fail = sum(1 for r in resultados if r["resultado"] == "FAIL")
    guardar(nombre_resumen, "\n".join(
        f"{r['resultado']} · {r['prueba']} · {r['criterio']}" + (f" · {r['detalle']}" if r["detalle"] else "")
        for r in resultados) + f"\n\ntotal: {total_pass} PASS / {total_fail} FAIL\n")
    print(f"resumen: {total_pass} PASS / {total_fail} FAIL — evidencia en {SALIDA.relative_to(RAIZ)}")
    return 1 if total_fail else 0


def preparar_salida():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not clave_api():
        print("precondición no cumplida: falta API_KEY en el entorno o en .env")
        sys.exit(1)
    estado, _ = api_tienda("/api/apartados/resumen")
    if estado != 200:
        print(f"precondición no cumplida: la app no responde en {API_URL} (status {estado})")
        sys.exit(1)
    estado_mp, _ = http_json(f"{MAILPIT_URL}/api/v1/messages?limit=1")
    if estado_mp != 200:
        print(f"precondición no cumplida: Mailpit no responde en {MAILPIT_URL} (status {estado_mp})")
        sys.exit(1)
