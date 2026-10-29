#!/usr/bin/env python3
"""Escenario C — Casos dudosos excluidos y listados en el informe a Marisa (US-10).

Comprueba que el apartado de Lucía Gómez (abono inicial de 4 € < 5 € mínimo) y su fila posterior
del 20/09/2026 NO se cargan en la app, y que Marisa recibe por correo el informe de casos dudosos
con los datos para decidir.
"""

import sys

import ayudantes as a

PRUEBA = "casos-dudosos"


def main():
    a.preparar_salida()
    print("— Escenario C · Casos dudosos e informe a Marisa —")

    conocidos = a.mensajes_actuales()
    ok_exec, salida_cli = a.ejecutar_migracion()
    a.apuntar(PRUEBA, "el Flujo 09 se ejecuta y genera el informe", ok_exec, "n8n execute OK" if ok_exec else salida_cli[-200:])

    _, apartados = a.api_tienda("/api/apartados")
    _, abonos = a.api_tienda("/api/abonos")
    apartados = apartados if isinstance(apartados, list) else []
    abonos = abonos if isinstance(abonos, list) else []

    clientes = [ap["cliente"] for ap in apartados]
    lucia_en_app = any("lucía" in c.lower() or "lucia" in c.lower() for c in clientes)
    a.apuntar(
        PRUEBA,
        "Lucía Gómez (abono inicial 4 € < 5 €) NO se carga en apartados",
        not lucia_en_app,
        f"clientes={clientes}",
    )

    abonos_lucia = [ab for ab in abonos if ab.get("importe") in (4.0, 41.0) or ab.get("fecha") in ("2026-09-03", "2026-09-20")]
    a.apuntar(
        PRUEBA,
        "las filas de 4 € (03/09) y 41 € (20/09) de Lucía Gómez NO están en abonos",
        len(abonos_lucia) == 0,
        f"abonos_lucia={abonos_lucia}",
    )

    informe = a.esperar_informe(conocidos)
    if not informe:
        a.apuntar(PRUEBA, "llega el correo con el informe de casos dudosos a Mailpit", False, "timeout esperando correo")
        sys.exit(a.finalizar("resumen-escenario-c.txt"))

    asunto = informe.get("Subject") or ""
    html = informe.get("HTML") or informe.get("Text") or ""
    a.guardar("escenario-c-casos-dudosos.json", {
        "id": a.identificador(informe),
        "asunto": asunto,
        "from": informe.get("From"),
        "to": informe.get("To"),
        "html": html,
    })

    a.apuntar(PRUEBA, "llega el correo con el informe de casos dudosos a Mailpit", True, asunto)
    a.apuntar(
        PRUEBA,
        "el informe lista a Lucía Gómez y el producto Sandalia tacón negra",
        "Lucía Gómez" in html and "Sandalia tacón negra" in html,
        "Lucía Gómez · Sandalia tacón negra presentes en HTML",
    )
    a.apuntar(
        PRUEBA,
        "el informe explica el motivo (abono inicial 4 € menor del mínimo de 5 €) y la fila del 20/09",
        "4" in html and "5" in html and ("20/09/2026" in html or "2026-09-20" in html),
        "motivo (< 5 €) y fila asociada (20/09/2026) presentes",
    )

    sys.exit(a.finalizar("resumen-escenario-c.txt"))


if __name__ == "__main__":
    main()
