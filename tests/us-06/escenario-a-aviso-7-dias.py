#!/usr/bin/env python3
"""Escenario A — Aviso con 7 días de antelación (US-06, criterio 1).

Crea un apartado activo cuya fecha límite es dentro de 7 días (`hoy - 83 días`, plazo 90 días)
y otro de control que vence en 20 días. Ejecuta el Flujo 06 y comprueba que solo el cliente
de 7 días recibe el recordatorio con el importe pendiente y la fecha límite de la app.
"""

import sys
import time
from datetime import date, timedelta

import ayudantes as a

PRUEBA = "aviso-7-dias"


def main():
    a.preparar_salida()
    print("— Escenario A · Recordatorio de vencimiento a 7 días —")

    a.limpiar_base()
    a.limpiar_buzon()

    hoy = date.today()
    ap_7d = a.crear_apartado(
        "Elena Siete Días",
        "elena.7d@paso-firme.local",
        "Botín piel marrón",
        "38",
        89.90,
        20.00,
        fecha=hoy - timedelta(days=83),
    )
    ap_control = a.crear_apartado(
        "Carlos Veinte Días",
        "carlos.20d@paso-firme.local",
        "Mocasín ante",
        "41",
        72.00,
        15.00,
        fecha=hoy - timedelta(days=70),
    )
    # Esperar brevemente a que el receptor procese las confirmaciones del Flujo 01
    time.sleep(1.5)
    conocidos = a.mensajes_actuales()

    ok_exec, salida_cli = a.ejecutar_flujo()
    a.apuntar(PRUEBA, "el Flujo 06 se ejecuta sin error", ok_exec, "n8n execute OK" if ok_exec else salida_cli[-200:])

    correo = a.esperar_recordatorio(conocidos, "elena.7d@paso-firme.local", a.ASUNTO_7D)
    if not correo:
        a.apuntar(PRUEBA, "el cliente que vence en 7 días recibe el correo de recordatorio", False, "timeout esperando correo")
        sys.exit(a.finalizar("resumen-escenario-a.txt"))

    html = correo.get("HTML") or correo.get("Text") or ""
    fecha_limite_iso = ap_7d["fecha_limite"]
    fecha_limite_es = "/".join(reversed(fecha_limite_iso.split("-")))
    pendiente_str_1 = f"{ap_7d['pendiente']:.2f}"
    pendiente_str_2 = str(ap_7d["pendiente"])

    nuevos = a.recordatorios_nuevos(conocidos)
    enviado_a_control = any("carlos.20d@paso-firme.local" in m["to"] for m in nuevos)

    a.guardar("escenario-a-aviso-7-dias.json", {
        "apartado_7d": ap_7d,
        "apartado_control_20d": ap_control,
        "correo_recibido": {
            "id": a.identificador(correo),
            "asunto": correo.get("Subject"),
            "to": correo.get("To"),
            "html": html,
        },
        "recordatorios_emitidos": nuevos,
    })

    a.apuntar(
        PRUEBA,
        "el cliente que vence en 7 días recibe el correo de recordatorio",
        True,
        correo.get("Subject", ""),
    )
    a.apuntar(
        PRUEBA,
        "el mensaje incluye lo que falta por pagar (pendiente exacto de la app)",
        (pendiente_str_1 in html or pendiente_str_2 in html) and "Botín piel marrón" in html,
        f"pendiente={ap_7d['pendiente']} €",
    )
    a.apuntar(
        PRUEBA,
        "el mensaje incluye la fecha límite del apartado",
        fecha_limite_es in html or fecha_limite_iso in html,
        f"fecha_limite={fecha_limite_es} ({fecha_limite_iso})",
    )
    a.apuntar(
        PRUEBA,
        "un apartado que vence en 20 días NO recibe recordatorio",
        not enviado_a_control,
        f"recordatorios_emitidos={len(nuevos)}",
    )

    sys.exit(a.finalizar("resumen-escenario-a.txt"))


if __name__ == "__main__":
    main()
