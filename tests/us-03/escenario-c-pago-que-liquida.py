#!/usr/bin/env python3
"""Escenario C — Pago justo que liquida (US-03): 03_transferencia_lucia.

Lucía paga justo lo que falta (12 €): el apartado queda liquidado y el recibo (Flujo 02) avisa de
que puede recoger sus zapatos.

Fixture: precio 17 € y abono inicial 5 € → pendiente 12 €, que la transferencia de 12 € liquida.

Uso:  python tests/us-03/escenario-c-pago-que-liquida.py   (RESETEA los datos de la app)
"""

import sys

import ayudantes as a

PRUEBA = "C-pago-que-liquida"


def main():
    a.preparar(PRUEBA)
    lucia = a.crear_apartado("Lucía Gómez", "lucia.gomez@prueba.local", "Mocasín ante", 17.0, 5.0)
    asunto, cuerpo = a.aviso_desde_eml("03_transferencia_lucia")
    t0 = a.ahora()
    payload, _ = a.enviar_aviso(asunto, cuerpo)
    ejec = a.esperar_ejecucion(t0)
    a.guardar("escenario-c-payload.json", payload)
    a.guardar("escenario-c-ejecucion.json", a.resumen_ejecucion(ejec))
    a.apuntar(PRUEBA, "ejecución del Flujo 03", bool(ejec) and ejec.get("status") == "success",
              ejec.get("status") if ejec else "sin ejecución")
    a.apuntar(PRUEBA, "el flujo registra el abono", a.camino(ejec) == "registrado", a.camino(ejec))
    despues = a.apartado(lucia["id"])
    a.apuntar(PRUEBA, "el apartado queda liquidado", despues.get("estado") == "liquidado", despues.get("estado"))
    a.apuntar(PRUEBA, "pendiente a 0 €", round(despues.get("pendiente", -1), 2) == 0.0, f"pendiente={despues.get('pendiente')}")
    recibo = a.esperar_correo(lambda m: a.para("lucia.gomez@prueba.local")(m) and
                              (a.asunto_contiene("recoger")(m) or a.asunto_contiene("último abono")(m)))
    a.guardar("escenario-c-recibo.json", {"asunto": (recibo or {}).get("Subject"), "to": a.destinatarios(recibo or {})})
    a.apuntar(PRUEBA, "recibo final: puede recoger los zapatos", bool(recibo), (recibo or {}).get("Subject", "sin recibo"))
    return a.finalizar("resumen-escenario-c.txt")


if __name__ == "__main__":
    sys.exit(main())
