#!/usr/bin/env python3
"""Escenario B — Día sin movimientos (US-04).

Con la app sin ventas ni abonos del día, el Flujo 05 no debe fallar: el cierre lo dice.

Uso:  python tests/us-04/escenario-b-sin-movimientos.py   (requiere app+n8n+mailpit; RESETEA los datos de la app)
"""

import sys
from datetime import date

import ayudantes as a

PRUEBA = "B-sin-movimientos"


def main():
    a.preparar_salida()
    a.limpiar_base()
    a.limpiar_buzon()

    conocidos = a.mensajes_actuales()
    ok, salida = a.ejecutar_flujo()
    a.guardar("escenario-b-ejecucion.txt", salida)
    a.apuntar(PRUEBA, "el flujo NO falla sin movimientos", ok, salida.splitlines()[-1] if salida else "")

    cierre = a.esperar_cierre(conocidos)
    if not cierre:
        a.apuntar(PRUEBA, "llega el correo del cierre", False, "timeout sin correo")
        return a.finalizar("resumen-escenario-b.txt")
    html = cierre.get("HTML", "")
    a.guardar("escenario-b-cierre.json", {"asunto": cierre.get("Subject"), "html": html})
    a.apuntar(PRUEBA, "llega el correo del cierre", True, cierre.get("Subject"))
    a.apuntar(PRUEBA, "el asunto lleva la fecha del día", date.today().strftime("%d/%m/%Y") in (cierre.get("Subject") or ""),
              cierre.get("Subject"))
    a.apuntar(PRUEBA, "el cuerpo avisa de que no hubo movimientos", "no hubo movimientos" in html.lower(),
              "mensaje de día vacío presente" if "no hubo movimientos" in html.lower() else "falta el aviso")
    return a.finalizar("resumen-escenario-b.txt")


if __name__ == "__main__":
    sys.exit(main())
