#!/usr/bin/env python3
"""Escenario B — `apartado.creado` (US-17, criterio 2).

Envía el evento con el payload que manda la app al crear un apartado y comprueba en Executions que
el Switch lo lleva a su rama y que esa rama llama al Flujo 01.

Uso:  python tests/us-17/escenario-b-apartado-creado.py
      (requiere n8n en N8N_URL, por defecto localhost, y la clave de n8n en API_KEY/.env)
Salida: evidencia en docs/evidencia/us-17/ y exit code 1 si algún criterio falla.
"""

import sys

import ayudantes as a

PRUEBA = "apartado-creado"
PAYLOAD = {
    "evento": "apartado.creado",
    "datos": {
        "id": 970, "fecha": "2026-10-27", "cliente": "Prueba US-17",
        "telefono": "600000000", "email": "prueba.us17@paso-firme.local",
        "producto": "Botín piel marrón", "talla": "38",
        "precio": 89.9, "abonado": 10.0, "pendiente": 79.9,
        "fecha_limite": "2027-01-25", "estado": "activo",
    },
}


def main():
    a.preparar_salida()
    print("— Escenario B · apartado.creado —")

    desde = a.ahora()
    estado, respuesta = a.webhook_datos(PAYLOAD)
    a.guardar("escenario-b-apartado-creado-payload.json", PAYLOAD)
    a.guardar("escenario-b-apartado-creado-webhook.json", {"status": estado, "respuesta": respuesta})
    a.apuntar(PRUEBA, "el webhook acepta el evento", estado == 200, str(respuesta.get("message", "")))

    ejecucion = a.esperar_ejecucion(desde)
    if not ejecucion:
        a.apuntar(PRUEBA, "ejecución registrada en Executions", False, "timeout sin ejecución")
        sys.exit(a.finalizar("resumen-escenario-b.txt"))
    a.guardar("escenario-b-apartado-creado-ejecucion.json", a.resumen_ejecucion(ejecucion))
    a.apuntar(PRUEBA, "ejecución registrada en Executions", True, f"id {ejecucion['id']}")
    a.apuntar(PRUEBA, "la ejecución termina bien", ejecucion.get("status") == "success", str(ejecucion.get("status")))

    a.comprobar_reparto(PRUEBA, ejecucion, 0)
    a.apuntar(PRUEBA, "la rama ejecuta el Flujo 01", "Ejecutar Flujo 01" in a.nodos(ejecucion), str(a.nodos(ejecucion)))

    sys.exit(a.finalizar("resumen-escenario-b.txt"))


if __name__ == "__main__":
    main()
