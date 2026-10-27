#!/usr/bin/env python3
"""Escenario A — Publicación del receptor (US-17, criterio 1).

Comprueba que el flujo receptor está publicado en su Production URL (`/webhook/tienda`), que el
webhook de pruebas no atiende y que un evento sin rama no se pierde: cae en la salida fallback
«evento desconocido» del Switch.

Uso:  python tests/us-17/escenario-a-publicacion.py
      (requiere n8n en N8N_URL, por defecto localhost, y la clave de n8n en API_KEY/.env)
Salida: evidencia en docs/evidencia/us-17/ y exit code 1 si algún criterio falla.
"""

import sys

import ayudantes as a

PRUEBA = "publicacion"
SONDA = {"evento": "sonda.receptor", "datos": {"origen": "prueba de publicación"}}


def main():
    a.preparar_salida()
    print("— Escenario A · Publicación del receptor —")

    estado, flujo = a.api_n8n(f"/workflows/{a.RECEPTOR_ID}")
    a.guardar("escenario-a-publicacion-workflow.json", {
        "status": estado,
        "id": flujo.get("id"), "name": flujo.get("name"), "active": flujo.get("active"),
    })
    a.apuntar(PRUEBA, "el flujo receptor está activo", estado == 200 and flujo.get("active") is True, f"active={flujo.get('active')}")
    a.apuntar(PRUEBA, "el flujo tiene el nombre de la convención", flujo.get("name") == a.NOMBRE_RECEPTOR, str(flujo.get("name")))

    desde = a.ahora()
    estado, respuesta = a.webhook_datos(SONDA)
    a.guardar("escenario-a-publicacion-webhook.json", {"url": f"{a.N8N_URL}/webhook/tienda", "payload": SONDA, "status": estado, "respuesta": respuesta})
    a.apuntar(PRUEBA, "la Production URL acepta el evento", estado == 200, str(respuesta.get("message", "")))
    a.apuntar(PRUEBA, "responde sin esperar al flujo", (respuesta.get("message") or "") == "Workflow was started", str(respuesta.get("message", "")))

    estado_prueba, respuesta_prueba = a.api(f"{a.N8N_URL}/webhook-test/tienda", SONDA)
    a.guardar("escenario-a-publicacion-webhook-prueba.json", {"url": f"{a.N8N_URL}/webhook-test/tienda", "status": estado_prueba, "respuesta": respuesta_prueba})
    a.apuntar(PRUEBA, "el webhook de pruebas no atiende (es producción)", estado_prueba != 200, f"status={estado_prueba}")

    ejecucion = a.esperar_ejecucion(desde)
    if not ejecucion:
        a.apuntar(PRUEBA, "ejecución registrada en Executions", False, "timeout sin ejecución")
        sys.exit(a.finalizar("resumen-escenario-a.txt"))
    a.guardar("escenario-a-publicacion-ejecucion.json", a.resumen_ejecucion(ejecucion))
    a.apuntar(PRUEBA, "ejecución registrada en Executions", True, f"id {ejecucion['id']}")
    a.apuntar(PRUEBA, "la ejecución termina bien", ejecucion.get("status") == "success", str(ejecucion.get("status")))

    cuentas = a.reparto(ejecucion)
    a.apuntar(PRUEBA, "un evento sin rama cae en el fallback «evento desconocido»",
              len(cuentas) > a.INDICE_FALLBACK and cuentas[a.INDICE_FALLBACK] == 1, f"salidas={cuentas}")
    a.apuntar(PRUEBA, "el fallback conserva el evento recibido",
              a.evento_de_rama(ejecucion, a.INDICE_FALLBACK) == SONDA["evento"], str(a.evento_de_rama(ejecucion, a.INDICE_FALLBACK)))

    sys.exit(a.finalizar("resumen-escenario-a.txt"))


if __name__ == "__main__":
    main()
