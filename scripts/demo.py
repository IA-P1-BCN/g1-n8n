#!/usr/bin/env python3
"""Crea los datos de la demo en la app por API (run: task demo).

Deja la tienda lista para la demo sin apuntar nada a mano:

- un **apartado nuevo** con su abono inicial y abonos parciales **hasta liquidarlo**;
- un apartado **a punto de vencer** (dentro de plazo, unos días);
- un apartado **vencido con su vale**;
- **ventas del día** por las tres formas de pago.

Todos los POST pasan por la API, así que también disparan el webhook: las confirmaciones y recibos
de los flujos 01/02 aparecen en Mailpit. Al final se comprueba con GET lo creado y se imprime una
**guía rápida** de los escenarios (qué apartado o venta prueba cada flujo y dónde mirarlo).

Con `--limpio` vacía antes la base de datos de la app y el buzón de Mailpit (el stack de Docker
tiene que estar levantado; no toca n8n), para empezar de cero.

Uso:  python scripts/demo.py
      python scripts/demo.py --limpio
      variables: API_URL (http://localhost:8000), API_KEY (entorno o .env), MAILPIT_URL (http://localhost:8025)
Exit code: 0 demo lista · 1 algún paso o la comprobación falló.
"""

import argparse
import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta

RAIZ = pathlib.Path(__file__).resolve().parents[1]
API_URL = (os.environ.get("API_URL") or "http://localhost:8000").rstrip("/")
MAILPIT_URL = (os.environ.get("MAILPIT_URL") or "http://localhost:8025").rstrip("/")


def clave_api():
    """Clave de la API de la tienda: entorno o `.env` del repo (nunca escrita en el script)."""
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


def api(metodo, ruta, datos=None, esperados=(200, 201)):
    """Petición a la app; devuelve (estado, cuerpo)."""
    cuerpo = None
    cabeceras = {"X-API-Key": clave_api()}
    if datos is not None:
        cuerpo = json.dumps(datos, ensure_ascii=False).encode()
        cabeceras["Content-Type"] = "application/json"
    peticion = urllib.request.Request(f"{API_URL}{ruta}", cuerpo, cabeceras, method=metodo)
    try:
        with urllib.request.urlopen(peticion, timeout=10) as r:
            estado, texto = r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        estado, texto = e.code, e.read().decode()
    except Exception as e:
        return 0, {"detail": f"la app no responde en {API_URL} ({e})"}
    try:
        respuesta = json.loads(texto or "{}")
    except json.JSONDecodeError:
        respuesta = {"detail": texto}
    return estado, respuesta


def paso(metodo, ruta, datos, esperados, que):
    """Petición que tiene que salir bien; si no, se para la demo con el mensaje de la API."""
    estado, respuesta = api(metodo, ruta, datos, esperados)
    if estado not in esperados:
        detalle = respuesta.get("detail") if isinstance(respuesta, dict) else respuesta
        print(f"ERROR: {que} (status {estado}): {detalle}", file=sys.stderr)
        sys.exit(1)
    return respuesta


def crear_apartado(cliente, email, producto, talla, precio, abono_inicial, forma_pago, fecha=None):
    datos = {"cliente": cliente, "email": email, "producto": producto, "talla": talla, "precio": precio,
             "abono_inicial": abono_inicial, "forma_pago": forma_pago}
    if fecha:
        datos["fecha"] = fecha.isoformat()
    return paso("POST", "/api/apartados", datos, (201,), f"crear el apartado de {cliente}")


def abonar(apartado_id, importe, forma_pago):
    return paso("POST", f"/api/apartados/{apartado_id}/abonos", {"importe": importe, "forma_pago": forma_pago},
                (201,), f"abonar {importe} € al apartado {apartado_id}")


def vender(concepto, importe, forma_pago):
    return paso("POST", "/api/ventas", {"concepto": concepto, "importe": importe, "forma_pago": forma_pago},
                (201,), f"registrar la venta de {concepto}")


def limpiar_base():
    """Vacía apartados, abonos, ventas y vales. Usa el propio contenedor de la app: no toca n8n."""
    orden = ["docker", "compose", "exec", "-T", "tienda", "python", "-c",
             "import sqlite3, config; con = sqlite3.connect(config.DB_PATH); "
             "con.executescript('DELETE FROM vales; DELETE FROM abonos; DELETE FROM ventas; DELETE FROM apartados;'); "
             "con.commit(); con.close()"]
    try:
        proceso = subprocess.run(orden, cwd=RAIZ, capture_output=True, text=True, timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return f"no se pudo ejecutar docker compose ({e})"
    if proceso.returncode != 0:
        return proceso.stderr.strip() or proceso.stdout.strip() or "docker compose exec falló"
    return None


def limpiar_buzon():
    """Vacía Mailpit; si no está disponible no es un fallo (solo avisa)."""
    peticion = urllib.request.Request(f"{MAILPIT_URL}/api/v1/messages", method="DELETE")
    try:
        with urllib.request.urlopen(peticion, timeout=5) as r:
            return r.status < 300
    except Exception:
        return False


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Crea los datos de la demo por API.")
    parser.add_argument("--limpio", action="store_true",
                        help="vacía antes la base de datos de la app y Mailpit (empezar de cero)")
    args = parser.parse_args()

    if not clave_api():
        print("ERROR: falta API_KEY en el entorno o en .env (la app la exige en la cabecera X-API-Key)", file=sys.stderr)
        return 1

    if args.limpio:
        if API_URL != "http://localhost:8000":
            print(f"ERROR: «--limpio» solo funciona con el stack local de docker compose "
                  f"(API_URL es {API_URL})", file=sys.stderr)
            return 1
        error = limpiar_base()
        if error:
            print(f"ERROR: no se pudo vaciar la base de datos: {error}", file=sys.stderr)
            return 1
        print("· limpio: base de datos de la app vaciada")
        print("· limpio: buzón de Mailpit vaciado" if limpiar_buzon() else "· aviso: Mailpit no responde, no vacío el buzón")

    hoy = date.today()
    print(f"· API: {API_URL}")

    # 1. Apartado nuevo con abono inicial + abonos parciales hasta liquidarlo (Flujo 01 y Flujo 02).
    liquidado = crear_apartado("Marisa Demo", "demo.liquidado@paso-firme.local", "Botín piel marrón", "38",
                               89.90, 10.00, "efectivo")
    abonos = [("efectivo", 10.00)]
    for importe, forma in [(30.00, "tarjeta"), (None, "bizum")]:
        importe = importe if importe is not None else liquidado["pendiente"]
        liquidado = abonar(liquidado["id"], importe, forma)
        abonos.append((forma, importe))
    print(f"· apartado liquidado: #{liquidado['id']} · {liquidado['cliente']} · {liquidado['estado']} · "
          f"pendiente {liquidado['pendiente']:.2f} €")
    print("  abonos: " + " · ".join(f"{importe:.2f} € {forma}" for forma, importe in abonos))

    # 2. Apartado a punto de vencer: nació hace 83 días, el plazo son 90 (vence en 7 días → Flujo 06).
    por_vencer = crear_apartado("Cliente Demo Por Vencer", "demo.porvencer@paso-firme.local",
                                "Zapatilla running azul", "42", 64.50, 15.00, "efectivo",
                                fecha=hoy - timedelta(days=83))
    por_vencer = abonar(por_vencer["id"], 20.00, "tarjeta")
    dias = (date.fromisoformat(por_vencer["fecha_limite"]) - hoy).days
    print(f"· apartado por vencer: #{por_vencer['id']} · vence el {por_vencer['fecha_limite']} ({dias} días) · "
          f"pendiente {por_vencer['pendiente']:.2f} €")

    # 3. Apartado fuera de plazo, para ver el vale.
    vencido = crear_apartado("Cliente Demo Vencido", "demo.vencido@paso-firme.local",
                             "Sandalia tacón negra", "39", 45.00, 20.00, "efectivo",
                             fecha=hoy - timedelta(days=100))
    resultado = paso("POST", f"/api/apartados/{vencido['id']}/vencer", None, (200,),
                     f"vencer el apartado {vencido['id']}")
    vale = resultado["vale"]
    print(f"· apartado vencido: #{vencido['id']} · vale {vale['codigo']} por {vale['importe']:.2f} €")

    # 4. Ventas del día, una por forma de pago.
    ventas = [
        vender("Calcetines pack 3", 6.50, "efectivo"),
        vender("Zapatilla running azul · 42", 64.50, "tarjeta"),
        vender("Plantillas gel", 12.00, "bizum"),
    ]
    print("· ventas de hoy: " + " · ".join(f"#{v['id']} {v['importe']:.2f} € {v['forma_pago']}" for v in ventas))

    # 5. Comprobación: la API devuelve lo creado (apartado liquidado, sus abonos, vale y ventas de hoy).
    detalle = paso("GET", f"/api/apartados/{liquidado['id']}", None, (200,), "leer el apartado liquidado")
    sin_abonos = len(detalle["abonos"]) != len(abonos)
    mal_liquidado = detalle["estado"] != "liquidado" or detalle["pendiente"] != 0
    _, hoy_ventas = api("GET", f"/api/ventas?desde={hoy}&hasta={hoy}")
    ids_ventas = {v["id"] for v in hoy_ventas} if isinstance(hoy_ventas, list) else set()
    _, vales = api("GET", "/api/vales")
    ids_vales = {v["id"] for v in vales} if isinstance(vales, list) else set()
    _, resumen = api("GET", "/api/apartados/resumen")

    if sin_abonos or mal_liquidado:
        print(f"ERROR: el apartado {liquidado['id']} no quedó como se esperaba: {detalle}", file=sys.stderr)
        return 1
    if not {v["id"] for v in ventas} <= ids_ventas:
        print("ERROR: las ventas de hoy no aparecen en la API", file=sys.stderr)
        return 1
    if vale["id"] not in ids_vales:
        print(f"ERROR: el vale {vale['codigo']} no aparece en la API", file=sys.stderr)
        return 1

    # 6. Guía rápida: qué escenario prueba cada flujo y dónde mirarlo.
    print(f"· resumen: {resumen.get('activo')} activos · {resumen.get('liquidado')} liquidados · "
          f"{resumen.get('vencido')} vencidos · {resumen.get('total')} apartados")
    print("· Guía rápida de la demo:")
    print(f"    apartado #{liquidado['id']} · liquidado en 3 abonos · Flujo 01 (confirmación) y Flujo 02 (recibos) → Mailpit")
    print(f"    apartado #{por_vencer['id']} · vence en {dias} días · Flujo 06 (recordatorio de vencimiento) + recibo de su abono (Flujo 02)")
    print(f"    apartado #{vencido['id']} · vencido con vale {vale['codigo']} · Flujo 06 (vencimiento por API, vale al cliente y zapatos que vuelven a la venta)")
    print("    ventas #" + ", #".join(str(v["id"]) for v in ventas) +
          " · efectivo, tarjeta y bizum · Flujo 05 (cierre diario; ejecútalo a mano en n8n o espera a las 22:00) → Mailpit")
    print("    CSV de data/ · migración del Excel antiguo · Flujo 09 (ejecución manual en n8n) → app + informe de dudosos en Mailpit")
    print(f"    app {API_URL} · API {API_URL}/docs · correos {MAILPIT_URL}")
    print("· Prueba un evento a mano (para retocar o añadir algo fácil):")
    print("    task payload -- payloads/venta-registrada.json --esperar")
    print("    (duplica un fichero de payloads/, retócalo y lánzalo igual)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
