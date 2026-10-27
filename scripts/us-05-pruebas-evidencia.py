#!/usr/bin/env python3
"""Pruebas de aceptación e2e de US-05 (Flujo 08 · Aviso de fallo) contra el stack local.

Requiere n8n + mailpit arriba (`docker compose up -d`); no necesita la API de n8n ni la app.
Comprueba los escenarios de aceptación de la historia #21 y deja la evidencia del output
de cada test versionada en docs/evidencia/us-05/.

Uso:  python scripts/us-05-pruebas-evidencia.py
      variables: N8N_URL (por defecto http://localhost:5678), MAILPIT_URL (http://localhost:8025).
Salida: resumen PASS/FAIL por criterio en consola y ficheros; exit code 1 si algún FAIL.
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

N8N_URL = os.environ.get("N8N_URL", "http://localhost:5678")
MAILPIT_URL = os.environ.get("MAILPIT_URL", "http://localhost:8025")
MARCA_ASUNTO = "Aviso de fallo"
SEÑUELOS = ["ULTRA-SECRETO-en82bxyz", "AKIABADKEY123"]
RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "docs" / "evidencia" / "us-05"

resultados = []


def apuntar(prueba, criterio, ok, detalle=""):
    resultados.append({"prueba": prueba, "criterio": criterio, "resultado": "PASS" if ok else "FAIL", "detalle": detalle})
    print(f"  [{'PASS' if ok else 'FAIL'}] {prueba} · {criterio}" + (f" — {detalle}" if detalle else ""))
    return ok


def api(url, datos=None, cabecera_json=True):
    cuerpo = None
    cabeceras = {}
    if datos is not None:
        cuerpo = datos if isinstance(datos, bytes) else json.dumps(datos, ensure_ascii=False).encode()
        if cabecera_json:
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


def buscar_secretos(aviso, etiqueta):
    texto, html = aviso.get("Text") or "", aviso.get("HTML") or ""
    favores = {s: (s in texto, s in html) for s in SEÑUELOS}
    guardar("busqueda-secretos.txt", "\n".join(
        [f"aviso: {aviso.get('ID') or aviso.get('Id')} · {aviso.get('Subject')}"] +
        [f"{etiqueta} · '{s}' en Text: {t} · en HTML: {h}" for s, (t, h) in favores.items()]
    ) + "\n")
    return favores


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    print("Pruebas US-05 · Flujo 08 · Aviso de fallo")
    estado, _ = api(f"{MAILPIT_URL}/api/v1/messages?limit=1")
    if estado != 200:
        print(f"  [FAIL] precondición · Mailpit no responde en {MAILPIT_URL}")
        sys.exit(1)

    conocidos = mensajes_actuales()
    print(f"  mensajes previos en Mailpit: {len(conocidos)}")

    print("\n— Test 1 · fallo en Flujo 01 (Escenario A) + secretos (Escenario B) —")
    payload = {
        "evento": "apartado.creado",
        "datos": {
            "id": 997, "fecha": "2026-10-26", "cliente": "Prueba de fallo",
            "email": "nadie", "producto": "Botín piel marrón", "talla": "38",
            "precio": 89.9, "abonado": 10, "pendiente": 79.9,
            "fecha_limite": "2027-01-24", "estado": "activo",
            "password": SEÑUELOS[0], "apikey": SEÑUELOS[1],
        },
    }
    estado, respuesta = api(f"{N8N_URL}/webhook/tienda", payload)
    guardar("fallo-flujo-01-payload.json", payload)
    guardar("fallo-flujo-01-webhook.json", {"status": estado, "respuesta": respuesta})
    apuntar("fallo-flujo-01", "webhook acepta el evento", estado == 200, str(respuesta.get("message", "")))

    aviso = esperar_aviso(conocidos, "Flujo 01")
    if not aviso:
        apuntar("fallo-flujo-01", "aviso recibido en Mailpit", False, "timeout sin aviso")
    else:
        campos = extraer_campos(aviso)
        guardar("fallo-flujo-01-aviso.json", aviso)
        apuntar("fallo-flujo-01", "aviso recibido en Mailpit", True, aviso.get("Subject", ""))
        apuntar("fallo-flujo-01", "nombra el flujo", (campos.get("flujo") or "").startswith("Flujo 01"), campos.get("flujo"))
        apuntar("fallo-flujo-01", "nombra el paso", campos.get("paso") == "Enviar resumen al cliente", campos.get("paso"))
        apuntar("fallo-flujo-01", "incluye el error", "No recipients defined" in (campos.get("error") or ""), campos.get("error"))
        apuntar("fallo-flujo-01", "enlace a la ejecución", bool((campos.get("ejecucion") or "").startswith(N8N_URL + "/workflow/")), campos.get("ejecucion"))
        favores = buscar_secretos(aviso, "fallo-flujo-01")
        limpio = all(not t and not h for t, h in favores.values())
        apuntar("fallo-flujo-01", "sin contraseñas ni claves (Escenario B)", limpio, json.dumps(favores))

        aviso_receptor = esperar_aviso(conocidos, "Receptor")
        if not aviso_receptor:
            apuntar("fallo-flujo-01", "aviso del Receptor (padre)", False, "timeout sin aviso del receptor")
        else:
            campos_r = extraer_campos(aviso_receptor)
            guardar("fallo-flujo-01-receptor-aviso.json", aviso_receptor)
            apuntar("fallo-flujo-01", "aviso del Receptor (padre)", True, aviso_receptor.get("Subject", ""))
            apuntar("fallo-flujo-01", "paso del receptor", campos_r.get("paso") == "Ejecutar Flujo 01", campos_r.get("paso"))

    print("\n— Test 2 · fallo en el Receptor (body no objeto) —")
    conocidos = mensajes_actuales()
    estado, respuesta = api(f"{N8N_URL}/webhook/tienda", b"[1,2,3]")
    guardar("fallo-receptor-payload.txt", "[1,2,3]")
    guardar("fallo-receptor-webhook.json", {"status": estado, "respuesta": respuesta})
    apuntar("fallo-receptor", "webhook acepta la petición", estado == 200, str(respuesta.get("message", "")))

    aviso = esperar_aviso(conocidos, "Receptor")
    if not aviso:
        apuntar("fallo-receptor", "aviso recibido en Mailpit", False, "timeout sin aviso")
    else:
        campos = extraer_campos(aviso)
        guardar("fallo-receptor-aviso.json", aviso)
        apuntar("fallo-receptor", "aviso recibido en Mailpit", True, aviso.get("Subject", ""))
        apuntar("fallo-receptor", "nombra el flujo", "Receptor" in (campos.get("flujo") or ""), campos.get("flujo"))
        apuntar("fallo-receptor", "nombra el paso", campos.get("paso") == "Evento y datos", campos.get("paso"))
        apuntar("fallo-receptor", "incluye el error", "valid JSON object" in (campos.get("error") or ""), campos.get("error"))

    total_pass = sum(1 for r in resultados if r["resultado"] == "PASS")
    total_fail = sum(1 for r in resultados if r["resultado"] == "FAIL")
    guardar(
        "resumen.txt",
        "\n".join(f"{r['resultado']} · {r['prueba']} · {r['criterio']}" + (f" · {r['detalle']}" if r['detalle'] else "") for r in resultados)
        + f"\n\ntotal: {total_pass} PASS / {total_fail} FAIL\n",
    )
    print(f"\nresumen: {total_pass} PASS / {total_fail} FAIL — evidencia en {SALIDA.relative_to(RAIZ)}")
    sys.exit(1 if total_fail else 0)


if __name__ == "__main__":
    main()
