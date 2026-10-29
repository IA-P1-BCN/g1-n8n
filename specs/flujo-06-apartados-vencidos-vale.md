# Spec SDD · Flujo 06 · Apartados vencidos con su vale

> **Historia**: US-07 ([issue #52](https://github.com/IA-P1-BCN/g1-n8n/issues/52)) · **Nivel**: 🟡 Medio · **Vocabulario**: [`GLOSSARY.md`](../GLOSSARY.md) · **Relacionado**: [`specs/flujo-06-recordatorios-vencimiento.md`](flujo-06-recordatorios-vencimiento.md) (US-06)

## Disparador

El **Flujo 06 · Recordatorios de vencimiento** (`pFlujo06RecordatoriosVencimiento`) se ejecuta cada mañana para gestionar tanto los recordatorios previos (7 y 1 día, US-06) como los **apartados fuera de plazo con generación de vale** (US-07):

1. **Programado** (`Cada mañana a las 09:00`, `n8n-nodes-base.scheduleTrigger`): todos los días a las `09:00` (`0 9 * * *`, zona horaria `Europe/Madrid`).
2. **Manual** (`Al ejecutar manualmente`, `n8n-nodes-base.manualTrigger`): ejecución bajo demanda desde el editor de n8n o por CLI (`n8n execute --id=pFlujo06RecordatoriosVencimiento`).

## Entradas

- `GET /api/apartados?estado=activo` en la API de la tienda (`http://tienda:8000`, autenticado con `X-API-Key: {{ $env.API_KEY }}`).
- De cada **apartado** en estado `activo` se consulta su `fecha_limite` (`AAAA-MM-DD`).
- Los importes y códigos se toman directamente de la respuesta oficial de `POST /api/apartados/{id}/vencer` (`vale.codigo`, `vale.importe` y `apartado`), **sin recalcular nada en n8n**.

## Reglas de negocio y procesamiento

1. **Detección de apartados fuera de plazo**:
   - Se toma la fecha actual en zona `Europe/Madrid` (`hoy`, formato `AAAA-MM-DD`).
   - Todo apartado en estado `activo` cuya `fecha_limite < hoy` (`dias_restantes < 0`) ha superado los 90 días de plazo sin liquidarse.
2. **Vencimiento por API y generación de vale**:
   - Para cada apartado fuera de plazo se invoca `POST http://tienda:8000/api/apartados/{id}/vencer` con cabecera `X-API-Key: {{ $env.API_KEY }}`.
   - La app cambia el estado del apartado a `vencido` y genera automáticamente un **Vale** (`VALE-00001`, etc.) por el total `abonado` hasta la fecha, devolviendo `{ apartado, vale }`.
   - Dado que el apartado pasa a estado `vencido` en la base de datos de la tienda, una segunda ejecución del flujo en el mismo día ya no lo recibe en `GET /api/apartados?estado=activo` (idempotencia garantizada por estado).
3. **Notificación al cliente con su vale**:
   - Si el cliente tiene `email`, recibe un correo con el `codigo` del vale y su `importe` en euros para canjearlo en cualquier compra en la tienda.
   - Si el cliente no tiene `email`, se envía un aviso a la tienda (`cambia-esta-direccion@paso-firme.local`) indicando el `codigo` y el `importe` del vale y su teléfono para que le avisen sin que el flujo falle.
4. **Resumen para Marisa (zapatos que vuelven a la venta)**:
   - Cuando en la ejecución se vence al menos un apartado, se envía un único correo de resumen a la tienda (`cambia-esta-direccion@paso-firme.local`) con la **lista de zapatos que vuelven a la venta** (`producto`, `talla`, `cliente`, `codigo` e `importe` del vale).

## Salidas

1. **Estado en la app (`POST /api/apartados/{id}/vencer`)**:
   - El apartado pasa a `estado = "vencido"`.
   - Se registra el vale en `/api/vales` con `codigo` (`VALE-XXXXX`) e `importe` igual al `abonado`.
2. **Correo al cliente con su vale** (si tiene `email`):
   - Nodo: `Enviar vale por apartado vencido al cliente` (`SMTP Mailpit (pruebas)`).
   - Asunto: `🎟️ Tu vale por apartado vencido ({{ $json.vale.codigo }}) · Zapatería Paso Firme`
   - Cuerpo (HTML): informa de que el plazo del apartado (`producto`, `talla`, `fecha_limite`) ha vencido y entrega el **Vale** con su **`codigo`** y su **`importe`**.
3. **Aviso a la tienda si el cliente no tiene email**:
   - Nodo: `Avisar a la tienda (vale sin email)` (`toEmail: cambia-esta-direccion@paso-firme.local`).
   - Asunto: `🎟️ Vale generado sin email ({{ $json.vale.codigo }}) · apartado nº {{ $json.id }}`
4. **Aviso a Marisa con los zapatos que vuelven a la venta**:
   - Nodo: `Avisar a Marisa de zapatos que vuelven a la venta` (`toEmail: cambia-esta-direccion@paso-firme.local`).
   - Asunto: `👟 Apartados vencidos hoy: {{ $json.total_vencidos }} par(es) vuelven a la venta · Zapatería Paso Firme`
   - Cuerpo (HTML): tabla con todos los apartados vencidos en la ejecución (`id`, `producto`, `talla`, `cliente`, `codigo` del vale e `importe` del vale) para que Marisa devuelva los pares al expositor/estantería de venta.

## Casos de error

| Caso | Comportamiento |
|---|---|
| No hay apartados fuera de plazo (`fecha_limite < hoy`) | La rama de vencimientos no emite items, no llama a `/vencer` y no envía correo a Marisa; el flujo termina en `success` |
| Cliente del apartado vencido sin `email` | Rama `false` de `¿El cliente del apartado vencido tiene email?` → avisa a la tienda con los datos del vale y el teléfono del cliente sin que el flujo falle |
| API de la tienda caída (`5xx`/conexión) o fallo en `POST /api/apartados/{id}/vencer` | El nodo falla y salta el **Flujo 08 · Aviso de fallo** (`settings.errorWorkflow = pFlujo08AvisoFallo`) |
| Servidor SMTP caído | El nodo de correo falla y salta el **Flujo 08 · Aviso de fallo** |

## Criterios de aceptación

Los de la historia ([issue #52](https://github.com/IA-P1-BCN/g1-n8n/issues/52)), verificados automáticamente por `tests/us-07/` y su evidencia en `docs/evidencia/us-07/`:

- **Escenario A — Vencer un fuera de plazo** (`escenario-a-vencer-fuera-de-plazo.py`): al ejecutar el flujo con un apartado `activo` cuya `fecha_limite` ya pasó, el apartado queda en estado `vencido` en `GET /api/apartados/{id}` y la app ha generado su `vale` en `GET /api/vales` con el importe abonado. Los apartados dentro de plazo siguen `activos`.
- **Escenario B — Cliente con su vale** (`escenario-b-cliente-con-su-vale.py`): el mensaje enviado al cliente por correo incluye el `codigo` (`VALE-...`) y el `importe` del vale generado por la app.
- **Escenario C — Marisa al día** (`escenario-c-marisa-al-dia.py`): el aviso enviado a la tienda (`cambia-esta-direccion@paso-firme.local`) incluye la lista de zapatos (`producto`, `talla`, `cliente` y `codigo` del vale) que vuelven a ponerse a la venta.
