#!/usr/bin/env python3
"""Escenario A — Fallo provocado (US-05): provoca fallos reales y verifica que llega el aviso con flujo, paso y error.

Uso:  python tests/us-05/escenario-a-fallo-provocado.py
      (requiere n8n + mailpit en N8N_URL / MAILPIT_URL, por defecto localhost)
Salida: evidencia en docs/evidencia/us-05/ y exit code 1 si algún criterio falla.
"""

import sys

import ayudantes as a

PRUEBA = "fallo-provocado"


def test_fallo_en_flujo_01(conocidos):
    payload = {
        "evento": "apartado.creado",
        "datos": {
            "id": 997, "fecha": "2026-10-26", "cliente": "Prueba de fallo",
            "email": "nadie", "producto": "Botín piel marrón", "talla": "38",
            "precio": 89.9, "abonado": 10, "pendiente": 79.9,
            "fecha_limite": "2027-01-24", "estado": "activo",
        },
    }
    estado, respuesta = a.api(f"{a.N8N_URL}/webhook/tienda", payload)
    a.guardar("escenario-a-fallo-flujo-01-payload.json", payload)
    a.guardar("escenario-a-fallo-flujo-01-webhook.json", {"status": estado, "respuesta": respuesta})
    a.apuntar(PRUEBA, "webhook acepta el evento", estado == 200, str(respuesta.get("message", "")))

    aviso = a.esperar_aviso(conocidos, "Flujo 01")
    if not aviso:
        a.apuntar(PRUEBA, "aviso recibido en Mailpit", False, "timeout sin aviso")
        return
    campos = a.extraer_campos(aviso)
    a.guardar("escenario-a-fallo-flujo-01-aviso.json", aviso)
    a.apuntar(PRUEBA, "aviso recibido en Mailpit", True, aviso.get("Subject", ""))
    a.apuntar(PRUEBA, "nombra el flujo", (campos.get("flujo") or "").startswith("Flujo 01"), campos.get("flujo"))
    a.apuntar(PRUEBA, "nombra el paso", campos.get("paso") == "Enviar resumen al cliente", campos.get("paso"))
    a.apuntar(PRUEBA, "incluye el error", "No recipients defined" in (campos.get("error") or ""), campos.get("error"))
    a.apuntar(PRUEBA, "enlace a la ejecución", bool((campos.get("ejecucion") or "").startswith(a.N8N_URL + "/workflow/")), campos.get("ejecucion"))

    aviso_receptor = a.esperar_aviso(conocidos, "Receptor")
    if not aviso_receptor:
        a.apuntar(PRUEBA, "aviso del Receptor (padre)", False, "timeout sin aviso del receptor")
        return
    campos_r = a.extraer_campos(aviso_receptor)
    a.guardar("escenario-a-fallo-flujo-01-receptor-aviso.json", aviso_receptor)
    a.apuntar(PRUEBA, "aviso del Receptor (padre)", True, aviso_receptor.get("Subject", ""))
    a.apuntar(PRUEBA, "paso del receptor", campos_r.get("paso") == "Ejecutar Flujo 01", campos_r.get("paso"))


def test_fallo_en_receptor():
    conocidos = a.mensajes_actuales()
    estado, respuesta = a.api(f"{a.N8N_URL}/webhook/tienda", b"[1,2,3]")
    a.guardar("escenario-a-fallo-receptor-payload.txt", "[1,2,3]")
    a.guardar("escenario-a-fallo-receptor-webhook.json", {"status": estado, "respuesta": respuesta})
    a.apuntar(PRUEBA, "webhook acepta la petición", estado == 200, str(respuesta.get("message", "")))

    aviso = a.esperar_aviso(conocidos, "Receptor")
    if not aviso:
        a.apuntar(PRUEBA, "aviso recibido en Mailpit", False, "timeout sin aviso")
        return
    campos = a.extraer_campos(aviso)
    a.guardar("escenario-a-fallo-receptor-aviso.json", aviso)
    a.apuntar(PRUEBA, "aviso recibido en Mailpit", True, aviso.get("Subject", ""))
    a.apuntar(PRUEBA, "nombra el flujo", "Receptor" in (campos.get("flujo") or ""), campos.get("flujo"))
    a.apuntar(PRUEBA, "nombra el paso", campos.get("paso") == "Evento y datos", campos.get("paso"))
    a.apuntar(PRUEBA, "incluye el error", "valid JSON object" in (campos.get("error") or ""), campos.get("error"))


def main():
    a.preparar_salida()
    print("— Escenario A · Fallo provocado —")
    test_fallo_en_flujo_01(a.mensajes_actuales())
    test_fallo_en_receptor()
    sys.exit(a.finalizar("resumen-escenario-a.txt"))


if __name__ == "__main__":
    main()
