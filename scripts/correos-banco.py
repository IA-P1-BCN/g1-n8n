#!/usr/bin/env python3
"""Carga en Mailpit los avisos del banco de `data/correos/` (run: task correos).

Cada `.eml` es un aviso de un banco ficticio («Banco Ejemplo», dominio reservado `.example`):
Bizum, transferencia o publicidad, con su importe, ordenante y concepto. El script lo lee y lo
entrega a Mailpit por su API (`POST /api/v1/send`, el SMTP no está publicado al host) con el mismo
remitente, destinatario, asunto y cuerpo. Así el buzón de pruebas tiene los correos que leerá el
Flujo 03 (abonos a distancia) sin depender de un banco ni de una cuenta real.

Al final se comprueba que cada correo está en el buzón y se imprime la tabla (correo → remitente → importe).

Uso:  python scripts/correos-banco.py
      python scripts/correos-banco.py --limpio
      python scripts/correos-banco.py --solo 01,03
      variables: MAILPIT_URL (http://localhost:8025)
Exit code: 0 correos cargados · 1 algún correo no se pudo cargar o no aparece en el buzón.
"""

import argparse
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request
from email.utils import parseaddr

RAIZ = pathlib.Path(__file__).resolve().parents[1]
CORREOS = RAIZ / "data" / "correos"
MAILPIT_URL = (os.environ.get("MAILPIT_URL") or "http://localhost:8025").rstrip("/")


def leer_eml(fichero):
    """Cabeceras y cuerpo de un `.eml` de texto plano (sin MIME: así vienen los del banco)."""
    texto = fichero.read_text(encoding="utf-8").replace("\r\n", "\n")
    cabecera, _, cuerpo = texto.partition("\n\n")
    cabeceras = {}
    for linea in cabecera.splitlines():
        nombre, _, valor = linea.partition(":")
        cabeceras[nombre.strip().lower()] = valor.strip()
    return cabeceras, cuerpo.strip() + "\n"


def importe_de(cuerpo):
    """El importe del aviso tal como lo escribe el banco («10,00 EUR»), o «—» si no es un pago."""
    encontrado = re.search(r"Importe\W*([\d.,]+\s*EUR)", cuerpo)
    return encontrado.group(1) if encontrado else "—"


def direccion(cabecera):
    nombre, email = parseaddr(cabecera)
    return {"Email": email, "Name": nombre}


def mailpit(metodo, ruta, datos=None):
    """Petición a la API de Mailpit; devuelve (estado, cuerpo)."""
    cuerpo = json.dumps(datos, ensure_ascii=False).encode() if datos is not None else None
    peticion = urllib.request.Request(f"{MAILPIT_URL}/api/v1{ruta}", cuerpo, method=metodo,
                                      headers={"Content-Type": "application/json"} if cuerpo else {})
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


def enviar(fichero):
    """Entrega un aviso a Mailpit; devuelve (id del mensaje, remitente, asunto, importe) o lanza error."""
    cabeceras, cuerpo = leer_eml(fichero)
    correo = {
        "From": direccion(cabeceras["from"]),
        "To": [direccion(cabeceras["to"])],
        "Subject": cabeceras["subject"],
        "Text": cuerpo,
    }
    estado, respuesta = mailpit("POST", "/send", correo)
    if estado != 200 or not respuesta.get("ID"):
        raise RuntimeError(f"{fichero.name}: Mailpit respondió {estado} · {respuesta}")
    return respuesta["ID"], cabeceras["from"], cabeceras["subject"], importe_de(cuerpo)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Carga en Mailpit los avisos del banco de data/correos/.")
    parser.add_argument("--limpio", action="store_true", help="vacía antes el buzón de Mailpit")
    parser.add_argument("--solo", default="", help="solo esos correos, por prefijo (ej. --solo 01,03)")
    args = parser.parse_args()

    prefijos = [p.strip() for p in args.solo.split(",") if p.strip()]
    ficheros = [f for f in sorted(CORREOS.glob("*.eml")) if not prefijos or f.name.split("_")[0] in prefijos]
    if not ficheros:
        print(f"ERROR: no hay correos que cargar en {CORREOS} (--solo {args.solo or '—'})", file=sys.stderr)
        return 1

    estado, _ = mailpit("GET", "/info")
    if estado != 200:
        print(f"ERROR: Mailpit no responde en {MAILPIT_URL} (¿task arrancar?)", file=sys.stderr)
        return 1
    print(f"· Mailpit: {MAILPIT_URL}")

    if args.limpio:
        estado, _ = mailpit("DELETE", "/messages")
        if estado != 200:
            print(f"ERROR: no se pudo vaciar el buzón (status {estado})", file=sys.stderr)
            return 1
        print("· limpio: buzón de Mailpit vaciado")

    cargados, fallos = [], 0
    for fichero in ficheros:
        try:
            cargados.append((fichero.stem, *enviar(fichero)))
        except (RuntimeError, KeyError) as e:
            fallos += 1
            print(f"  [FAIL] {e}", file=sys.stderr)

    # Comprobación: cada correo cargado se puede leer de vuelta en el buzón.
    print("\n· Avisos del banco en Mailpit (correo → remitente → importe → asunto):")
    en_buzon = 0
    for nombre, id_mensaje, remitente, asunto, importe in cargados:
        estado, mensaje = mailpit("GET", f"/message/{id_mensaje}")
        ok = estado == 200 and mensaje.get("Subject") == asunto
        en_buzon += ok
        print(f"  [{'OK' if ok else 'FAIL'}] {nombre:<30} {remitente:<52} {importe:>10}  {asunto}")

    print(f"\n· {en_buzon}/{len(ficheros)} correos en el buzón · ver {MAILPIT_URL}")
    return 0 if en_buzon == len(ficheros) and not fallos else 1


if __name__ == "__main__":
    sys.exit(main())
