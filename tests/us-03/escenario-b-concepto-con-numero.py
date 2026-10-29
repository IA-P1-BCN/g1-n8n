#!/usr/bin/env python3
"""Escenario B — Ordenante abreviado con nº de apartado en el concepto (US-03): 02_bizum_jorge.

El ordenante está abreviado («JORGE M.»), pero el concepto trae el nº de apartado: ese número
identifica el apartado y se registra el abono.

El nº real del apartado se descubre al crearlo (los ids son autoincrementales), así que el aviso se
construye con ese id — fiel al escenario (nombre abreviado + número explícito en el concepto).

Uso:  python tests/us-03/escenario-b-concepto-con-numero.py   (RESETEA los datos de la app)
"""

import sys

import ayudantes as a

PRUEBA = "B-concepto-con-numero"


def main():
    a.preparar(PRUEBA)
    jorge = a.crear_apartado("Jorge Martín", "jorge.martin@prueba.local", "Bota montaña", 60.0, 5.0)
    asunto = "Has recibido un Bizum de 20,00 €"
    cuerpo = ("Hola, ZAPATERIA PASO FIRME:\n\nHas recibido un Bizum.\n\n"
              "Importe: 20,00 EUR\nOrdenante: JORGE M.\n"
              f"Concepto: apartado {jorge['id']} bota\n\n"
              "El importe ya está disponible en tu cuenta terminada en 4821.\n\nCaja Rivera")
    t0 = a.ahora()
    payload, _ = a.enviar_aviso(asunto, cuerpo)
    ejec = a.esperar_ejecucion(t0)
    a.guardar("escenario-b-payload.json", payload)
    a.guardar("escenario-b-ejecucion.json", a.resumen_ejecucion(ejec))
    a.apuntar(PRUEBA, "ejecución del Flujo 03", bool(ejec) and ejec.get("status") == "success",
              ejec.get("status") if ejec else "sin ejecución")
    dec = a.decision(ejec) or {}
    a.apuntar(PRUEBA, "el nº del concepto identifica el apartado",
              (dec.get("apartado") or {}).get("id") == jorge["id"], f"apartado={ (dec.get('apartado') or {}).get('id') }")
    a.apuntar(PRUEBA, "el flujo registra el abono", a.camino(ejec) == "registrado", a.camino(ejec))
    despues = a.apartado(jorge["id"])
    a.apuntar(PRUEBA, "pendiente baja 20 €",
              round(despues.get("pendiente", -1), 2) == round(jorge["pendiente"] - 20.0, 2),
              f"pendiente={despues.get('pendiente')}")
    return a.finalizar("resumen-escenario-b.txt")


if __name__ == "__main__":
    sys.exit(main())
