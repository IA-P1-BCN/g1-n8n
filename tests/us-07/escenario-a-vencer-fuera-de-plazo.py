#!/usr/bin/env python3
"""Escenario A — Vencer un fuera de plazo (US-07, criterio 1).

Ejecuta el Flujo 06 con un apartado `activo` cuya `fecha_limite` ya pasó (`hoy - 95 días`,
plazo 90 días) y otro de control en plazo (`hoy - 30 días`). Comprueba por API que el apartado
fuera de plazo queda en estado `vencido`, que la app ha generado el `vale` correspondiente y
que el apartado en plazo permanece `activo`.
"""

import sys
import time
from datetime import date, timedelta

import ayudantes as a

PRUEBA = "vencer-fuera-de-plazo"


def main():
    a.preparar_salida()
    print("— Escenario A · Vencer un apartado fuera de plazo y generar su vale —")

    a.limpiar_base()
    a.limpiar_buzon()

    hoy = date.today()
    ap_fuera_plazo = a.crear_apartado(
        "Raúl Fuera De Plazo",
        "raul.vencido@paso-firme.local",
        "Zapato Oxford negro",
        "42",
        95.00,
        25.00,
        fecha=hoy - timedelta(days=95),
    )
    ap_en_plazo = a.crear_apartado(
        "Marta En Plazo",
        "marta.enplazo@paso-firme.local",
        "Sandalia cuña esparto",
        "38",
        59.90,
        15.00,
        fecha=hoy - timedelta(days=30),
    )
    time.sleep(1.0)

    ok_exec, salida_cli = a.ejecutar_flujo()
    a.apuntar(PRUEBA, "el Flujo 06 se ejecuta sin error", ok_exec, "n8n execute OK" if ok_exec else salida_cli[-200:])

    _, detalle_vencido = a.api_tienda(f"/api/apartados/{ap_fuera_plazo['id']}")
    _, detalle_en_plazo = a.api_tienda(f"/api/apartados/{ap_en_plazo['id']}")
    _, lista_vales = a.api_tienda("/api/vales")
    vales = lista_vales if isinstance(lista_vales, list) else []

    codigo_esperado = f"VALE-{ap_fuera_plazo['id']:05d}"
    vale_generado = next((v for v in vales if v.get("apartado_id") == ap_fuera_plazo["id"]), None)

    a.guardar("escenario-a-vencer-fuera-de-plazo.json", {
        "apartado_fuera_de_plazo_antes": ap_fuera_plazo,
        "apartado_fuera_de_plazo_despues": detalle_vencido,
        "apartado_en_plazo_despues": detalle_en_plazo,
        "vales_en_api": vales,
    })

    a.apuntar(
        PRUEBA,
        "el apartado fuera de plazo pasa a estado 'vencido' en la API",
        isinstance(detalle_vencido, dict) and detalle_vencido.get("estado") == "vencido",
        f"id={ap_fuera_plazo['id']} estado={detalle_vencido.get('estado') if isinstance(detalle_vencido, dict) else detalle_vencido}",
    )
    a.apuntar(
        PRUEBA,
        "la app ha generado el vale del apartado vencido con el importe abonado",
        vale_generado is not None
        and vale_generado.get("codigo") == codigo_esperado
        and float(vale_generado.get("importe", -1)) == float(ap_fuera_plazo["abonado"]),
        f"vale={vale_generado}",
    )
    a.apuntar(
        PRUEBA,
        "el apartado dentro de plazo permanece en estado 'activo'",
        isinstance(detalle_en_plazo, dict) and detalle_en_plazo.get("estado") == "activo",
        f"id={ap_en_plazo['id']} estado={detalle_en_plazo.get('estado') if isinstance(detalle_en_plazo, dict) else detalle_en_plazo}",
    )

    sys.exit(a.finalizar("resumen-escenario-a.txt"))


if __name__ == "__main__":
    main()
