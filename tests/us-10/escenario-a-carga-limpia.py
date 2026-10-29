#!/usr/bin/env python3
"""Escenario A — Carga limpia del Excel antiguo (US-10, criterios 1, 2 y 3).

Vacía la base de datos de la tienda, ejecuta el Flujo 09 con los CSV reales de `data/` y
comprueba por API que se crean los 7 apartados válidos, sus 3 abonos posteriores y las 6 ventas
directas, conservando las fechas originales y limpiando nombres (`carmen ruiz` → `Carmen Ruiz`)
e importes con símbolo `€` (`15€` → `15.0`).
"""

import sys

import ayudantes as a

PRUEBA = "carga-limpia"


def main():
    a.preparar_salida()
    print("— Escenario A · Carga limpia del Excel antiguo —")

    a.limpiar_base()
    ok_exec, salida_cli = a.ejecutar_migracion()
    a.apuntar(PRUEBA, "el Flujo 09 se ejecuta sin error", ok_exec, "n8n execute OK" if ok_exec else salida_cli[-200:])

    estado_ap, apartados = a.api_tienda("/api/apartados")
    estado_ab, abonos = a.api_tienda("/api/abonos")
    estado_ve, ventas = a.api_tienda("/api/ventas")

    apartados = apartados if isinstance(apartados, list) else []
    abonos = abonos if isinstance(abonos, list) else []
    ventas = ventas if isinstance(ventas, list) else []

    a.guardar("escenario-a-carga-limpia.json", {
        "status_apartados": estado_ap,
        "total_apartados": len(apartados),
        "apartados": apartados,
        "status_abonos": estado_ab,
        "total_abonos": len(abonos),
        "abonos": abonos,
        "status_ventas": estado_ve,
        "total_ventas": len(ventas),
        "ventas": ventas,
    })

    clientes = {ap["cliente"]: ap for ap in apartados}
    esperados = {
        "Carmen Ruiz",
        "Jorge Martín",
        "Ana Torres",
        "Pedro Sanz",
        "Rosa Díaz",
        "Miguel Ángel López",
        "Sofía Navarro",
    }
    a.apuntar(
        PRUEBA,
        "se crean los 7 apartados válidos por API",
        len(apartados) == 7 and set(clientes) == esperados,
        f"total={len(apartados)} · clientes={sorted(clientes)}",
    )

    carmen = clientes.get("Carmen Ruiz") or {}
    a.apuntar(
        PRUEBA,
        "nombres normalizados (Carmen Ruiz agrupa 'Carmen Ruiz' y 'carmen ruiz')",
        carmen.get("fecha") == "2026-09-02" and carmen.get("abonado") == 30.0 and carmen.get("pendiente") == 59.9,
        f"fecha={carmen.get('fecha')} · abonado={carmen.get('abonado')} · pendiente={carmen.get('pendiente')}",
    )

    jorge = clientes.get("Jorge Martín") or {}
    a.apuntar(
        PRUEBA,
        "fechas originales conservadas (Jorge Martín 02/09/2026 + abono 12/09/2026)",
        jorge.get("fecha") == "2026-09-02" and jorge.get("abonado") == 35.0 and jorge.get("pendiente") == 29.5,
        f"fecha={jorge.get('fecha')} · abonado={jorge.get('abonado')} · pendiente={jorge.get('pendiente')}",
    )

    ana = clientes.get("Ana Torres") or {}
    a.apuntar(
        PRUEBA,
        "fecha corta '7/9/26' e importe '15€' limpiados en Ana Torres (+ abono de 20 €)",
        ana.get("fecha") == "2026-09-07" and ana.get("abonado") == 35.0 and ana.get("pendiente") == 37.0,
        f"fecha={ana.get('fecha')} · abonado={ana.get('abonado')} · pendiente={ana.get('pendiente')}",
    )

    fechas_abonos = sorted(ab["fecha"] for ab in abonos)
    a.apuntar(
        PRUEBA,
        "se registran los 10 abonos (7 iniciales + 3 posteriores) con sus fechas originales",
        len(abonos) == 10 and "2026-09-05" in fechas_abonos and "2026-09-12" in fechas_abonos and "2026-10-03" in fechas_abonos,
        f"total={len(abonos)} · fechas={fechas_abonos}",
    )

    conceptos_ventas = [v["concepto"] for v in ventas]
    tiene_apuntes_abono = any("abono" in c.lower() or "apartado" in c.lower() or "total" in c.lower() for c in conceptos_ventas)
    a.apuntar(
        PRUEBA,
        "se cargan las 6 ventas directas excluyendo apuntes de abonos y el total a mano",
        len(ventas) == 6 and not tiene_apuntes_abono,
        f"total={len(ventas)} · conceptos={conceptos_ventas}",
    )

    sys.exit(a.finalizar("resumen-escenario-a.txt"))


if __name__ == "__main__":
    main()
