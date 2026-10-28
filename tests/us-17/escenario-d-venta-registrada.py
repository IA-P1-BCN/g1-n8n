#!/usr/bin/env python3
"""Escenario D — `venta.registrada` (US-17, criterio 4).

Envía el evento con el payload que manda la app al registrar una venta y comprueba en Executions que
el Switch lo lleva a la rama `venta.registrada` (todavía sin sub-flujo: llegará con el Flujo 04, US-09).

Uso:  python tests/us-17/escenario-d-venta-registrada.py
      (requiere n8n en N8N_URL, por defecto localhost, y la clave de n8n en API_KEY/.env)
Salida: evidencia en docs/evidencia/us-17/ y exit code 1 si algún criterio falla.
"""

import sys

import ayudantes as a

PRUEBA = "venta-registrada"
PAYLOAD = {
    "evento": "venta.registrada",
    "datos": {"id": 640, "fecha": "2026-10-27", "concepto": "Botín piel marrón · 38", "importe": 89.9, "forma_pago": "efectivo"},
}


def main():
    a.preparar_salida()
    print("— Escenario D · venta.registrada —")

    desde = a.ahora()
    estado, respuesta = a.webhook_datos(PAYLOAD)
    a.guardar("escenario-d-venta-registrada-payload.json", PAYLOAD)
    a.guardar("escenario-d-venta-registrada-webhook.json", {"status": estado, "respuesta": respuesta})
    a.apuntar(PRUEBA, "el webhook acepta el evento", estado == 200, str(respuesta.get("message", "")))

    ejecucion = a.esperar_ejecucion(desde)
    if not ejecucion:
        a.apuntar(PRUEBA, "ejecución registrada en Executions", False, "timeout sin ejecución")
        sys.exit(a.finalizar("resumen-escenario-d.txt"))
    a.guardar("escenario-d-venta-registrada-ejecucion.json", a.resumen_ejecucion(ejecucion))
    a.apuntar(PRUEBA, "ejecución registrada en Executions", True, f"id {ejecucion['id']}")
    a.apuntar(PRUEBA, "la ejecución termina bien", ejecucion.get("status") == "success", str(ejecucion.get("status")))

    a.comprobar_reparto(PRUEBA, ejecucion, 2)
    a.apuntar(PRUEBA, "la rama queda a la espera del Flujo 04", "Ejecutar Flujo 01" not in a.nodos(ejecucion) and "Ejecutar Flujo 02" not in a.nodos(ejecucion), str(a.nodos(ejecucion)))

    sys.exit(a.finalizar("resumen-escenario-d.txt"))


if __name__ == "__main__":
    main()
