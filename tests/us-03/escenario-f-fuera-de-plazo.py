#!/usr/bin/env python3
"""Escenario F — Apartado fuera de plazo (US-03): 06_bizum_paula.

El apartado de Paula está fuera de plazo: la app no admite el abono (422 plazo vencido), NO se
registra nada y se avisa a Marisa.

Fixture: apartado creado con fecha de hace 100 días → su fecha límite (90 días) ya pasó, pero sigue
activo (la app no vence sola; eso es del Flujo 06).

Uso:  python tests/us-03/escenario-f-fuera-de-plazo.py   (RESETEA los datos de la app)
"""

import sys
from datetime import date, timedelta

import ayudantes as a

PRUEBA = "F-fuera-de-plazo"


def main():
    a.preparar(PRUEBA)
    hace_100 = (date.today() - timedelta(days=100)).isoformat()
    paula = a.crear_apartado("Paula Ramos", "paula.ramos@prueba.local", "Bota alta mujer", 60.0, 5.0, fecha=hace_100)
    a.apuntar(PRUEBA, "precondición: apartado activo fuera de plazo",
              paula.get("estado") == "activo" and paula.get("fecha_limite") < date.today().isoformat(),
              f"estado={paula.get('estado')} limite={paula.get('fecha_limite')}")
    asunto, cuerpo = a.aviso_desde_eml("06_bizum_paula")
    t0 = a.ahora()
    payload, _ = a.enviar_aviso(asunto, cuerpo)
    ejec = a.esperar_ejecucion(t0)
    a.guardar("escenario-f-payload.json", payload)
    a.guardar("escenario-f-ejecucion.json", a.resumen_ejecucion(ejec))
    a.apuntar(PRUEBA, "ejecución del Flujo 03", bool(ejec) and ejec.get("status") == "success",
              ejec.get("status") if ejec else "sin ejecución")
    a.apuntar(PRUEBA, "la app rechaza el abono (no se registra)", a.camino(ejec) == "rechazo", a.camino(ejec))
    despues = a.apartado(paula["id"])
    a.apuntar(PRUEBA, "no se registró nada (solo el abono inicial)", len(despues.get("abonos", [])) == 1,
              f"abonos={len(despues.get('abonos', []))}")
    aviso = a.esperar_correo(a.asunto_contiene("rechazado"))
    a.guardar("escenario-f-aviso.json", {"asunto": (aviso or {}).get("Subject"), "html": (aviso or {}).get("HTML", "")[:1500]})
    a.apuntar(PRUEBA, "Marisa recibe el aviso de rechazo", bool(aviso), (aviso or {}).get("Subject", "sin aviso"))
    html = (aviso or {}).get("HTML", "").lower()
    a.apuntar(PRUEBA, "el aviso trae el motivo (plazo vencido)", "plazo" in html or "vencid" in html,
              "motivo presente" if ("plazo" in html or "vencid" in html) else "sin motivo")
    return a.finalizar("resumen-escenario-f.txt")


if __name__ == "__main__":
    sys.exit(main())
