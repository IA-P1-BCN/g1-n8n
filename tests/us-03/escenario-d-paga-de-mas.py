#!/usr/bin/env python3
"""Escenario D — Paga de más (US-03): 04_bizum_laura.

Laura paga 15 € pero le queda menos pendiente: la app lo rechaza (422), NO se registra nada y se
avisa a Marisa con el motivo.

Fixture: precio 20 € y abono inicial 10 € → pendiente 10 €; el Bizum de 15 € supera lo pendiente.

Uso:  python tests/us-03/escenario-d-paga-de-mas.py   (RESETEA los datos de la app)
"""

import sys

import ayudantes as a

PRUEBA = "D-paga-de-mas"


def main():
    a.preparar(PRUEBA)
    laura = a.crear_apartado("Laura Ortega", "laura.ortega@prueba.local", "Deportiva blanca", 20.0, 10.0)
    asunto, cuerpo = a.aviso_desde_eml("04_bizum_laura")
    t0 = a.ahora()
    payload, _ = a.enviar_aviso(asunto, cuerpo)
    ejec = a.esperar_ejecucion(t0)
    a.guardar("escenario-d-payload.json", payload)
    a.guardar("escenario-d-ejecucion.json", a.resumen_ejecucion(ejec))
    a.apuntar(PRUEBA, "ejecución del Flujo 03", bool(ejec) and ejec.get("status") == "success",
              ejec.get("status") if ejec else "sin ejecución")
    a.apuntar(PRUEBA, "la app rechaza el abono (no se registra)", a.camino(ejec) == "rechazo", a.camino(ejec))
    despues = a.apartado(laura["id"])
    a.apuntar(PRUEBA, "no se registró nada (pendiente intacto 10 €)",
              round(despues.get("pendiente", -1), 2) == 10.0 and len(despues.get("abonos", [])) == 1,
              f"pendiente={despues.get('pendiente')} abonos={len(despues.get('abonos', []))}")
    aviso = a.esperar_correo(a.asunto_contiene("rechazado"))
    a.guardar("escenario-d-aviso.json", {"asunto": (aviso or {}).get("Subject"), "html": (aviso or {}).get("HTML", "")[:1500]})
    a.apuntar(PRUEBA, "Marisa recibe el aviso de rechazo", bool(aviso), (aviso or {}).get("Subject", "sin aviso"))
    html = (aviso or {}).get("HTML", "").lower()
    a.apuntar(PRUEBA, "el aviso trae el motivo (supera lo pendiente)", "pendiente" in html or "supera" in html,
              "motivo presente" if ("pendiente" in html or "supera" in html) else "sin motivo")
    return a.finalizar("resumen-escenario-d.txt")


if __name__ == "__main__":
    sys.exit(main())
