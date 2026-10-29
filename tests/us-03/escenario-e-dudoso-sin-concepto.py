#!/usr/bin/env python3
"""Escenario E — Dudoso, sin concepto (US-03): 05_bizum_romero.

Ordenante abreviado («ROMERO D») y sin concepto: no se puede confirmar el apartado, así que NO se
registra nada y se pregunta a Marisa antes de registrar.

Uso:  python tests/us-03/escenario-e-dudoso-sin-concepto.py   (RESETEA los datos de la app)
"""

import sys

import ayudantes as a

PRUEBA = "E-dudoso-sin-concepto"


def main():
    a.preparar(PRUEBA)
    romero = a.crear_apartado("David Romero", "david.romero@prueba.local", "Bailarina roja", 40.0, 5.0)
    asunto, cuerpo = a.aviso_desde_eml("05_bizum_romero")
    t0 = a.ahora()
    payload, _ = a.enviar_aviso(asunto, cuerpo)
    ejec = a.esperar_ejecucion(t0)
    a.guardar("escenario-e-payload.json", payload)
    a.guardar("escenario-e-ejecucion.json", a.resumen_ejecucion(ejec))
    a.apuntar(PRUEBA, "ejecución del Flujo 03", bool(ejec) and ejec.get("status") == "success",
              ejec.get("status") if ejec else "sin ejecución")
    a.apuntar(PRUEBA, "no se registra: se pregunta a Marisa", a.camino(ejec) == "preguntar", a.camino(ejec))
    despues = a.apartado(romero["id"])
    a.apuntar(PRUEBA, "el apartado no cambia (solo su abono inicial)",
              len(despues.get("abonos", [])) == 1 and round(despues.get("pendiente", -1), 2) == 35.0,
              f"pendiente={despues.get('pendiente')} abonos={len(despues.get('abonos', []))}")
    aviso = a.esperar_correo(a.asunto_contiene("sin identificar"))
    a.guardar("escenario-e-aviso.json", {"asunto": (aviso or {}).get("Subject"), "html": (aviso or {}).get("HTML", "")[:1500]})
    a.apuntar(PRUEBA, "Marisa recibe la pregunta", bool(aviso), (aviso or {}).get("Subject", "sin aviso"))
    return a.finalizar("resumen-escenario-e.txt")


if __name__ == "__main__":
    sys.exit(main())
