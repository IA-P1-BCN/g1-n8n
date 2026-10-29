# Spec SDD · Flujo 06 · Recordatorios de vencimiento

> **Historia**: US-06 ([issue #47](https://github.com/IA-P1-BCN/g1-n8n/issues/47)) · **Nivel**: 🟡 Medio · **Vocabulario**: [`GLOSSARY.md`](../GLOSSARY.md)

## Disparador

Flujo programado diario con soporte de ejecución manual para pruebas y demostraciones:

1. **Programado** (`Cada mañana a las 09:00`, `n8n-nodes-base.scheduleTrigger`): se ejecuta todos los días a las `09:00` (`0 9 * * *`, zona horaria `Europe/Madrid`).
2. **Manual** (`Al ejecutar manualmente`, `n8n-nodes-base.manualTrigger`): permite lanzarlo bajo demanda desde el editor de n8n o por CLI (`n8n execute --id=pFlujo06RecordatoriosVencimiento`).

## Entradas

- `GET /api/apartados?estado=activo` en la API de la tienda (`http://tienda:8000`, autenticado con la cabecera `X-API-Key: {{ $env.API_KEY }}`).
- De cada **apartado** en estado `activo` se utilizan los campos devueltos por la app (**sin recalcular importes**):
  - `id`, `cliente`, `email`, `telefono`, `producto`, `talla`, `precio`, `abonado`, `pendiente` y `fecha_limite`.
- Estado de avisos ya enviados:
  - En producción: `staticData` global del flujo (`$getWorkflowStaticData('global').enviados`).
  - En el entorno local con ejecuciones CLI (`n8n execute`): verificación adicional contra el buzón de Mailpit (`http://mailpit:8025/api/v1/messages`) mediante la referencia única `apartado-{id}-aviso-{dias}d-{fecha_limite}`, garantizando que ninguna ejecución repetida en el mismo día duplique un aviso.

## Reglas de negocio y selección

1. **Cálculo de días hasta el vencimiento**:
   - Se toma la fecha actual en zona `Europe/Madrid` (`AAAA-MM-DD`).
   - Para cada apartado `activo`, se calcula `dias_restantes = (fecha_limite - hoy)` en días naturales.
   - Solo se seleccionan los apartados cuyo plazo vence en **exactamente 7 días** (`dias_restantes === 7`) o en **exactamente 1 día** (`dias_restantes === 1`, mañana).
2. **Deduplicación (un solo aviso por umbral)**:
   - Cada aviso se identifica con la clave `apartado-{id}-aviso-{dias_restantes}d-{fecha_limite}`.
   - Si ese aviso ya figura como enviado, se omite para que el cliente reciba cada recordatorio (**7 días** y **1 día**) **una sola vez**.

## Salidas

1. **Cliente con email · vence en 7 días** (`dias_restantes === 7`):
   - Nodo: `Enviar recordatorio de 7 días al cliente` (`SMTP Mailpit (pruebas)`).
   - Asunto: `👟 Tu apartado vence en 7 días · Zapatería Paso Firme`
   - Cuerpo (HTML): recuerda al cliente su `producto` (`talla`), `precio`, `abonado`, lo que queda **`pendiente`** por pagar y la **`fecha_limite`** (`DD/MM/AAAA` y `AAAA-MM-DD`).
2. **Cliente con email · vence en 1 día** (`dias_restantes === 1`):
   - Nodo: `Enviar recordatorio de 1 día al cliente` (`SMTP Mailpit (pruebas)`).
   - Asunto: `⏰ Mañana vence tu apartado · Zapatería Paso Firme`
   - Cuerpo (HTML): avisa de que el plazo termina mañana (`1 día`), detallando el importe **`pendiente`** y la **`fecha_limite`**.
3. **Cliente sin email** (`email` vacío o nulo):
   - Nodo: `Avisar a la tienda (cliente sin email)` (`toEmail: cambia-esta-direccion@paso-firme.local`).
   - Asunto: `👟 Recordatorio sin email ({dias_restantes}d) · apartado nº {id}`
   - Cuerpo (HTML): avisa a Marisa/Dependienta con el teléfono del cliente, el importe `pendiente` y la `fecha_limite` para que le avisen por teléfono, sin que el flujo falle.
4. Para los apartados cuyo plazo aún no ha vencido (`dias_restantes === 7` o `dias_restantes === 1`), no se modifica el estado en la app. Los apartados activos fuera de plazo (`dias_restantes < 0`) se vencen por API en una segunda rama del mismo flujo según [`specs/flujo-06-apartados-vencidos-vale.md`](flujo-06-apartados-vencidos-vale.md) (US-07).

## Casos de error

| Caso | Comportamiento |
|---|---|
| No hay apartados que venzan en 7 ni en 1 día | El nodo de selección devuelve 0 items y la ejecución termina en `success` sin enviar correos |
| El flujo se ejecuta dos o más veces el mismo día | Los avisos ya enviados se filtran por su clave de deduplicación: se envían `0` correos repetidos |
| Apartado sin `email` del cliente | Rama `false` de `¿El cliente tiene email?` → envía aviso a la tienda sin fallar |
| API de la tienda caída (`5xx`/conexión) o clave `401` | `Consultar apartados activos` falla → lo captura el **Flujo 08 · Aviso de fallo** (`settings.errorWorkflow`) |
| Servidor SMTP caído | El nodo de correo falla → lo captura el **Flujo 08 · Aviso de fallo** |

## Criterios de aceptación

Los de la historia ([issue #47](https://github.com/IA-P1-BCN/g1-n8n/issues/47)), verificados automáticamente por `tests/us-06/` y su evidencia en `docs/evidencia/us-06/`:

- **Escenario A — Aviso con 7 días** (`escenario-a-aviso-7-dias.py`): con un apartado activo cuya `fecha_limite` es dentro de 7 días (`fecha = hoy - 83 días`), al ejecutar el flujo el cliente recibe el correo de recordatorio de 7 días con el importe `pendiente` y la `fecha_limite` exactos de la app.
- **Escenario B — Aviso con 1 día** (`escenario-b-aviso-1-dia.py`): con un apartado activo cuya `fecha_limite` es mañana (`fecha = hoy - 89 días`), al ejecutar el flujo el cliente recibe el correo de recordatorio de 1 día con el importe `pendiente` y la `fecha_limite` exactos de la app.
- **Escenario C — Sin duplicados** (`escenario-c-sin-duplicados.py`): al volver a ejecutar el flujo el mismo día, ningún cliente recibe un segundo correo por el mismo aviso (`0` duplicados).

## Notas de arquitectura

- **Identificador del flujo**: `pFlujo06RecordatoriosVencimiento`.
- **Fichero**: `workflows/flujo-06-recordatorios-vencimiento.json`.
- **Credenciales**: `SMTP Mailpit (pruebas)` para el envío de correos y `$env.API_KEY` para autenticar las consultas a `http://tienda:8000`.
- **Manejo de errores**: `settings.errorWorkflow = pFlujo08AvisoFallo`.
