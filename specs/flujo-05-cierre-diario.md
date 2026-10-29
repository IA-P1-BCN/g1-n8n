# Spec SDD · Flujo 05 · Cierre diario

> **Historia**: US-04 ([issue #16](https://github.com/IA-P1-BCN/g1-n8n/issues/16)) · **Nivel**: 🟢 Esencial · **Vocabulario**: [`GLOSSARY.md`](../GLOSSARY.md)
>
> Cada noche, Marisa recibe el **Cierre diario**: lo cobrado en el día (ventas + abonos) **separado por forma de pago**, para cerrar la caja sin sumar con calculadora. Si no hubo movimientos, el resumen lo dice en vez de fallar.

## Ontología (entidades que toca el flujo)

| Entidad | Atributos usados | De dónde sale |
|---|---|---|
| **Venta** | `importe`, `forma_pago`, `fecha` | API (`GET /api/ventas?desde&hasta`) |
| **Abono** | `importe`, `forma_pago`, `fecha` | API (`GET /api/abonos?desde&hasta`) |
| **Forma de pago** | `efectivo` \| `tarjeta` \| `bizum` | enum de la app (`GLOSSARY.md`) |
| **Cierre diario** | ventas y abonos del día por forma de pago + total | lo **calcula el flujo** (no se guarda en la app) |

El flujo **solo lee y suma**: no registra nada en la app. Los importes son los que da la app, sin recalcular reglas.

## Disparador

Dos entradas a la misma lógica:

1. **Programado** — cada noche a las **22:00** (`scheduleTrigger`, cron `0 22 * * *`, zona `Europe/Madrid`).
2. **Manual** (`manualTrigger`) — para pruebas y para re-lanzar un cierre a mano.

El día del cierre es **hoy** por defecto; un `fecha` (`YYYY-MM-DD`) en el item de entrada lo sobre-escribe (útil para re-lanzar el cierre de un día concreto).

## Entradas

- **API de la app** (cabecera `X-API-Key` con `$env.API_KEY`, igual que los Flujos 06/07): `GET /api/ventas?desde=HOY&hasta=HOY` y `GET /api/abonos?desde=HOY&hasta=HOY`.
- No hay webhook ni evento: el cierre es un proceso programado, no reacciona a la app.

## Salidas

**Un correo a Marisa** (HTML) con el cierre del día:

- Asunto: `🧾 Cierre de caja del DD/MM/AAAA · Zapatería Paso Firme`.
- Cuerpo (día **con** movimientos): tabla por **forma de pago** (`efectivo`, `tarjeta`, `bizum`) con tres columnas — **ventas**, **abonos** y **total** de esa forma — y una fila de **totales**: total de ventas directas, total de abonos y **total cobrado del día**. Incluye cuántas ventas y cuántos abonos se contaron.
- Cuerpo (día **sin** movimientos): el mismo correo pero diciendo claramente que **hoy no hubo ventas ni abonos** (el flujo **no falla**).

El flujo **no modifica la app** (constatación).

## Casos de error

| Caso | Comportamiento |
|---|---|
| Día sin ventas ni abonos | Correo de «sin movimientos» (el flujo **no** falla) — Escenario B |
| Forma de pago inesperada en un registro | Se cuenta como `efectivo` (defensivo); nunca se pierde importe del total |
| API caída o 5xx | El nodo HTTP falla → lo captura el **Flujo 08 · Aviso de fallo** (`settings.errorWorkflow`) |
| Fallo de envío (SMTP) | Igual: lo captura el Flujo 08 |

## Criterios de aceptación

Los de la issue (US-04), verificados por `tests/us-04/` y su evidencia en `docs/evidencia/us-04/`:

- **Escenario A — día con movimientos**: se registran ventas y abonos por varias formas de pago; al ejecutar el flujo, llega el resumen con **ventas, abonos y total separados por forma de pago**, y los **importes coinciden con los de la app**.
- **Escenario B — día sin movimientos**: al ejecutar el flujo sin datos del día, el resumen **lo dice** en vez de fallar.

La evidencia es el correo capturado en Mailpit (asunto + cifras del cuerpo) y el resultado de cada criterio; el flujo se dispara en los tests por el CLI de n8n (`n8n execute --id=pFlujo05CierreDiario`).

## Notas de arquitectura

- **Mismo patrón que los Flujos 06 y 07** (programados): `scheduleTrigger` + `manualTrigger` → nodos *Code* que consultan la API con `this.helpers.httpRequest` y `$env.API_KEY`, suman, montan el HTML y envían con *Send Email* (credencial `SMTP Mailpit (pruebas)`; en producción, SMTP real).
- **Ventas del día** = ventas directas + abonos cobrados ese día (incluido el abono inicial), como define `business-rules.md`. Se consultan **filtrando por fecha en la API** (`desde=hasta=HOY`).
- **Sin credencial de API propia**: se reutiliza `$env.API_KEY` (la misma clave del `.env`), como los Flujos 06/07; no hace falta la credencial `API tienda (X-API-Key)` del Flujo 03.
- **`errorWorkflow = Flujo 08`** en los ajustes: cualquier fallo (API o SMTP) avisa a la tienda.
- `toEmail` de prueba (`cambia-esta-direccion@paso-firme.local`) sustituible por el correo real de la tienda.
