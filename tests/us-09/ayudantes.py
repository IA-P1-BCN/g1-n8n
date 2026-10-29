"""Aviso de ventas grandes · US-09 (Flujo 04) contra el stack local.

Suite de `tests/us-09/`, un script por escenario de aceptación de la historia #62.
Las ventas se crean por la API de la app (`POST /api/ventas`), que avisa al Receptor
(`POST /webhook/tienda`) y este enruta a `Ejecutar Flujo 04`; el aviso a Marisa se
comprueba en Mailpit (`http://localhost:8025`). El umbral se lee del entorno del
contenedor de n8n y el escenario B lo cambia en `.env` sin abrir el flujo.
La evidencia del output de cada test queda versionada en `docs/evidencia/us-09/`.
"""

import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

FLUJO_ID = os.environ.get("N8N_FLUJO_04_ID", "pFlujo04AvisoVentaGrande")
NOMBRE_FLUJO = "Flujo 04 · Aviso de ventas grandes"
N8N_URL = (os.environ.get("N8N_URL") or "http://localhost:5678").rstrip("/")
API_URL = (os.environ.get("API_URL") or "http://localhost:8000").rstrip("/")
MAILPIT_URL = (os.environ.get("MAILPIT_URL") or "http://localhost:8025").rstrip("/")
MARCA_ASUNTO = "Venta grande"
UMBRAL_DEF = 200
RAIZ = pathlib.Path(__file__).resolve().parents[2]
SALIDA = RAIZ / "docs" / "evidencia" / "us-09"

resultados = []


def apuntar(prueba, criterio, ok, detalle=""):
    resultados.append({
        "prueba": prueba,
        "criterio": criterio,
        "resultado": "PASS" if ok else "FAIL",
        "detalle": detalle,
    })
    print(f"  [{'PASS' if ok else 'FAIL'}] {prueba} · {criterio}" + (f" — {detalle}" if detalle else ""))


def _variable_del_env(nombre_busqueda):
    """Variable de `.env` del repo (nunca se escribe su valor en la evidencia)."""
    if os.environ.get(nombre_busqueda):
        return os.environ[nombre_busqueda].strip()
    fichero = RAIZ / ".env"
    if fichero.exists():
        for linea in fichero.read_text(encoding="utf-8").splitlines():
            if linea.strip().startswith("#") or "=" not in linea:
                continue
            nombre, valor = linea.split("=", 1)
            if nombre.strip() == nombre_busqueda and valor.strip():
                return valor.strip()
    return ""


def clave_api():
    return _variable_del_env("API_KEY")


def clave_n8n():
    return _variable_del_env("N8N_API_KEY") or _variable_del_env("API_KEY")


def http_json(url, metodo="GET", datos=None, cabeceras=None, reintentos=1, espera=2):
    """Petición HTTP que devuelve (estado, cuerpo JSON). Reintenta mientras el stack arranca."""
    cuerpo = None
    cabeceras = dict(cabeceras or {})
    if datos is not None:
        cuerpo = datos if isinstance(datos, bytes) else json.dumps(datos, ensure_ascii=False).encode()
        cabeceras["Content-Type"] = "application/json"
    estado, respuesta = 0, {}
    for intento in range(1, reintentos + 1):
        peticion = urllib.request.Request(url, cuerpo, cabeceras, method=metodo)
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


def api_tienda(ruta, metodo="GET", datos=None):
    return http_json(f"{API_URL}{ruta}", metodo=metodo, datos=datos, cabeceras={"X-API-Key": clave_api()})


def crear_venta(importe, concepto, forma_pago="tarjeta"):
    """Registra la venta en la app (que avisa al Receptor en una tarea de fondo)."""
    datos = {"concepto": concepto, "importe": importe, "forma_pago": forma_pago}
    return api_tienda("/api/ventas", metodo="POST", datos=datos)


def mensajes_actuales():
    _, lista = http_json(f"{MAILPIT_URL}/api/v1/messages?limit=200")
    return {m.get("ID") for m in (lista or {}).get("messages", [])}


def detalle_correo(m):
    _, detalle = http_json(f"{MAILPIT_URL}/api/v1/message/{m['ID']}")
    return detalle


def buscar_aviso(conocidos):
    """El primer correo nuevo cuyo asunto marca aviso de venta grande (detalle completo)."""
    _, lista = http_json(f"{MAILPIT_URL}/api/v1/messages?limit=200")
    for m in (lista or {}).get("messages", []):
        if m.get("ID") in conocidos:
            continue
        asunto = (m.get("Subject") or "").strip()
        if MARCA_ASUNTO in asunto:
            return detalle_correo(m)
    return None


def esperar_aviso(conocidos, timeout=30):
    fin = time.time() + timeout
    while time.time() < fin:
        correo = buscar_aviso(conocidos)
        if correo:
            return correo
        time.sleep(1)
    return None


def esperar_sin_aviso(conocidos, timeout=25):
    """True si en `timeout` no llega ningún aviso nuevo (criterio «NO llega aviso»)."""
    return esperar_aviso(conocidos, timeout=timeout) is None


def esperar_url(url, cabeceras=None, datos=None, timeout=120, espera=2):
    """True cuando la URL responde entre la 200/201 y no cuando 404 (webhook aún sin registrar)."""
    fin = time.time() + timeout
    ultimo = 0
    while time.time() < fin:
        estado, _ = http_json(url, metodo="GET" if datos is None else "POST", datos=datos, cabeceras=cabeceras)
        if estado in (200, 201):
            return True
        ultimo = estado
        time.sleep(espera)
    print(f"    {url} sigue sin estar disponible (último status {ultimo}) tras {timeout} s")
    return False


def webhook_datos(payload, reintentos=20, espera=2):
    """POST a la Production URL del receptor, reintentando mientras n8n arranca o registra el webhook."""
    return http_json(f"{N8N_URL}/webhook/tienda", metodo="POST", datos=payload, reintentos=reintentos, espera=espera)


def esperar_webhook(timeout=120):
    """True cuando el receptor ya atiende su Production URL (tras un arranque puede tardar)."""
    return esperar_url(f"{N8N_URL}/webhook/tienda", datos={"evento": "sonda.webhook", "datos": {}}, timeout=timeout)


def _compose(*args):
    return subprocess.run(["docker", "compose", *args], cwd=RAIZ, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=300)


def umbral_actual():
    """El umbral tal y como lo ve el flujo: la variable en el contenedor de n8n."""
    proceso = _compose("exec", "-T", "n8n", "printenv", "UMBRAL_VENTA_GRANDE")
    try:
        return int((proceso.stdout or "").strip())
    except ValueError:
        return UMBRAL_DEF


def fijar_umbral(nuevo):
    """Pone `UMBRAL_VENTA_GRANDE=nuevo` en `.env` (sin tocar el flujo) y crea el contenedor al reiniciar."""
    fichero = RAIZ / ".env"
    lineas = fichero.read_text(encoding="utf-8").splitlines()
    original = None
    for l in lineas:
        if l.strip().startswith("UMBRAL_VENTA_GRANDE="):
            original = l.split("=", 1)[1].strip()
            break
    lineas = [l for l in lineas if not l.strip().startswith("UMBRAL_VENTA_GRANDE=")]
    lineas.append(f"UMBRAL_VENTA_GRANDE={nuevo}")
    fichero.write_text("\r\n".join(lineas) + "\r\n", encoding="utf-8")
    return original


def recrear_n8n():
    """Recrea el contenedor de n8n para que lea su entorno nuevo, y espera a que responda."""
    proceso = _compose("up", "-d", "n8n")
    if proceso.returncode != 0:
        raise RuntimeError("docker compose up -d n8n falló: " + (proceso.stderr or "").strip()[:200])
    web = esperar_url(f"{N8N_URL}/healthz", timeout=120)
    hook = esperar_webhook(timeout=120)
    return web and hook


def restaurar_umbral(original):
    """Deja el `.env` como estaba (quita la línea si no existía) y recrea n8n."""
    fichero = RAIZ / ".env"
    if original is None:
        lineas = [l for l in fichero.read_text(encoding="utf-8").splitlines()
                  if not l.strip().startswith("UMBRAL_VENTA_GRANDE=")]
        fichero.write_text("\r\n".join(lineas) + "\r\n", encoding="utf-8")
    else:
        fijar_umbral(original)
    ok = recrear_n8n()
    return ok and umbral_actual() == (UMBRAL_DEF if original is None else int(original))


def guardar(nombre, contenido):
    fichero = SALIDA / nombre
    fichero.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(contenido, ensure_ascii=False, indent=2) if isinstance(contenido, (dict, list)) else str(contenido)
    fichero.write_text(texto, encoding="utf-8")


def finalizar(nombre_resumen):
    total_pass = sum(1 for r in resultados if r["resultado"] == "PASS")
    total_fail = sum(1 for r in resultados if r["resultado"] == "FAIL")
    lineas = [
        f"{r['resultado']} · {r['prueba']} · {r['criterio']}" + (f" · {r['detalle']}" if r["detalle"] else "")
        for r in resultados
    ]
    guardar(nombre_resumen, "\n".join(lineas) + f"\n\ntotal: {total_pass} PASS / {total_fail} FAIL\n")
    print(f"resumen: {total_pass} PASS / {total_fail} FAIL — evidencia en {SALIDA.relative_to(RAIZ)}")
    return 1 if total_fail else 0


def preparar_salida():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not clave_api():
        print("precondición no cumplida: falta API_KEY en el entorno o en .env")
        sys.exit(1)
    estado_tienda, _ = api_tienda("/api/apartados/resumen")
    if estado_tienda != 200:
        print(f"precondición no cumplida: la app no responde en {API_URL} (status {estado_tienda})")
        sys.exit(1)
    estado_mailpit, _ = http_json(f"{MAILPIT_URL}/api/v1/messages?limit=1")
    if estado_mailpit != 200:
        print(f"precondición no cumplida: Mailpit no responde en {MAILPIT_URL} (status {estado_mailpit})")
        sys.exit(1)
    if not esperar_webhook():
        print("precondición no cumplida: el receptor no atiende la Production URL (¿task importar?)")
        sys.exit(1)
    umbral = umbral_actual()
    print(f"  umbral efectivo en n8n: {umbral} €")
    return umbral
