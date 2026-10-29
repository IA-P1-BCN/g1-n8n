#!/usr/bin/env python3
"""Escenario C — Marisa al día (US-07, criterio 3).

Ejecuta el Flujo 06 con dos apartados fuera de plazo y comprueba en Mailpit que la tienda
(`cambia-esta-direccion@paso-firme.local`) recibe el aviso con la lista de zapatos
(producto, talla, cliente y código del vale) que vuelven a ponerse a la venta.
"""

import sys
import time
from datetime import date, timedelta

import ayudantes as a

PRUEBA = "marisa-al-dia"


def main():
    a.preparar_salida()
    print("— Escenario C · Marisa recibe el aviso con la lista de zapatos que vuelven a la venta —")

    a.limpiar_base()
    a.limpiar_buzon()

    hoy = date.today()
    ap_1 = a.crear_apartado(
        "Diego Par Uno",
        "diego.par1@paso-firme.local",
        "Deportiva retro blanca",
        "43",
        79.00,
        20.00,
        fecha=hoy - timedelta(days=96),
    )
    ap_2 = a.crear_apartado(
        "Clara Par Dos",
        "clara.par2@paso-firme.local",
        "Bailarina charol roja",
        "37",
        54.00,
        15.00,
        fecha=hoy - timedelta(days=91),
    )
    time.sleep(1.5)
    conocidos = a.mensajes_actuales()

    ok_exec, salida_cli = a.ejecutar_flujo()
    a.apuntar(PRUEBA, "el Flujo 06 se ejecuta sin error", ok_exec, "n8n execute OK" if ok_exec else salida_cli[-200:])

    correo_tienda = a.esperar_correo(conocidos, a.EMAIL_TIENDA, a.ASUNTO_AVISO_MARISA)
    if not correo_tienda:
        a.apuntar(PRUEBA, "Marisa recibe el aviso en el correo de la tienda", False, "timeout esperando aviso en Mailpit")
        sys.exit(a.finalizar("resumen-escenario-c.txt"))

    html = correo_tienda.get("HTML") or correo_tienda.get("Text") or ""
    asunto = correo_tienda.get("Subject") or ""
    codigo_1 = f"VALE-{ap_1['id']:05d}"
    codigo_2 = f"VALE-{ap_2['id']:05d}"

    a.guardar("escenario-c-marisa-al-dia.json", {
        "apartados_vencidos": [ap_1, ap_2],
        "correo_marisa": {
            "id": a.identificador(correo_tienda),
            "asunto": asunto,
            "to": correo_tienda.get("To"),
            "html": html,
        },
    })

    a.apuntar(
        PRUEBA,
        "Marisa recibe el aviso en el correo de la tienda",
        True,
        asunto,
    )
    a.apuntar(
        PRUEBA,
        "el aviso incluye el primer par de zapatos (producto, talla, cliente y vale) que vuelve a la venta",
        "Deportiva retro blanca" in html and "43" in html and "Diego Par Uno" in html and codigo_1 in html,
        f"{ap_1['producto']} (talla {ap_1['talla']}) · {codigo_1}",
    )
    a.apuntar(
        PRUEBA,
        "el aviso incluye el segundo par de zapatos (producto, talla, cliente y vale) que vuelve a la venta",
        "Bailarina charol roja" in html and "37" in html and "Clara Par Dos" in html and codigo_2 in html,
        f"{ap_2['producto']} (talla {ap_2['talla']}) · {codigo_2}",
    )

    sys.exit(a.finalizar("resumen-escenario-c.txt"))


if __name__ == "__main__":
    main()
