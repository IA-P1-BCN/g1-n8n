#!/usr/bin/env python3
"""Escenario B — Cliente con su vale (US-07, criterio 2).

Ejecuta el Flujo 06 con un apartado fuera de plazo y comprueba en Mailpit que el correo
enviado al cliente incluye el código (p. ej. `VALE-00001`) y el importe del vale generado.
"""

import sys
import time
from datetime import date, timedelta

import ayudantes as a

PRUEBA = "cliente-con-su-vale"


def main():
    a.preparar_salida()
    print("— Escenario B · Cliente recibe el correo con el código y el importe de su vale —")

    a.limpiar_base()
    a.limpiar_buzon()

    hoy = date.today()
    ap = a.crear_apartado(
        "Sofía Cliente Vale",
        "sofia.vale@paso-firme.local",
        "Bota alta piel negra",
        "39",
        110.00,
        35.50,
        fecha=hoy - timedelta(days=92),
    )
    time.sleep(1.5)
    conocidos = a.mensajes_actuales()

    ok_exec, salida_cli = a.ejecutar_flujo()
    a.apuntar(PRUEBA, "el Flujo 06 se ejecuta sin error", ok_exec, "n8n execute OK" if ok_exec else salida_cli[-200:])

    _, lista_vales = a.api_tienda("/api/vales")
    vales = lista_vales if isinstance(lista_vales, list) else []
    vale = next((v for v in vales if v.get("apartado_id") == ap["id"]), None)
    codigo_vale = vale.get("codigo") if vale else f"VALE-{ap['id']:05d}"

    correo = a.esperar_correo(conocidos, "sofia.vale@paso-firme.local", a.ASUNTO_VALE_CLIENTE)
    if not correo:
        a.apuntar(PRUEBA, "el cliente recibe el correo con su vale", False, "timeout esperando correo en Mailpit")
        sys.exit(a.finalizar("resumen-escenario-b.txt"))

    html = correo.get("HTML") or correo.get("Text") or ""
    asunto = correo.get("Subject") or ""
    importe_1 = f"{ap['abonado']:.2f}"
    importe_2 = str(ap["abonado"])

    a.guardar("escenario-b-cliente-con-su-vale.json", {
        "apartado": ap,
        "vale": vale,
        "correo_cliente": {
            "id": a.identificador(correo),
            "asunto": asunto,
            "to": correo.get("To"),
            "html": html,
        },
    })

    a.apuntar(
        PRUEBA,
        "el cliente recibe el correo de apartado vencido con su vale",
        True,
        asunto,
    )
    a.apuntar(
        PRUEBA,
        "el mensaje incluye el código del vale generado por la app",
        codigo_vale in html or codigo_vale in asunto,
        f"codigo={codigo_vale}",
    )
    a.apuntar(
        PRUEBA,
        "el mensaje incluye el importe del vale (igual a lo abonado)",
        importe_1 in html or importe_2 in html,
        f"importe={ap['abonado']} €",
    )

    sys.exit(a.finalizar("resumen-escenario-b.txt"))


if __name__ == "__main__":
    main()
