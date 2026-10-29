#!/usr/bin/env python3
"""Escenario H — No es un pago (US-03): 08_publicidad_banco.

La publicidad del banco no es un aviso de pago: se ignora (ningún registro y ninguna pregunta).

Uso:  python tests/us-03/escenario-h-no-es-pago.py   (RESETEA los datos de la app)
"""

import sys
import time

import ayudantes as a

PRUEBA = "H-no-es-pago"


def main():
    a.preparar(PRUEBA)
    asunto, cuerpo = a.aviso_desde_eml("08_publicidad_banco")
    t0 = a.ahora()
    payload, _ = a.enviar_aviso(asunto, cuerpo)
    ejec = a.esperar_ejecucion(t0)
    a.guardar("escenario-h-payload.json", payload)
    a.guardar("escenario-h-ejecucion.json", a.resumen_ejecucion(ejec))
    a.apuntar(PRUEBA, "ejecución del Flujo 03", bool(ejec) and ejec.get("status") == "success",
              ejec.get("status") if ejec else "sin ejecución")
    a.apuntar(PRUEBA, "se ignora (rama «no es un pago»)", a.camino(ejec) == "ignorar", a.camino(ejec))
    a.apuntar(PRUEBA, "no llama a la IA ni a la app",
              "Modelo Groq" not in a.nodos(ejec) and "Apartados activos" not in a.nodos(ejec),
              ", ".join(a.nodos(ejec)))
    # Ninguna pregunta ni registro: el buzón sigue vacío un margen razonable.
    time.sleep(6)
    correos = a.mensajes()
    a.guardar("escenario-h-buzon.json", {"mensajes": [m.get("Subject") for m in correos]})
    a.apuntar(PRUEBA, "no se envía ningún correo", len(correos) == 0, f"{len(correos)} correos en el buzón")
    resumen = a.app_api("GET", "/api/apartados/resumen")[1]
    a.apuntar(PRUEBA, "no se crea ni toca ningún apartado", resumen.get("total") == 0, f"total apartados={resumen.get('total')}")
    return a.finalizar("resumen-escenario-h.txt")


if __name__ == "__main__":
    sys.exit(main())
