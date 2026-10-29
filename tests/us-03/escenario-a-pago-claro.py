#!/usr/bin/env python3
"""Escenario A — Pago claro por nombre (US-03): 01_bizum_carmen y 09_bizum_silvia.

El nombre del ordenante coincide con un único apartado activo: se registra el abono y el cliente
recibe su recibo (vía Flujo 02).

Uso:  python tests/us-03/escenario-a-pago-claro.py   (requiere app+n8n+mailpit; RESETEA los datos de la app)
"""

import sys

import ayudantes as a

PRUEBA = "A-pago-claro"


def caso(nombre_eml, apt, email, importe):
    asunto, cuerpo = a.aviso_desde_eml(nombre_eml)
    t0 = a.ahora()
    payload, _ = a.enviar_aviso(asunto, cuerpo)
    ejec = a.esperar_ejecucion(t0)
    a.guardar(f"escenario-a-{nombre_eml}-payload.json", payload)
    a.guardar(f"escenario-a-{nombre_eml}-ejecucion.json", a.resumen_ejecucion(ejec))
    a.apuntar(PRUEBA, f"{nombre_eml}: ejecución del Flujo 03", bool(ejec) and ejec.get("status") == "success",
              ejec.get("status") if ejec else "sin ejecución")
    a.apuntar(PRUEBA, f"{nombre_eml}: el flujo registra el abono", a.camino(ejec) == "registrado", a.camino(ejec))
    despues = a.apartado(apt["id"])
    esperado = round(apt["pendiente"] - importe, 2)
    a.apuntar(PRUEBA, f"{nombre_eml}: pendiente baja a {esperado} €",
              round(despues.get("pendiente", -1), 2) == esperado, f"pendiente={despues.get('pendiente')}")
    a.apuntar(PRUEBA, f"{nombre_eml}: el apartado sigue activo", despues.get("estado") == "activo", despues.get("estado"))
    recibo = a.esperar_correo(lambda m: a.para(email)(m) and a.asunto_contiene("recibo")(m))
    a.guardar(f"escenario-a-{nombre_eml}-recibo.json", {"asunto": (recibo or {}).get("Subject"), "to": a.destinatarios(recibo or {})})
    a.apuntar(PRUEBA, f"{nombre_eml}: el cliente recibe su recibo (Flujo 02)", bool(recibo),
              (recibo or {}).get("Subject", "sin recibo"))


def main():
    a.preparar(PRUEBA)
    carmen = a.crear_apartado("Carmen Ruiz", "carmen.ruiz@prueba.local", "Zueco sanitario", 50.0, 5.0)
    silvia = a.crear_apartado("Silvia Cortés", "silvia.cortes@prueba.local", "Sandalia playa", 30.0, 5.0)
    caso("01_bizum_carmen", carmen, "carmen.ruiz@prueba.local", 10.0)
    caso("09_bizum_silvia", silvia, "silvia.cortes@prueba.local", 5.0)
    return a.finalizar("resumen-escenario-a.txt")


if __name__ == "__main__":
    sys.exit(main())
