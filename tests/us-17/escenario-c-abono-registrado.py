#!/usr/bin/env python3
"""Escenario C — `abono.registrado` (US-17, criterio 3).

Envía el evento con el payload que manda la app al registrar un abono y comprueba en Executions que
el Switch lo lleva a su rama y que esa rama llama al Flujo 02.

Uso:  python tests/us-17/escenario-c-abono-registrado.py
      (requiere n8n en N8N_URL, por defecto localhost, y la clave de n8n en API_KEY/.env)
Salida: evidencia en docs/evidencia/us-17/ y exit code 1 si algún criterio falla.
"""

import sys

import ayudantes as a

PRUEBA = "abono-registrado"
PAYLOAD = {
    "evento": "abono.registrado",
    "datos": {
        "id": 970, "fecha": "2026-10-27", "cliente": "Prueba US-17",
        "telefono": "600000000", "email": "prueba.us17@paso-firme.local",
        "producto": "Botín piel marrón", "talla": "38",
        "precio": 89.9, "abonado": 40.0, "pendiente": 49.9,
        "fecha_limite": "2027-01-25", "estado": "activo", "importe": 30.0,
    },
}


def main():
    a.preparar_salida()
    print("— Escenario C · abono.registrado —")

    desde = a.ahora()
    estado, respuesta = a.webhook_datos(PAYLOAD)
    a.guardar("escenario-c-abono-registrado-payload.json", PAYLOAD)
    a.guardar("escenario-c-abono-registrado-webhook.json", {"status": estado, "respuesta": respuesta})
    a.apuntar(PRUEBA, "el webhook acepta el evento", estado == 200, str(respuesta.get("message", "")))

    ejecucion = a.esperar_ejecucion(desde)
    if not ejecucion:
        a.apuntar(PRUEBA, "ejecución registrada en Executions", False, "timeout sin ejecución")
        sys.exit(a.finalizar("resumen-escenario-c.txt"))
    a.guardar("escenario-c-abono-registrado-ejecucion.json", a.resumen_ejecucion(ejecucion))
    a.apuntar(PRUEBA, "ejecución registrada en Executions", True, f"id {ejecucion['id']}")
    a.apuntar(PRUEBA, "la ejecución termina bien", ejecucion.get("status") == "success", str(ejecucion.get("status")))

    a.comprobar_reparto(PRUEBA, ejecucion, 1)
    a.apuntar(PRUEBA, "la rama ejecuta el Flujo 02", "Ejecutar Flujo 02" in a.nodos(ejecucion), str(a.nodos(ejecucion)))

    sys.exit(a.finalizar("resumen-escenario-c.txt"))


if __name__ == "__main__":
    main()
