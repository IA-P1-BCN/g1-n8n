#!/usr/bin/env python3
"""Escenario G — Cliente desconocido (US-03): 07_transferencia_desconocido.

El ordenante no coincide con ningún apartado activo: NO se registra nada y se pregunta a Marisa.

Fixture: un apartado señuelo de otra persona, para que la lista de activos no esté vacía y la
comprobación sea significativa (aun así, no hay ningún «Antonio»).

Uso:  python tests/us-03/escenario-g-cliente-desconocido.py   (RESETEA los datos de la app)
"""

import sys

import ayudantes as a

PRUEBA = "G-cliente-desconocido"


def main():
    a.preparar(PRUEBA)
    a.crear_apartado("Carmen Ruiz", "carmen.ruiz@prueba.local", "Zueco sanitario", 50.0, 5.0)  # señuelo
    asunto, cuerpo = a.aviso_desde_eml("07_transferencia_desconocido")
    t0 = a.ahora()
    payload, _ = a.enviar_aviso(asunto, cuerpo)
    ejec = a.esperar_ejecucion(t0)
    a.guardar("escenario-g-payload.json", payload)
    a.guardar("escenario-g-ejecucion.json", a.resumen_ejecucion(ejec))
    a.apuntar(PRUEBA, "ejecución del Flujo 03", bool(ejec) and ejec.get("status") == "success",
              ejec.get("status") if ejec else "sin ejecución")
    a.apuntar(PRUEBA, "no se registra: se pregunta a Marisa", a.camino(ejec) == "preguntar", a.camino(ejec))
    dec = a.decision(ejec) or {}
    a.apuntar(PRUEBA, "sin candidatos para el ordenante", dec.get("apartado") in (None, {}),
              f"apartado={dec.get('apartado')}")
    aviso = a.esperar_correo(a.asunto_contiene("sin identificar"))
    a.guardar("escenario-g-aviso.json", {"asunto": (aviso or {}).get("Subject"), "html": (aviso or {}).get("HTML", "")[:1500]})
    a.apuntar(PRUEBA, "Marisa recibe la pregunta", bool(aviso), (aviso or {}).get("Subject", "sin aviso"))
    return a.finalizar("resumen-escenario-g.txt")


if __name__ == "__main__":
    sys.exit(main())
