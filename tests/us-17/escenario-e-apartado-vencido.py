#!/usr/bin/env python3
"""Escenario E — `apartado.vencido` (US-17, criterio 5).

Envía el evento con el payload que manda la app al vencer un apartado (`{apartado, vale}`) y comprueba
en Executions que el Switch lo lleva a la rama `apartado.vencido` (todavía sin sub-flujo: llegará con
el Flujo 06, US-07).

Uso:  python tests/us-17/escenario-e-apartado-vencido.py
      (requiere n8n en N8N_URL, por defecto localhost, y la clave de n8n en API_KEY/.env)
Salida: evidencia en docs/evidencia/us-17/ y exit code 1 si algún criterio falla.
"""

import sys

import ayudantes as a

PRUEBA = "apartado-vencido"
PAYLOAD = {
    "evento": "apartado.vencido",
    "datos": {
        "apartado": {
            "id": 971, "fecha": "2026-07-01", "cliente": "Prueba US-17",
            "telefono": "600000000", "email": "prueba.us17@paso-firme.local",
            "producto": "Botín piel marrón", "talla": "38",
            "precio": 89.9, "abonado": 20.0, "pendiente": 69.9,
            "fecha_limite": "2026-09-29", "estado": "vencido",
        },
        "vale": {"id": 12, "codigo": "VALE-00971", "apartado_id": 971, "fecha": "2026-10-27", "importe": 20.0},
    },
}


def main():
    a.preparar_salida()
    print("— Escenario E · apartado.vencido —")

    desde = a.ahora()
    estado, respuesta = a.webhook_datos(PAYLOAD)
    a.guardar("escenario-e-apartado-vencido-payload.json", PAYLOAD)
    a.guardar("escenario-e-apartado-vencido-webhook.json", {"status": estado, "respuesta": respuesta})
    a.apuntar(PRUEBA, "el webhook acepta el evento", estado == 200, str(respuesta.get("message", "")))

    ejecucion = a.esperar_ejecucion(desde)
    if not ejecucion:
        a.apuntar(PRUEBA, "ejecución registrada en Executions", False, "timeout sin ejecución")
        sys.exit(a.finalizar("resumen-escenario-e.txt"))
    a.guardar("escenario-e-apartado-vencido-ejecucion.json", a.resumen_ejecucion(ejecucion))
    a.apuntar(PRUEBA, "ejecución registrada en Executions", True, f"id {ejecucion['id']}")
    a.apuntar(PRUEBA, "la ejecución termina bien", ejecucion.get("status") == "success", str(ejecucion.get("status")))

    a.comprobar_reparto(PRUEBA, ejecucion, 3)
    a.apuntar(PRUEBA, "la rama queda a la espera del Flujo 06", "Ejecutar Flujo 01" not in a.nodos(ejecucion) and "Ejecutar Flujo 02" not in a.nodos(ejecucion), str(a.nodos(ejecucion)))

    sys.exit(a.finalizar("resumen-escenario-e.txt"))


if __name__ == "__main__":
    main()
