#!/usr/bin/env python3
"""Escenario B — Sin secretos (US-05): como Marisa, revisa que el aviso de un fallo no incluye contraseñas ni claves.

El evento de prueba lleva señuelos de password/apikey dentro de datos; si el aviso los filtra, falla.
Uso:  python tests/us-05/escenario-b-sin-secretos.py
      (requiere n8n + mailpit en N8N_URL / MAILPIT_URL, por defecto localhost)
Salida: evidencia en docs/evidencia/us-05/ y exit code 1 si algún criterio falla.
"""

import ayudantes as a
import sys

PRUEBA = "sin-secretos"


def main():
    a.preparar_salida()
    print("— Escenario B · Sin secretos —")
    conocidos = a.mensajes_actuales()

    payload = {
        "evento": "apartado.creado",
        "datos": {
            "id": 998, "fecha": "2026-10-26", "cliente": "Prueba de fallo",
            "email": "nadie", "producto": "Botín piel marrón", "talla": "38",
            "precio": 89.9, "abonado": 10, "pendiente": 79.9,
            "fecha_limite": "2027-01-24", "estado": "activo",
            "password": a.SEÑUELOS[0], "apikey": a.SEÑUELOS[1],
        },
    }
    estado, respuesta = a.api(f"{a.N8N_URL}/webhook/tienda", payload)
    a.guardar("escenario-b-sin-secretos-payload.json", payload)
    a.guardar("escenario-b-sin-secretos-webhook.json", {"status": estado, "respuesta": respuesta})
    a.apuntar(PRUEBA, "webhook acepta el evento", estado == 200, str(respuesta.get("message", "")))

    aviso = a.esperar_aviso(conocidos, "Flujo 01")
    if not aviso:
        a.apuntar(PRUEBA, "aviso recibido en Mailpit", False, "timeout sin aviso")
        sys.exit(a.finalizar("resumen-escenario-b.txt"))
    campos = a.extraer_campos(aviso)
    a.guardar("escenario-b-sin-secretos-aviso.json", aviso)
    a.apuntar(PRUEBA, "aviso recibido en Mailpit", True, aviso.get("Subject", ""))

    texto, html = aviso.get("Text") or "", aviso.get("HTML") or ""
    favores = {s: (s in texto, s in html) for s in a.SEÑUELOS}
    a.guardar(
        "escenario-b-busqueda-secretos.txt",
        "\n".join(
            [f"aviso: {a.identificador(aviso)} · {aviso.get('Subject')}"]
            + [f"'{s}' en Text: {t} · en HTML: {h}" for s, (t, h) in favores.items()]
        ) + "\n",
    )
    a.apuntar(PRUEBA, "sin contraseñas ni claves", all(not t and not h for t, h in favores.values()), str(favores))
    a.apuntar(PRUEBA, "aviso con los campos de la lista blanca", bool(campos.get("flujo") and campos.get("paso") and campos.get("error")), str({k: campos.get(k) for k in ("flujo", "paso", "error")}))
    sys.exit(a.finalizar("resumen-escenario-b.txt"))


if __name__ == "__main__":
    main()
