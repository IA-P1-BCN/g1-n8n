#!/usr/bin/env python3
"""Escenario A — Día con movimientos (US-04).

Registra ventas y abonos del día por varias formas de pago, ejecuta el Flujo 05 y comprueba que llega
el cierre con ventas, abonos y total separados por forma de pago, y que los importes coinciden con los
de la app.

Uso:  python tests/us-04/escenario-a-con-movimientos.py   (requiere app+n8n+mailpit; RESETEA los datos de la app)
"""

import sys
from datetime import date

import ayudantes as a

PRUEBA = "A-con-movimientos"
FORMAS = ["efectivo", "tarjeta", "bizum"]


def totales_app(dia):
    """Suma por forma de pago lo cobrado hoy según la app (ventas + abonos)."""
    _, ventas = a.api_tienda(f"/api/ventas?desde={dia}&hasta={dia}")
    _, abonos = a.api_tienda(f"/api/abonos?desde={dia}&hasta={dia}")
    por_forma = {f: {"ventas": 0.0, "abonos": 0.0} for f in FORMAS}
    for v in ventas:
        por_forma.get(v["forma_pago"], por_forma["efectivo"])["ventas"] += float(v["importe"])
    for ab in abonos:
        por_forma.get(ab["forma_pago"], por_forma["efectivo"])["abonos"] += float(ab["importe"])
    tot_ventas = sum(float(v["importe"]) for v in ventas)
    tot_abonos = sum(float(ab["importe"]) for ab in abonos)
    return por_forma, tot_ventas, tot_abonos, tot_ventas + tot_abonos


def main():
    a.preparar_salida()
    a.limpiar_base()
    a.limpiar_buzon()
    # Ventas del día por tres formas de pago.
    a.crear_venta("Calcetines pack 3", 10.00, "efectivo")
    a.crear_venta("Bota montaña", 20.50, "tarjeta")
    a.crear_venta("Crema calzado", 5.00, "bizum")
    # Abonos del día: el inicial (efectivo) + un abono parcial (tarjeta).
    apartado = a.crear_apartado("Cliente Prueba", "Botín piel marrón", 50.00, 15.00, "efectivo")
    a.registrar_abono(apartado["id"], 8.00, "tarjeta")

    dia = date.today()
    por_forma, tot_ventas, tot_abonos, tot_dia = totales_app(dia.isoformat())
    fmt = lambda n: f"{round(n, 2):.2f}"

    conocidos = a.mensajes_actuales()
    ok, salida = a.ejecutar_flujo()
    a.guardar("escenario-a-ejecucion.txt", salida)
    a.apuntar(PRUEBA, "el flujo se ejecuta sin error", ok, salida.splitlines()[-1] if salida else "")

    cierre = a.esperar_cierre(conocidos)
    if not cierre:
        a.apuntar(PRUEBA, "llega el correo del cierre", False, "timeout sin correo")
        return a.finalizar("resumen-escenario-a.txt")
    html = cierre.get("HTML", "")
    a.guardar("escenario-a-cierre.json", {
        "asunto": cierre.get("Subject"),
        "esperado": {"ventas": fmt(tot_ventas), "abonos": fmt(tot_abonos), "total": fmt(tot_dia),
                     "efectivo": fmt(por_forma["efectivo"]["ventas"] + por_forma["efectivo"]["abonos"]),
                     "tarjeta": fmt(por_forma["tarjeta"]["ventas"] + por_forma["tarjeta"]["abonos"]),
                     "bizum": fmt(por_forma["bizum"]["ventas"] + por_forma["bizum"]["abonos"])},
        "html": html,
    })

    a.apuntar(PRUEBA, "el asunto lleva la fecha del día", dia.strftime("%d/%m/%Y") in (cierre.get("Subject") or ""),
              cierre.get("Subject"))
    a.apuntar(PRUEBA, "separa por forma de pago (efectivo, tarjeta y bizum)",
              all(e in html for e in ("Efectivo", "Tarjeta", "Bizum")), "las tres formas en el cuerpo")
    a.apuntar(PRUEBA, f"total de ventas coincide con la app ({fmt(tot_ventas)} €)", f"{fmt(tot_ventas)} €" in html)
    a.apuntar(PRUEBA, f"total de abonos coincide con la app ({fmt(tot_abonos)} €)", f"{fmt(tot_abonos)} €" in html)
    a.apuntar(PRUEBA, f"total del día coincide con la app ({fmt(tot_dia)} €)", f"{fmt(tot_dia)} €" in html)
    efectivo = por_forma["efectivo"]["ventas"] + por_forma["efectivo"]["abonos"]
    tarjeta = por_forma["tarjeta"]["ventas"] + por_forma["tarjeta"]["abonos"]
    a.apuntar(PRUEBA, f"total en efectivo correcto ({fmt(efectivo)} €)", f"{fmt(efectivo)} €" in html)
    a.apuntar(PRUEBA, f"total en tarjeta correcto ({fmt(tarjeta)} €)", f"{fmt(tarjeta)} €" in html)
    return a.finalizar("resumen-escenario-a.txt")


if __name__ == "__main__":
    sys.exit(main())
