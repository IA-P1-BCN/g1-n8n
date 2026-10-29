#!/usr/bin/env python3
"""Escenario A — Venta sobre el umbral (US-09, criterios 1–2).

Registra en la app una venta por encima del umbral (`POST /api/ventas`, que avisa
al Receptor en una tarea de fondo) y comprueba que Marisa recibe el aviso en Mailpit
con los datos de esa venta y el umbral aplicado.

Uso:  python tests/us-09/escenario-a-venta-sobre-umbral.py
      (requiere el stack local con `task arrancar` y flujos importados con `task importar`)
Salida: evidencia en docs/evidencia/us-09/ y exit code 1 si algún criterio falla.
"""

import sys

import ayudantes as a

PRUEBA = "venta-sobre-umbral"


def main():
    umbral = a.preparar_salida()
    print("— Escenario A · venta sobre el umbral —")

    conocidos = a.mensajes_actuales()
    venta_grande = umbral + 50
    payload = {"concepto": "Botín exótico edición limitada · 42", "importe": venta_grande, "forma_pago": "tarjeta"}
    a.guardar("escenario-a-venta-grande.json", {"umbral": umbral, "payload": payload})

    estado, venta = a.crear_venta(venta_grande, payload["concepto"], payload["forma_pago"])
    a.guardar("escenario-a-venta-registrada.json", {"status": estado, "respuesta": venta})
    vid = (venta or {}).get("id") if isinstance(venta, dict) else None
    a.apuntar(PRUEBA, "la app registra la venta grande", estado in (200, 201) and vid is not None,
              f"status {estado}, id {vid}")

    correo = a.esperar_aviso(conocidos)
    if not correo:
        a.apuntar(PRUEBA, "Marisa recibe el aviso en Mailpit", False, "timeout sin aviso")
        sys.exit(a.finalizar("resumen-escenario-a.txt"))
    a.guardar("escenario-a-aviso-recibido.json", correo)
    identificador = correo.get("ID") or correo.get("Id")
    asunto = (correo.get("Subject") or "").strip()
    a.apuntar(PRUEBA, "Marisa recibe el aviso en Mailpit", True, f"ID={identificador}")

    cuerpo = (correo.get("HTML") or "") + "\n" + (correo.get("Text") or "")
    importe_texto = f"{venta_grande:g}"
    datos_ok = payload["concepto"] in cuerpo and importe_texto in cuerpo and asunto.startswith("🧾 Venta grande")
    a.apuntar(PRUEBA, "el aviso da los datos de la venta", datos_ok,
              f"concepto, {importe_texto} € y forma de pago en el correo")

    umbral_ok = f"({umbral} €)" in cuerpo
    a.apuntar(PRUEBA, "el aviso enseña el umbral aplicado", umbral_ok, f"umbral {umbral} € en el correo")

    sys.exit(a.finalizar("resumen-escenario-a.txt"))


if __name__ == "__main__":
    main()
