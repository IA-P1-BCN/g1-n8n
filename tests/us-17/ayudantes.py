"""Receptor de eventos · US-17: webhook único y Switch repartidor contra el stack local.

Suite de `tests/us-17/`, un test por criterio de aceptación de la historia #26. Necesita `n8n` arriba
(`docker compose up -d`) y la clave de n8n en `.env` (`API_KEY`, la misma de Settings > n8n API) para
leer las ejecuciones por la API pública: ahí se ve a qué rama del Switch fue cada evento.
La evidencia del output de cada test va versionada en `docs/evidencia/us-17/`; los tests son
re-ejecutables (idempotentes) y salen con exit code.
"""

import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

N8N_URL = os.environ.get("N8N_URL", "http://localhost:5678")
RECEPTOR_ID = os.environ.get("N8N_RECEPTOR_ID", "HXZBeAF7TZrK4zfD")
NOMBRE_RECEPTOR = "Receptor · Webhook tienda"
NODO_SWITCH = "Repartir por evento"
RAMAS = ["apartado.creado", "abono.registrado", "venta.registrada", "apartado.vencido", "aviso.banco"]
INDICE_FALLBACK = 5
RAIZ = pathlib.Path(__file__).resolve().parents[2]
SALIDA = RAIZ / "docs" / "evidencia" / "us-17"

resultados = []


def apuntar(prueba, criterio, ok, detalle=""):
    resultados.append({"prueba": prueba, "criterio": criterio, "resultado": "PASS" if ok else "FAIL", "detalle": detalle})
    print(f"  [{'PASS' if ok else 'FAIL'}] {prueba} · {criterio}" + (f" — {detalle}" if detalle else ""))


def clave_n8n():
    """La clave de la API de n8n: entorno o `.env` del repo (nunca escrita en el test)."""
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


def api(url, datos=None, cabeceras=None, reintentos=1, espera=2):
    """Petición HTTP que devuelve (status, cuerpo JSON). Reintenta mientras n8n arranca."""
    cuerpo = None
    cabeceras = dict(cabeceras or {})
    if datos is not None:
        cuerpo = datos if isinstance(datos, bytes) else json.dumps(datos, ensure_ascii=False).encode()
        cabeceras["Content-Type"] = "application/json"
    estado, respuesta = 0, {}
    for intento in range(1, reintentos + 1):
        peticion = urllib.request.Request(url, cuerpo, cabeceras)
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
        if estado == 200 or estado == 404 or not intento < reintentos:
            return estado, respuesta
        print(f"    {url} no responde (status {estado}); reintento {intento}/{reintentos}")
        time.sleep(espera)
    return estado, respuesta


def api_n8n(ruta, datos=None, reintentos=1):
    return api(f"{N8N_URL}/api/v1{ruta}", datos, {"X-N8N-API-KEY": clave_n8n()}, reintentos=reintentos)


def ahora():
    return datetime.now(timezone.utc)


def webhook_datos(payload, reintentos=15, espera=2):
    """POST a la Production URL del receptor, reintentando mientras n8n arranca o registra el webhook."""
    return api(f"{N8N_URL}/webhook/tienda", payload, reintentos=reintentos, espera=espera)


def _instante(texto):
    return datetime.fromisoformat((texto or "").replace("Z", "+00:00"))


def esperar_ejecucion(desde, timeout=60):
    """La ejecución más reciente del receptor arrancada después de `desde` (None si no llega)."""
    fin = time.time() + timeout
    while time.time() < fin:
        estado, lista = api_n8n(f"/executions?workflowId={RECEPTOR_ID}&includeData=true&limit=20")
        if estado == 200:
            for ejecucion in lista.get("data", []):
                try:
                    if _instante(ejecucion.get("startedAt")) >= desde:
                        return ejecucion
                except ValueError:
                    continue
        time.sleep(2)
    return None


def _paso(ejecucion, nombre):
    return ((ejecucion.get("data") or {}).get("resultData") or {}).get("runData", {}).get(nombre) or []


def nodos(ejecucion):
    return list(((ejecucion.get("data") or {}).get("resultData") or {}).get("runData", {}))


def reparto(ejecucion):
    """Cuántos items salieron por cada salida del Switch, en orden."""
    pasos = _paso(ejecucion, NODO_SWITCH)
    salidas = (pasos[0].get("data", {}).get("main") or []) if pasos else []
    return [len(salida or []) for salida in salidas]


def evento_de_rama(ejecucion, indice):
    pasos = _paso(ejecucion, NODO_SWITCH)
    salidas = (pasos[0].get("data", {}).get("main") or []) if pasos else []
    items = salidas[indice] if indice < len(salidas) else []
    if not items:
        return None
    return (items[0].get("json") or {}).get("evento")


def resumen_ejecucion(ejecucion):
    """Lo justo para la evidencia: ni headers ni el payload entero."""
    datos = ejecucion.get("data") or {}
    return {
        "id": ejecucion.get("id"),
        "workflowId": ejecucion.get("workflowId"),
        "status": ejecucion.get("status"),
        "mode": ejecucion.get("mode"),
        "startedAt": ejecucion.get("startedAt"),
        "stoppedAt": ejecucion.get("stoppedAt"),
        "lastNodeExecuted": (datos.get("resultData") or {}).get("lastNodeExecuted"),
        "nodos": nodos(ejecucion),
        "salidasDelSwitch": {
            (RAMAS[i] if i < len(RAMAS) else "fallback"): cantidad
            for i, cantidad in enumerate(reparto(ejecucion))
        },
        "eventoPorRama": {
            (RAMAS[i] if i < len(RAMAS) else "fallback"): evento_de_rama(ejecucion, i)
            for i in range(len(reparto(ejecucion)))
        },
    }


def comprobar_reparto(prueba, ejecucion, indice):
    """El Switch manda el item a la rama esperada y a ninguna otra."""
    cuentas = reparto(ejecucion)
    solo_una = sum(cuentas[:len(RAMAS)]) == 1
    ok = indice < len(cuentas) and cuentas[indice] == 1 and solo_una
    apuntar(prueba, f"el Switch lo manda a su rama · {RAMAS[indice]}", ok, f"salidas={cuentas}")
    evento = evento_de_rama(ejecucion, indice)
    apuntar(prueba, f"la rama lleva el evento {RAMAS[indice]}", evento == RAMAS[indice], str(evento))


def guardar(nombre, contenido):
    fichero = SALIDA / nombre
    fichero.parent.mkdir(parents=True, exist_ok=True)
    fichero.write_text(json.dumps(contenido, ensure_ascii=False, indent=2) if isinstance(contenido, (dict, list)) else str(contenido), encoding="utf-8")


def finalizar(nombre_resumen):
    total_pass = sum(1 for r in resultados if r["resultado"] == "PASS")
    total_fail = sum(1 for r in resultados if r["resultado"] == "FAIL")
    guardar(nombre_resumen, "\n".join(f"{r['resultado']} · {r['prueba']} · {r['criterio']}" + (f" · {r['detalle']}" if r["detalle"] else "") for r in resultados) + f"\n\ntotal: {total_pass} PASS / {total_fail} FAIL\n")
    print(f"resumen: {total_pass} PASS / {total_fail} FAIL — evidencia en {SALIDA.relative_to(RAIZ)}")
    return 1 if total_fail else 0


def preparar_salida():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not clave_n8n():
        print("precondición no cumplida: define API_KEY (clave de n8n) en el entorno o en .env")
        sys.exit(1)
    estado, _ = api_n8n(f"/workflows/{RECEPTOR_ID}", reintentos=15)
    if estado != 200:
        print(f"precondición no cumplida: la API de n8n no responde en {N8N_URL} (status {estado})")
        sys.exit(1)
