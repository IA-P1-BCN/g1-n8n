#!/usr/bin/env python3
"""Escenario A — Informe del día 1 (US-08, criterios 1–4).

Comprueba que el Flujo 07 se ejecuta correctamente para el mes anterior,
calcula la recaudación con ventas y abonos por separado, suma el total pendiente de cobro,
cuenta los apartados nuevos, liquidados y vencidos, y envía el correo con importes que coinciden
exactamente con la API de la tienda.

Uso:  python tests/us-08/escenario-a-informe-dia-1.py
      (requiere el stack local levantado con `task arrancar` y flujos importados con `task importar`)
Salida: evidencia en docs/evidencia/us-08/ y exit code 1 si algún criterio falla.
"""

import re
import sys

import ayudantes as a

PRUEBA = "informe-dia-1"


def extraer_cuerpo(correo):
    """Devuelve el texto/HTML del correo."""
    html = correo.get("HTML") or ""
    texto = correo.get("Text") or ""
    return html + "\n" + texto


def main():
    a.preparar_salida()
    print("— Escenario A · Informe del día 1 —")

    conocidos = a.mensajes_actuales()
    desde, hasta, periodo_texto = a.calcular_periodo_mes_anterior()
    print(f"  Periodo evaluado: {periodo_texto} ({desde} al {hasta})")

    # 1. Obtener cifras directas de la API de la app
    _, ventas = a.api_tienda(f"/api/ventas?desde={desde}&hasta={hasta}")
    total_ventas = round(sum(float(v.get("importe", 0)) for v in (ventas if isinstance(ventas, list) else [])), 2)

    _, todos_abonos = a.api_tienda("/api/abonos")
    abonos_mes = [b for b in (todos_abonos if isinstance(todos_abonos, list) else []) if desde <= b.get("fecha", "") <= hasta]
    total_abonos = round(sum(float(b.get("importe", 0)) for b in abonos_mes), 2)

    total_recaudacion = round(total_ventas + total_abonos, 2)

    _, apartados = a.api_tienda("/api/apartados")
    lista_apartados = apartados if isinstance(apartados, list) else []
    apartados_activos = [ap for ap in lista_apartados if ap.get("estado") == "activo"]
    total_pendiente = round(sum(float(ap.get("pendiente", 0)) for ap in apartados_activos), 2)

    apartados_nuevos = [ap for ap in lista_apartados if desde <= ap.get("fecha", "") <= hasta]

    abonos_por_ap = {}
    for ab in (todos_abonos if isinstance(todos_abonos, list) else []):
        ap_id = ab.get("apartado_id")
        if ap_id not in abonos_por_ap:
            abonos_por_ap[ap_id] = []
        abonos_por_ap[ap_id].append(ab)

    apartados_liquidados = []
    for ap in lista_apartados:
        if ap.get("estado") == "liquidado":
            abs_ap = abonos_por_ap.get(ap.get("id"), [])
            if abs_ap:
                abs_ap.sort(key=lambda x: (x.get("fecha", ""), x.get("id", 0)))
                ultimo = abs_ap[-1]
                if desde <= ultimo.get("fecha", "") <= hasta:
                    apartados_liquidados.append(ap)

    _, vales = a.api_tienda("/api/vales")
    vales_mes = [v for v in (vales if isinstance(vales, list) else []) if desde <= v.get("fecha", "") <= hasta]

    datos_esperados = {
        "periodo_texto": periodo_texto,
        "desde": desde,
        "hasta": hasta,
        "total_ventas": total_ventas,
        "ventas_count": len(ventas if isinstance(ventas, list) else []),
        "total_abonos": total_abonos,
        "abonos_count": len(abonos_mes),
        "total_recaudacion": total_recaudacion,
        "total_pendiente": total_pendiente,
        "nuevos_count": len(apartados_nuevos),
        "liquidados_count": len(apartados_liquidados),
        "vencidos_count": len(vales_mes),
    }
    a.guardar("escenario-a-datos-esperados.json", datos_esperados)

    # 2. Ejecutar el flujo en n8n
    ok_ejec, salida_ejec = a.ejecutar_flujo()
    a.guardar("escenario-a-ejecucion-n8n.txt", salida_ejec)
    a.apuntar(PRUEBA, "ejecutar el flujo el día 1 de mes (o forzarlo manualmente)", ok_ejec,
              "exit code 0" if ok_ejec else f"falló n8n: {salida_ejec[:120]}")

    # 3. Esperar el correo en Mailpit
    correo = a.esperar_informe(conocidos, timeout=30)
    if not correo:
        a.apuntar(PRUEBA, "correo de informe mensual recibido en Mailpit", False, "timeout sin correo en Mailpit")
        sys.exit(a.finalizar("resumen-escenario-a.txt"))

    a.guardar("escenario-a-correo-recibido.json", correo)
    a.apuntar(PRUEBA, "correo de informe mensual recibido en Mailpit", True, f"ID={a.identificador(correo)}")

    asunto = correo.get("Subject") or ""
    cuerpo = extraer_cuerpo(correo)

    # 4. Comprobar que incluye la recaudación del mes anterior con ventas y abonos por separado
    str_ventas = f"{total_ventas:.2f}"
    str_abonos = f"{total_abonos:.2f}"
    str_total = f"{total_recaudacion:.2f}"

    ventas_en_correo = str_ventas in cuerpo
    abonos_en_correo = str_abonos in cuerpo
    total_en_correo = str_total in cuerpo

    a.apuntar(
        PRUEBA,
        "correo incluye recaudación del mes anterior con ventas y abonos por separado",
        ventas_en_correo and abonos_en_correo and total_en_correo,
        f"ventas={str_ventas}€ ({'OK' if ventas_en_correo else 'NO'}), "
        f"abonos={str_abonos}€ ({'OK' if abonos_en_correo else 'NO'}), "
        f"total={str_total}€ ({'OK' if total_en_correo else 'NO'})",
    )

    # 5. Comprobar que incluye el total pendiente de cobro y los apartados nuevos, liquidados y vencidos del mes
    str_pendiente = f"{total_pendiente:.2f}"
    pendiente_en_correo = str_pendiente in cuerpo
    nuevos_en_correo = f"{len(apartados_nuevos)}" in cuerpo
    liquidados_en_correo = f"{len(apartados_liquidados)}" in cuerpo
    vencidos_en_correo = f"{len(vales_mes)}" in cuerpo

    a.apuntar(
        PRUEBA,
        "correo incluye el total pendiente de cobro y apartados nuevos, liquidados y vencidos",
        pendiente_en_correo and nuevos_en_correo and liquidados_en_correo and vencidos_en_correo,
        f"pendiente={str_pendiente}€, nuevos={len(apartados_nuevos)}, "
        f"liquidados={len(apartados_liquidados)}, vencidos={len(vales_mes)}",
    )

    # 6. Verificar que los importes coinciden con los de la app
    importes_coinciden = (
        ventas_en_correo
        and abonos_en_correo
        and total_en_correo
        and pendiente_en_correo
    )
    a.apuntar(
        PRUEBA,
        "los importes del correo coinciden con los de la app",
        importes_coinciden,
        f"recaudación={str_total}€ (app {total_recaudacion}€), pendiente={str_pendiente}€ (app {total_pendiente}€)",
    )

    sys.exit(a.finalizar("resumen-escenario-a.txt"))


if __name__ == "__main__":
    main()
