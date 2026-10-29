#!/usr/bin/env python3
"""Escenario B — Aviso con 1 día de antelación (US-06, criterio 2).

Crea un apartado activo cuya fecha límite es mañana (`hoy - 89 días`, plazo 90 días),
ejecuta el Flujo 06 y comprueba que el cliente recibe el recordatorio de 1 día con el
importe pendiente y la fecha límite.
"""

import sys
import time
from datetime import date, timedelta

import ayudantes as a

PRUEBA = "aviso-1-dia"


def main():
    a.preparar_salida()
    print("— Escenario B · Recordatorio de vencimiento a 1 día (mañana) —")

    hoy = date.today()
    ap_1d = a.crear_apartado(
        "Marcos Un Día",
        "marcos.1d@paso-firme.local",
        "Zapatilla running azul",
        "42",
        64.50,
        15.00,
        fecha=hoy - timedelta(days=89),
    )
    time.sleep(1.5)
    conocidos = a.mensajes_actuales()

    ok_exec, salida_cli = a.ejecutar_flujo()
    a.apuntar(PRUEBA, "el Flujo 06 se ejecuta sin error", ok_exec, "n8n execute OK" if ok_exec else salida_cli[-200:])

    correo = a.esperar_recordatorio(conocidos, "marcos.1d@paso-firme.local", a.ASUNTO_1D)
    if not correo:
        a.apuntar(PRUEBA, "el cliente que vence mañana (1 día) recibe el aviso", False, "timeout esperando correo")
        sys.exit(a.finalizar("resumen-escenario-b.txt"))

    html = correo.get("HTML") or correo.get("Text") or ""
    fecha_limite_iso = ap_1d["fecha_limite"]
    fecha_limite_es = "/".join(reversed(fecha_limite_iso.split("-")))
    pendiente_str_1 = f"{ap_1d['pendiente']:.2f}"
    pendiente_str_2 = str(ap_1d["pendiente"])

    a.guardar("escenario-b-aviso-1-dia.json", {
        "apartado_1d": ap_1d,
        "correo_recibido": {
            "id": a.identificador(correo),
            "asunto": correo.get("Subject"),
            "to": correo.get("To"),
            "html": html,
        },
    })

    a.apuntar(
        PRUEBA,
        "el cliente que vence mañana (1 día) recibe el aviso",
        True,
        correo.get("Subject", ""),
    )
    a.apuntar(
        PRUEBA,
        "el mensaje incluye el importe pendiente exacto de la app",
        (pendiente_str_1 in html or pendiente_str_2 in html) and "Zapatilla running azul" in html,
        f"pendiente={ap_1d['pendiente']} €",
    )
    a.apuntar(
        PRUEBA,
        "el mensaje incluye la fecha límite de mañana",
        fecha_limite_es in html or fecha_limite_iso in html,
        f"fecha_limite={fecha_limite_es} ({fecha_limite_iso})",
    )

    sys.exit(a.finalizar("resumen-escenario-b.txt"))


if __name__ == "__main__":
    main()
