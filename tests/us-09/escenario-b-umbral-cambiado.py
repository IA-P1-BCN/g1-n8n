#!/usr/bin/env python3
"""Escenario B — cambiar el umbral sin editar el flujo (US-09, criterio B).

Cambia `UMBRAL_VENTA_GRANDE` en `.env` y recrea el contenedor de n8n (nada del editor
de flujos). Con el umbral más alto: una venta entre el umbral antiguo y el nuevo NO
genera aviso, y una venta por encima del nuevo, sí. Sale restaurando el `.env`
(umbral original) y recreando n8n, y comprueba que el umbral quedó como estaba.

Uso:  python tests/us-09/escenario-b-umbral-cambiado.py
Salida: evidencia en docs/evidencia/us-09/ y exit code 1 si algún criterio falla.
"""

import sys

import ayudantes as a

PRUEBA = "umbral-cambiado"


def main():
    umbral_original = a.preparar_salida()
    print("— Escenario B · umbral cambiado sin editar el flujo —")

    a.guardar("escenario-b-umbral-original.json", {"umbral_original": umbral_original})
    umbral_nuevo = umbral_original + 100

    try:
        original_linea = a.fijar_umbral(umbral_nuevo)
        ok_recrear = a.recrear_n8n()
        umbral_efectivo = a.umbral_actual()
        a.guardar("escenario-b-umbral-nuevo.json", {
            "original": umbral_original,
            "nuevo_en_env": umbral_nuevo,
            "n8n": ok_recrear,
            "efectivo_en_n8n": umbral_efectivo,
        })
        a.apuntar(PRUEBA, "cambiar el umbral en la variable sin editar el flujo",
                  ok_recrear and umbral_efectivo == umbral_nuevo,
                  f".env {umbral_nuevo} € → n8n {umbral_efectivo} €")

        conocidos = a.mensajes_actuales()

        venta_bajo = umbral_nuevo - 40
        estado, _ = a.crear_venta(venta_bajo, "Sneaker clásica edición especial · 39")
        a.guardar("escenario-b-venta-bajo.json", {"status": estado, "importe": venta_bajo})
        sin_aviso = a.esperar_sin_aviso(conocidos, timeout=25)
        a.apuntar(PRUEBA, "una venta entre el umbral antiguo y el nuevo NO llega aviso",
                  estado in (200, 201) and sin_aviso,
                  f"venta {venta_bajo} € con umbral {umbral_nuevo} €; sin aviso en 25 s")

        conocidos = a.mensajes_actuales()
        venta_sobre = umbral_nuevo + 40
        estado, venta = a.crear_venta(venta_sobre, "Zapato de novia con perlas · 36")
        a.guardar("escenario-b-venta-sobre.json", {"status": estado, "importe": venta_sobre})
        correo = a.esperar_aviso(conocidos)
        if not correo:
            a.apuntar(PRUEBA, "una venta sobre el nuevo umbral SÍ llega aviso", False,
                      "timeout sin aviso")
            sys.exit(a.finalizar("resumen-escenario-b.txt"))
        a.guardar("escenario-b-aviso-recibido.json", correo)
        cuerpo = (correo.get("HTML") or "") + "\n" + (correo.get("Text") or "")
        venta_ok = (venta or {}).get("id") is not None and f"{venta_sobre:g}" in cuerpo
        a.apuntar(PRUEBA, "una venta sobre el nuevo umbral SÍ llega aviso",
                  estado in (200, 201) and venta_ok,
                  f"venta {venta_sobre} € con umbral {umbral_nuevo} €; aviso ID={correo.get('ID')}")
    finally:
        # Devuelve la variable a su valor de salida (o quita la línea si no existía) y deja n8n en el estado inicial
        ok_restaurado = a.restaurar_umbral(original_linea)
        a.guardar("escenario-b-umbral-restaurado.json", {"original": umbral_original, "restaurado": ok_restaurado})
        print(f"  restauración: umbral {umbral_original} € de vuelta ({'OK' if ok_restaurado else 'FALLO'})")

    sys.exit(a.finalizar("resumen-escenario-b.txt"))


if __name__ == "__main__":
    main()
