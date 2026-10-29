#!/usr/bin/env python3
"""Escenario C — Sin duplicados al volver a ejecutar el mismo día (US-06, criterio 3).

Con los apartados que vencen en 7 días y en 1 día ya avisados hoy, vuelve a ejecutar
el Flujo 06 completo y comprueba que nadie recibe el mismo aviso dos veces (0 correos nuevos).
"""

import sys
import time
from datetime import date, timedelta

import ayudantes as a

PRUEBA = "sin-duplicados"


def main():
    a.preparar_salida()
    print("— Escenario C · Re-ejecución el mismo día sin duplicados —")

    _, apartados = a.api_tienda("/api/apartados?estado=activo")
    apartados = apartados if isinstance(apartados, list) else []
    emails = {ap.get("email") for ap in apartados}

    # Si este test se ejecuta en solitario, prepara antes los apartados de 7d y 1d y lanza la 1.ª pasada
    if "elena.7d@paso-firme.local" not in emails or "marcos.1d@paso-firme.local" not in emails:
        a.limpiar_base()
        a.limpiar_buzon()
        hoy = date.today()
        a.crear_apartado("Elena Siete Días", "elena.7d@paso-firme.local", "Botín piel marrón", "38", 89.90, 20.00, hoy - timedelta(days=83))
        a.crear_apartado("Marcos Un Día", "marcos.1d@paso-firme.local", "Zapatilla running azul", "42", 64.50, 15.00, hoy - timedelta(days=89))
        time.sleep(1.5)
        a.ejecutar_flujo()
        time.sleep(1.0)

    conocidos_antes = a.mensajes_actuales()

    ok_exec, salida_cli = a.ejecutar_flujo()
    time.sleep(1.5)
    nuevos = a.recordatorios_nuevos(conocidos_antes)

    a.guardar("escenario-c-sin-duplicados.json", {
        "mensajes_antes_de_reejecutar": len(conocidos_antes),
        "recordatorios_nuevos_en_segunda_ejecucion": nuevos,
        "total_nuevos": len(nuevos),
    })

    a.apuntar(
        PRUEBA,
        "la segunda ejecución del Flujo 06 el mismo día termina sin error",
        ok_exec,
        "n8n execute OK" if ok_exec else salida_cli[-200:],
    )
    a.apuntar(
        PRUEBA,
        "nadie recibe el mismo aviso dos veces (0 recordatorios duplicados)",
        len(nuevos) == 0,
        f"recordatorios_nuevos={len(nuevos)}",
    )

    sys.exit(a.finalizar("resumen-escenario-c.txt"))


if __name__ == "__main__":
    main()
