"""Avisos de fallo · US-05 (Flujo 08 · Aviso de fallo) contra el stack local.

Suite de `tests/us-05/`, un test por escenario de aceptación de la historia #21; no necesita la API de n8n ni la app, solo `n8n` + `mailpit` arriba (`docker compose up -d`).
La evidencia del output de cada test va versionada en `docs/evidencia/us-05/`; los tests son re-ejecutables (idempotentes) y salen con exit code.
"""

import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request
N8N_URL = os.environ.get("N8N_URL", "http://localhost:5678")
MAILPIT_URL = os.environ.get("MAILPIT_URL", "http://localhost:8025")
MARCA_ASUNTO = "Aviso de fallo"
SEÑUELOS = ["ULTRA-SECRETO-en82bxyz", "AKIABADKEY123"]
RAIZ = pathlib.Path(__file__).resolve().parents[2]
SALIDA = RAIZ / "docs" / "evidencia" / "us-05"

resultados = []


def apuntar(prueba, criterio, ok, detalle=""):
    resultados.append({"prueba": prueba, "criterio": criterio, "resultado": "PASS" if ok else "FAIL", "detalle": detalle})
    print(f"  [{'PASS' if ok else 'FAIL'}] {prueba} · {criterio}" + (f" — {detalle}" if detalle else ""))


def api(url, datos=None):
    cuerpo = None
    cabeceras = {}
    if datos is not None:
        cuerpo = datos if isinstance(datos, bytes) else json.dumps(datos, ensure_ascii=False).encode()
        cabeceras["Content-Type"] = "application/json"
    peticion = urllib.request.Request(url, cuerpo, cabeceras)
    try:
        with urllib.request.urlopen(peticion, timeout=10) as respuesta:
            return respuesta.status, json.loads(respuesta.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")
    except Exception as e:
        return 0, {"error": str(e)}


def identificador(m):
    return m.get("ID") or m.get("Id")


def mensajes_actuales():
    _, lista = api(f"{MAILPIT_URL}/api/v1/messages?limit=200")
    return {identificador(m) for m in (lista or {}).get("messages", [])}


def webhook_datos(payload, reintentos=15, espera=2):
    """POST al webhook del receptor, reintentando mientras n8n arranca o registra el webhook (404 o conexión caída tras un rearranque: ~30 s de ventana)."""
    estado, respuesta = 0, {}
    for intento in range(1, reintentos + 1):
        estado, respuesta = api(f"{N8N_URL}/webhook/tienda", payload)
        if estado == 200:
            return estado, respuesta
        print(f"    webhook no listo (status {estado}); reintento {intento}/{reintentos}")
        time.sleep(espera)
    return estado, respuesta


def esperar_aviso(conocidos, marca, timeout=60):
    fin = time.time() + timeout
    while time.time() < fin:
        _, lista = api(f"{MAILPIT_URL}/api/v1/messages?limit=200")
        for m in (lista or {}).get("messages", []):
            if identificador(m) in conocidos:
                continue
            asunto = (m.get("Subject") or "").strip()
            if MARCA_ASUNTO in asunto and marca in asunto:
                _, aviso = api(f"{MAILPIT_URL}/api/v1/message/{identificador(m)}")
                return aviso
        time.sleep(2)
    return None


def extraer_campos(aviso):
    html = aviso.get("HTML") or ""
    campos = {}
    for clave in ["Flujo", "Paso", "Error"]:
        m = re.search(rf"<td><b>{clave}</b></td><td>(.*?)</td>", html, re.S)
        campos[clave.lower()] = re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else None
    m = re.search(r'href="([^"]+)"', html)
    campos["ejecucion"] = m.group(1) if m else None
    return campos


def guardar(nombre, contenido):
    fichero = SALIDA / nombre
    fichero.parent.mkdir(parents=True, exist_ok=True)
    fichero.write_text(json.dumps(contenido, ensure_ascii=False, indent=2) if isinstance(contenido, (dict, list)) else str(contenido), encoding="utf-8")


def finalizar(sal):
    total_pass = sum(1 for r in resultados if r["resultado"] == "PASS")
    total_fail = sum(1 for r in resultados if r["resultado"] == "FAIL")
    guardar(sal, "\n".join(f"{r['resultado']} · {r['prueba']} · {r['criterio']}" + (f" · {r['detalle']}" if r["detalle"] else "") for r in resultados) + f"\n\ntotal: {total_pass} PASS / {total_fail} FAIL\n")
    print(f"resumen: {total_pass} PASS / {total_fail} FAIL — evidencia en {SALIDA.relative_to(RAIZ)}")
    return 1 if total_fail else 0


def preparar_salida():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    estado, _ = api(f"{MAILPIT_URL}/api/v1/messages?limit=1")
    if estado != 200:
        print(f"precondición no cumplida: Mailpit no responde en {MAILPIT_URL}")
        sys.exit(1)
