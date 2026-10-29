#!/usr/bin/env python3
"""Escenario B — Sin duplicados al re-ejecutar el flujo (US-10, criterios de idempotencia).

Comprueba que al volver a ejecutar el Flujo 09 completo sobre una base ya migrada no se duplica
ningún apartado, abono ni venta.
"""

import sys

import ayudantes as a

PRUEBA = "sin-duplicados"


def main():
    a.preparar_salida()
    print("— Escenario B · Re-ejecución sin duplicados —")

    _, apartados_antes = a.api_tienda("/api/apartados")
    if not isinstance(apartados_antes, list) or len(apartados_antes) != 7:
        a.limpiar_base()
        a.ejecutar_migracion()
        _, apartados_antes = a.api_tienda("/api/apartados")

    _, abonos_antes = a.api_tienda("/api/abonos")
    _, ventas_antes = a.api_tienda("/api/ventas")

    ok_exec, salida_cli = a.ejecutar_migracion()
    a.apuntar(PRUEBA, "la segunda ejecución del Flujo 09 termina sin error", ok_exec, "n8n execute OK" if ok_exec else salida_cli[-200:])

    _, apartados_despues = a.api_tienda("/api/apartados")
    _, abonos_despues = a.api_tienda("/api/abonos")
    _, ventas_despues = a.api_tienda("/api/ventas")

    apartados_despues = apartados_despues if isinstance(apartados_despues, list) else []
    abonos_despues = abonos_despues if isinstance(abonos_despues, list) else []
    ventas_despues = ventas_despues if isinstance(ventas_despues, list) else []

    a.guardar("escenario-b-sin-duplicados.json", {
        "antes": {
            "apartados": len(apartados_antes),
            "abonos": len(abonos_antes),
            "ventas": len(ventas_antes),
        },
        "despues": {
            "apartados": len(apartados_despues),
            "abonos": len(abonos_despues),
            "ventas": len(ventas_despues),
        },
        "ids_apartados_despues": [ap["id"] for ap in apartados_despues],
    })

    ids_antes = [ap["id"] for ap in apartados_antes]
    ids_despues = [ap["id"] for ap in apartados_despues]
    a.apuntar(
        PRUEBA,
        "no se duplican apartados (siguen los mismos 7 IDs)",
        len(apartados_despues) == 7 and ids_antes == ids_despues,
        f"antes={len(apartados_antes)} · despues={len(apartados_despues)}",
    )
    a.apuntar(
        PRUEBA,
        "no se duplican abonos (siguen exactamente 10)",
        len(abonos_despues) == len(abonos_antes) == 10,
        f"antes={len(abonos_antes)} · despues={len(abonos_despues)}",
    )
    a.apuntar(
        PRUEBA,
        "no se duplican ventas (siguen exactamente 6)",
        len(ventas_despues) == len(ventas_antes) == 6,
        f"antes={len(ventas_antes)} · despues={len(ventas_despues)}",
    )

    sys.exit(a.finalizar("resumen-escenario-b.txt"))


if __name__ == "__main__":
    main()
