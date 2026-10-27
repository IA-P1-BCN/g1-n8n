#!/usr/bin/env python3
"""Envía a n8n el payload de un fichero JSON (run: task payload -- payloads/venta-registrada.json).

Herramienta de desarrollo: lee el evento de un fichero (nada de JSON a mano en el shell, que se
escapa mal en PowerShell), lo valida y lo POSTea al receptor de la tienda. Con `--esperar` busca la
ejecución en n8n y dice a qué rama del Switch fue el evento.

Uso:  python scripts/enviar-payload.py payloads/apartado-creado.json
      python scripts/enviar-payload.py mi-evento.json --esperar
      variables: N8N_URL (http://localhost:5678), N8N_RECEPTOR_ID, API_KEY o N8N_API_KEY (.env)
Exit code: 0 bien · 1 payload o envío fallido · 2 uso.
"""

import argparse
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

RAIZ = pathlib.Path(__file__).resolve().parents[1]
N8N_URL = (os.environ.get("N8N_URL") or "http://localhost:5678").rstrip("/")
RECEPTOR_ID = os.environ.get("N8N_RECEPTOR_ID") or "HXZBeAF7TZrK4zfD"
RAMAS = ["apartado.creado", "abono.registrado", "venta.registrada", "apartado.vencido"]
NODO_SWITCH = "Repartir por evento"


def clave_n8n():
    """Clave de la API de n8n para leer la ejecución: entorno o `.env` del repo (nunca en el código)."""
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


def leer_payload(ruta):
    """(payload, error): valida el fichero antes de molestar a n8n."""
    fichero = pathlib.Path(ruta)
    if not fichero.is_file():
        return None, f"no existe el fichero «{ruta}»"
    try:
        payload = json.loads(fichero.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return None, f"el fichero no es JSON válido (línea {e.lineno}, columna {e.colno}): {e.msg}"
    if not isinstance(payload, dict):
        return None, "el payload debe ser un objeto JSON con «evento» y «datos»"
    evento = payload.get("evento")
    if not isinstance(evento, str) or not evento.strip():
        return None, "falta «evento» (texto), p. ej. " + ", ".join(RAMAS)
    if not isinstance(payload.get("datos"), dict):
        print("  aviso: no hay «datos» (objeto); los flujos no tendrán qué mostrar")
    return payload, None


def enviar(url, payload, reintentos=5, espera=2):
    """POST al receptor; reintenta mientras n8n está arrancando."""
    cuerpo = json.dumps(payload, ensure_ascii=False).encode()
    estado, respuesta = 0, {}
    for intento in range(1, reintentos + 1):
        peticion = urllib.request.Request(url, cuerpo, {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(peticion, timeout=10) as r:
                estado, texto = r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            estado, texto = e.code, e.read().decode()
        except Exception as e:
            estado, texto = 0, json.dumps({"error": str(e)})
        try:
            respuesta = json.loads(texto or "{}")
        except json.JSONDecodeError:
            respuesta = {"texto": texto}
        if estado == 200:
            return estado, respuesta
        if intento < reintentos:
            print(f"  n8n no acepta el evento (status {estado}); reintento {intento}/{reintentos}")
            time.sleep(espera)
    return estado, respuesta


def instante(texto):
    return datetime.fromisoformat((texto or "").replace("Z", "+00:00"))


def esperar_ejecucion(desde, timeout=30):
    """La ejecución del receptor arrancada después del envío (None si no aparece)."""
    clave = clave_n8n()
    if not clave:
        print("  no puedo leer la ejecución: falta API_KEY (Settings > n8n API) en el entorno o en .env")
        return None
    fin = time.time() + timeout
    while time.time() < fin:
        peticion = urllib.request.Request(
            f"{N8N_URL}/api/v1/executions?workflowId={RECEPTOR_ID}&includeData=true&limit=20",
            headers={"X-N8N-API-KEY": clave},
        )
        try:
            with urllib.request.urlopen(peticion, timeout=10) as r:
                lista = json.loads(r.read().decode())
        except Exception as e:
            print(f"  no puedo consultar las ejecuciones ({e})")
            return None
        for ejecucion in lista.get("data", []):
            try:
                if instante(ejecucion.get("startedAt")) >= desde:
                    return ejecucion
            except ValueError:
                continue
        time.sleep(2)
    return None


def contar_ramas(ejecucion):
    pasos = ((ejecucion.get("data") or {}).get("resultData") or {}).get("runData", {}).get(NODO_SWITCH) or []
    salidas = (pasos[0].get("data", {}).get("main") or []) if pasos else []
    return [(RAMAS[i] if i < len(RAMAS) else "evento desconocido", len(salida or [])) for i, salida in enumerate(salidas)]


def mostrar_ejecucion(ejecucion):
    datos = (ejecucion.get("data") or {}).get("resultData") or {}
    print(f"  ejecución: {ejecucion.get('id')} · {ejecucion.get('status')} · último paso: {datos.get('lastNodeExecuted')}")
    ramas = [(nombre, cantidad) for nombre, cantidad in contar_ramas(ejecucion) if cantidad]
    if not ramas:
        print("  rama: ninguna (¿el Switch no llegó a ejecutarse?)")
    for nombre, cantidad in ramas:
        print(f"  rama: {nombre} · {cantidad} item(s)")
    return ejecucion.get("status") == "success" and len(ramas) == 1


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Envía a n8n el payload de un fichero JSON.")
    parser.add_argument("fichero", help="ruta del JSON con el evento (p. ej. payloads/venta-registrada.json)")
    parser.add_argument("--url", default=f"{N8N_URL}/webhook/tienda", help="webhook destino (por defecto el receptor local)")
    parser.add_argument("--esperar", action="store_true", help="espera la ejecución y muestra a qué rama del Switch fue")
    parser.add_argument("--timeout", type=int, default=30, help="segundos a esperar la ejecución con --esperar (30)")
    args = parser.parse_args()

    payload, error = leer_payload(args.fichero)
    if error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"· payload: {args.fichero}")
    print(f"· evento: {payload['evento']}")
    print(f"· destino: {args.url}")

    desde = datetime.now(timezone.utc)
    estado, respuesta = enviar(args.url, payload)
    print(f"· respuesta: {estado} · {json.dumps(respuesta, ensure_ascii=False)}")
    if estado != 200:
        return 1

    if not args.esperar:
        print("  (con --esperar verás la ejecución y la rama del Switch)")
        return 0

    ejecucion = esperar_ejecucion(desde, args.timeout)
    if not ejecucion:
        print("ERROR: no apareció la ejecución del receptor", file=sys.stderr)
        return 1
    return 0 if mostrar_ejecucion(ejecucion) else 1


if __name__ == "__main__":
    sys.exit(main())
