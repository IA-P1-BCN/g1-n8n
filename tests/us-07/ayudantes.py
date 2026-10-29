"""Apartados vencidos con su vale · US-07 (Flujo 06 · Recordatorios de vencimiento) contra el stack local.

Suite de `tests/us-07/`, un script por escenario de aceptación de la historia #52.
Ejecuta el flujo por CLI en el contenedor de n8n (`n8n execute --id=pFlujo06RecordatoriosVencimiento`),
comprueba en la API de la tienda (`http://localhost:8000`) que los apartados fuera de plazo pasan a
`vencido` y generan su `vale`, y verifica en Mailpit (`http://localhost:8025`) el correo enviado al
cliente con el código e importe del vale y el aviso a Marisa con los zapatos que vuelven a la venta.
La evidencia del output de cada test queda versionada en `docs/evidencia/us-07/`.
"""

import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

FLUJO_ID = os.environ.get("N8N_FLUJO_06_ID", "pFlujo06RecordatoriosVencimiento")
NOMBRE_FLUJO = "Flujo 06 · Recordatorios de vencimiento"
API_URL = (os.environ.get("API_URL") or "http://localhost:8000").rstrip("/")
MAILPIT_URL = (os.environ.get("MAILPIT_URL") or "http://localhost:8025").rstrip("/")
EMAIL_TIENDA = "cambia-esta-direccion@paso-firme.local"
ASUNTO_VALE_CLIENTE = "Tu vale por apartado vencido"
ASUNTO_AVISO_MARISA = "vuelven a la venta"
RAIZ = pathlib.Path(__file__).resolve().parents[2]
SALIDA = RAIZ / "docs" / "evidencia" / "us-07"

resultados = []


def apuntar(prueba, criterio, ok, detalle=""):
    resultados.append({
        "prueba": prueba,
        "criterio": criterio,
        "resultado": "PASS" if ok else "FAIL",
        "detalle": detalle,
    })
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


def crear_apartado(cliente, email, producto, talla, precio, abono_inicial, fecha):
    datos = {
        "cliente": cliente,
        "email": email,
        "producto": producto,
        "talla": talla,
        "precio": precio,
        "abono_inicial": abono_inicial,
        "forma_pago": "efectivo",
        "fecha": fecha.isoformat(),
    }
    estado, resp = api_tienda("/api/apartados", metodo="POST", datos=datos)
    if estado != 201:
        raise RuntimeError(f"Error creando apartado de {cliente} ({estado}): {resp}")
    return resp


def limpiar_base():
    """Vacía apartados, abonos, ventas y vales en el contenedor `tienda` (sin tocar n8n)."""
    orden = [
        "docker", "compose", "exec", "-T", "tienda", "python", "-c",
        "import sqlite3, config; con = sqlite3.connect(config.DB_PATH); "
        "con.executescript('DELETE FROM vales; DELETE FROM abonos; DELETE FROM ventas; DELETE FROM apartados;'); "
        "con.commit(); con.close()",
    ]
    proceso = subprocess.run(orden, cwd=RAIZ, capture_output=True, text=True, timeout=30)
    if proceso.returncode != 0:
        raise RuntimeError(proceso.stderr.strip() or proceso.stdout.strip() or "no se pudo limpiar la base de datos")


def limpiar_buzon():
    """Vacía el buzón de Mailpit para aislar las pruebas."""
    http_json(f"{MAILPIT_URL}/api/v1/messages", metodo="DELETE")


def ejecutar_flujo():
    """Dispara el Flujo 06 en el contenedor `n8n` mediante el CLI de n8n."""
    orden = [
        "docker", "compose", "exec", "-T",
        "-e", "N8N_RUNNERS_BROKER_PORT=5689",
        "n8n", "n8n", "execute", f"--id={FLUJO_ID}",
    ]
    proceso = subprocess.run(
        orden,
        cwd=RAIZ,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
    )
    salida = (proceso.stdout or "") + ("\n" + proceso.stderr if proceso.stderr else "")
    return proceso.returncode == 0, salida.strip()


def identificador(m):
    return m.get("ID") or m.get("Id")


def destinatarios(m):
    return [d.get("Address", "") for d in (m.get("To") or [])]


def mensajes_actuales():
    _, lista = http_json(f"{MAILPIT_URL}/api/v1/messages?limit=200")
    return {identificador(m) for m in (lista or {}).get("messages", [])}


def esperar_correo(conocidos, email_destino, marca_asunto, timeout=25):
    fin = time.time() + timeout
    while time.time() < fin:
        _, lista = http_json(f"{MAILPIT_URL}/api/v1/messages?limit=200")
        for m in (lista or {}).get("messages", []):
            if identificador(m) in conocidos:
                continue
            asunto = (m.get("Subject") or "").strip()
            if marca_asunto in asunto and email_destino in destinatarios(m):
                _, detalle = http_json(f"{MAILPIT_URL}/api/v1/message/{identificador(m)}")
                return detalle
        time.sleep(1)
    return None


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
