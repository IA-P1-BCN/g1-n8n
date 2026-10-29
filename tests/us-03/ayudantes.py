"""Abonos a distancia · US-03 (Flujo 03) contra el stack local.

Suite de `tests/us-03/`, un script por escenario de aceptación (A–H) de la historia #11.
Necesita `app` + `n8n` + `mailpit` arriba y la clave local `API_KEY` del `.env` (sirve a la vez de
`X-API-Key` de la app y de `X-N8N-API-KEY` para leer las executions de n8n; nunca se escribe en el repo).

Cada escenario:
  1. RESETEA los datos de la app (vacía apartados/abonos/ventas/vales por el contenedor; no toca n8n) y el buzón;
  2. crea por API su fixture de apartados (así los importes de C/D y el plazo de F son deterministas, sin depender del seed);
  3. envía el aviso del banco por la rama `aviso.banco` del receptor (`POST /webhook/tienda`);
  4. comprueba en las **executions** de n8n qué rama tomó el flujo y en **Mailpit** el correo resultante
     (recibo del cliente vía Flujo 02, o pregunta/aviso a Marisa), y el estado del apartado en la app.

La evidencia se versiona en `docs/evidencia/us-03/`; los tests son re-ejecutables y salen con exit code.
"""

import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

API_URL = (os.environ.get("API_URL") or "http://localhost:8000").rstrip("/")
N8N_URL = (os.environ.get("N8N_URL") or "http://localhost:5678").rstrip("/")
MAILPIT_URL = (os.environ.get("MAILPIT_URL") or "http://localhost:8025").rstrip("/")
FLUJO03_ID = os.environ.get("N8N_FLUJO03_ID", "pFlujo03AbonosDistancia")
RAIZ = pathlib.Path(__file__).resolve().parents[2]
SALIDA = RAIZ / "docs" / "evidencia" / "us-03"

resultados = []


def clave():
    """Clave local: entorno o `.env` del repo (sirve de X-API-Key de la app y de X-N8N-API-KEY de n8n)."""
    for variable in ("N8N_API_KEY", "API_KEY"):
        if os.environ.get(variable):
            return os.environ[variable].strip()
    fichero = RAIZ / ".env"
    if fichero.exists():
        for linea in fichero.read_text(encoding="utf-8").splitlines():
            if linea.strip().startswith("#") or "=" not in linea:
                continue
            nombre, valor = linea.split("=", 1)
            if nombre.strip() in ("N8N_API_KEY", "API_KEY") and valor.strip():
                return valor.strip()
    return ""


def _peticion(url, datos=None, cabeceras=None, metodo=None):
    cuerpo = None
    cabeceras = dict(cabeceras or {})
    if datos is not None:
        cuerpo = datos if isinstance(datos, bytes) else json.dumps(datos, ensure_ascii=False).encode()
        cabeceras["Content-Type"] = "application/json"
    peticion = urllib.request.Request(url, cuerpo, cabeceras, method=metodo)
    try:
        with urllib.request.urlopen(peticion, timeout=15) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except json.JSONDecodeError:
            return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}


def app_api(metodo, ruta, datos=None):
    return _peticion(f"{API_URL}{ruta}", datos, {"X-API-Key": clave()}, metodo)


def n8n_api(ruta):
    return _peticion(f"{N8N_URL}/api/v1{ruta}", None, {"X-N8N-API-KEY": clave()})


def apuntar(prueba, criterio, ok, detalle=""):
    resultados.append({"prueba": prueba, "criterio": criterio, "resultado": "PASS" if ok else "FAIL", "detalle": str(detalle)})
    print(f"  [{'PASS' if ok else 'FAIL'}] {prueba} · {criterio}" + (f" — {detalle}" if detalle else ""))


# --- Preparación del stack: reset de datos y buzón ------------------------------------------------

def resetear_app():
    """Vacía apartados, abonos, ventas y vales por el propio contenedor de la app (no toca n8n)."""
    orden = ["docker", "compose", "exec", "-T", "tienda", "python", "-c",
             "import sqlite3, config; con = sqlite3.connect(config.DB_PATH); "
             "con.executescript('DELETE FROM vales; DELETE FROM abonos; DELETE FROM ventas; DELETE FROM apartados;'); "
             "con.commit(); con.close()"]
    try:
        proceso = subprocess.run(orden, cwd=RAIZ, capture_output=True, text=True, timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return f"no se pudo ejecutar docker compose ({e})"
    return None if proceso.returncode == 0 else (proceso.stderr.strip() or "docker compose exec falló")


def vaciar_buzon():
    _peticion(f"{MAILPIT_URL}/api/v1/messages", metodo="DELETE")


def crear_apartado(cliente, email, producto, precio, abono_inicial, fecha=None, talla="38"):
    datos = {"cliente": cliente, "email": email, "producto": producto, "talla": talla,
             "precio": precio, "abono_inicial": abono_inicial, "forma_pago": "bizum"}
    if fecha:
        datos["fecha"] = fecha
    estado, cuerpo = app_api("POST", "/api/apartados", datos)
    if estado != 201:
        raise RuntimeError(f"no se pudo crear el apartado de {cliente}: {estado} {cuerpo}")
    return cuerpo


def apartado(apartado_id):
    return app_api("GET", f"/api/apartados/{apartado_id}")[1]


# --- Disparo del aviso y lectura de la ejecución --------------------------------------------------

def enviar_aviso(asunto, cuerpo, reintentos=15, espera=2):
    """POST del aviso por la rama aviso.banco; reintenta mientras n8n registra el webhook tras un rearranque."""
    payload = {"evento": "aviso.banco", "datos": {"asunto": asunto, "cuerpo": cuerpo}}
    for intento in range(1, reintentos + 1):
        estado, respuesta = _peticion(f"{N8N_URL}/webhook/tienda", payload)
        if estado == 200:
            return payload, respuesta
        print(f"    webhook no listo (status {estado}); reintento {intento}/{reintentos}")
        time.sleep(espera)
    return payload, respuesta


def aviso_desde_eml(nombre):
    """Lee data/correos/<nombre>.eml y devuelve (asunto, cuerpo) tal cual llega del banco."""
    texto = (RAIZ / "data" / "correos" / f"{nombre}.eml").read_text(encoding="utf-8").replace("\r\n", "\n")
    cabecera, _, cuerpo = texto.partition("\n\n")
    asunto = ""
    for linea in cabecera.splitlines():
        if linea.lower().startswith("subject:"):
            asunto = linea.split(":", 1)[1].strip()
    return asunto, cuerpo.strip()


def _instante(texto):
    return datetime.fromisoformat((texto or "").replace("Z", "+00:00"))


def ahora():
    return datetime.now(timezone.utc)


def esperar_ejecucion(desde, timeout=70):
    """La ejecución más reciente del Flujo 03 arrancada después de `desde` (None si no llega)."""
    fin = time.time() + timeout
    while time.time() < fin:
        estado, lista = n8n_api(f"/executions?workflowId={FLUJO03_ID}&includeData=true&status=success&limit=20")
        estado2, lista2 = n8n_api(f"/executions?workflowId={FLUJO03_ID}&includeData=true&limit=20")
        for datos in (lista, lista2):
            for ejecucion in (datos or {}).get("data", []):
                try:
                    if _instante(ejecucion.get("startedAt")) >= desde:
                        return ejecucion
                except ValueError:
                    continue
        time.sleep(2)
    return None


def _run_data(ejecucion):
    return (((ejecucion.get("data") or {}).get("resultData") or {}).get("runData") or {})


def nodos(ejecucion):
    return list(_run_data(ejecucion))


def camino(ejecucion):
    """Nodo terminal alcanzado: registrado | rechazo | preguntar | ignorar | (None)."""
    ejecutados = nodos(ejecucion)
    if "Abono registrado · recibo vía Flujo 02" in ejecutados:
        return "registrado"
    if "Motivo del rechazo" in ejecutados or "Avisar a Marisa · rechazo" in ejecutados:
        return "rechazo"
    if "Preguntar a Marisa" in ejecutados:
        return "preguntar"
    if "No es un pago · ignorar" in ejecutados:
        return "ignorar"
    return None


def decision(ejecucion):
    pasos = _run_data(ejecucion).get("Decidir apartado")
    try:
        return pasos[0]["data"]["main"][0][0]["json"]
    except Exception:
        return None


def extraccion(ejecucion):
    pasos = _run_data(ejecucion).get("Normalizar datos del pago")
    try:
        return pasos[0]["data"]["main"][0][0]["json"]
    except Exception:
        return None


# --- Mailpit --------------------------------------------------------------------------------------

def _id(m):
    return m.get("ID") or m.get("Id")


def mensajes():
    _, lista = _peticion(f"{MAILPIT_URL}/api/v1/messages?limit=200")
    return (lista or {}).get("messages", [])


def esperar_correo(predicado, timeout=70):
    """Primer correo del buzón que cumple `predicado(mensaje)` (None si no llega)."""
    fin = time.time() + timeout
    while time.time() < fin:
        for m in mensajes():
            if predicado(m):
                _, completo = _peticion(f"{MAILPIT_URL}/api/v1/message/{_id(m)}")
                return completo or m
        time.sleep(2)
    return None


def destinatarios(m):
    return [d.get("Address", "").lower() for d in (m.get("To") or [])]


def para(email):
    email = email.lower()
    return lambda m: email in destinatarios(m)


def asunto_contiene(texto):
    return lambda m: texto.lower() in (m.get("Subject") or "").lower()


# --- Evidencia y cierre ---------------------------------------------------------------------------

def guardar(nombre, contenido):
    fichero = SALIDA / nombre
    fichero.parent.mkdir(parents=True, exist_ok=True)
    fichero.write_text(
        json.dumps(contenido, ensure_ascii=False, indent=2) if isinstance(contenido, (dict, list)) else str(contenido),
        encoding="utf-8")


def resumen_ejecucion(ejecucion):
    if not ejecucion:
        return {"error": "sin ejecución del Flujo 03"}
    return {
        "id": ejecucion.get("id"),
        "status": ejecucion.get("status"),
        "nodos": nodos(ejecucion),
        "camino": camino(ejecucion),
        "extraccion": extraccion(ejecucion),
        "decision": decision(ejecucion),
    }


def preparar(prueba):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not clave():
        print(f"precondición no cumplida: falta API_KEY en el entorno o en .env")
        sys.exit(1)
    estado, _ = app_api("GET", "/api/apartados/resumen")
    if estado != 200:
        print(f"precondición no cumplida: la app no responde o la clave no es válida ({API_URL}, status {estado})")
        sys.exit(1)
    error = resetear_app()
    if error:
        print(f"precondición no cumplida: no se pudo resetear la app ({error})")
        sys.exit(1)
    vaciar_buzon()
    print(f"== Escenario {prueba} == (app reseteada, buzón vacío)")


def finalizar(sal):
    total_pass = sum(1 for r in resultados if r["resultado"] == "PASS")
    total_fail = sum(1 for r in resultados if r["resultado"] == "FAIL")
    guardar(sal, "\n".join(
        f"{r['resultado']} · {r['prueba']} · {r['criterio']}" + (f" · {r['detalle']}" if r["detalle"] else "")
        for r in resultados) + f"\n\ntotal: {total_pass} PASS / {total_fail} FAIL\n")
    print(f"resumen: {total_pass} PASS / {total_fail} FAIL — evidencia en {SALIDA.relative_to(RAIZ)}")
    return 1 if total_fail else 0
