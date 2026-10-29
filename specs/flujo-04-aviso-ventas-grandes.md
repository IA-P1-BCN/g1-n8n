# Spec SDD · Flujo 04 · Aviso de ventas grandes

> **Historia**: US-09 ([issue #62](https://github.com/IA-P1-BCN/g1-n8n/issues/62)) · **Nivel**: 🟡 Medio · **Vocabulario**: [`GLOSSARY.md`](../GLOSSARY.md)
>
> Sub-flujo enganchado a la rama `venta.registrada` del [`Receptor · Webhook tienda`](receptor-webhook-tienda.md): cuando la Dependienta registra en la app una venta por encima del umbral configurado, Marisa recibe un aviso aun sin estar en la tienda.

## Disparador

`n8n-nodes-base.executeWorkflowTrigger` (`inputSource: passthrough`): lo llama `Ejecutar Flujo 04` desde el Receptor cuando el evento es `venta.registrada`. El item de entrada es `{ evento, datos }` con `datos = { id, fecha, concepto, importe, forma_pago }` (ver [eventos de la app](receptor-webhook-tienda.md#entradas)).

No hay disparador manual: en Editar > Selecciona se puede ejecutar el Receptor con el payload de [`payloads/venta-registrada.json`](../payloads/venta-registrada.json) para probarlo.

## Entradas

| Campo | Tipo | Nota |
|---|---|---|
| `datos.importe` | número | lo que compara con el umbral |
| `datos.concepto`, `datos.forma_pago`, `datos.fecha`, `datos.id` | texto | van al aviso para dar contexto |

**Umbral (variable de entorno, no editable en el flujo):**

| Variable | Dónde se configura | Por defecto |
|---|---|---|
| `UMBRAL_VENTA_GRANDE` | `.env` del repo → `docker-compose.yml` → entorno del contenedor n8n | `200` |

El nodo `Umbral de venta grande` lo lee con `$env.UMBRAL_VENTA_GRANDE` (la instancia tiene `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`), lo convierte a número y añade `es_venta_grande = importe > umbral` al item. Un valor mal puesto (texto, vacío, 0) cae al por defecto `200` en vez de romper el flujo.

Cambiar el umbral = cambiar el valor en `.env` y recrear el contenedor (`task arrancar`): **sin editar el flujo en n8n** (criterio B de la historia).

## Salidas

| Nodo | Cuándo | Qué |
|---|---|---|
| `Enviar aviso a Marisa` (`emailSend`) — rama «true» | `datos.importe > umbral` | correo HTML de remitente `n8n@paso-firme.local` a `cambia-esta-direccion@paso-firme.local` con asunto `🧾 Venta grande · {importe} € · {concepto}` y los datos de la venta más el umbral aplicado |
| `Sin aviso (venta pequeña)` (`noOp`) — rama «false» | `datos.importe <= umbral` | termina sin hacer nada: la ejecución queda en Executions y no sale correo |

Destinatario placeholder igual que en el Flujo 02: en producción se cambia la dirección en el propio nodo (o se pasa a variable) — no hay datos de cliente reales en el repo.

## Casos de error

| Caso | Comportamiento |
|---|---|
| Receptor no enruta | es fallo del receptor: avisa el Flujo 08 desde el padre (probado en US-05) |
| Fallo del envío SMTP | el flujo falla → Flujo 08 · Aviso de fallo (el `errorWorkflow` está en este flujo y en el Receptor) |
| `importe` no numérico | `Number("x")` → `NaN`, `NaN > umbral` es `false` → se va la rama «false», sin aviso y sin error |
| Umbral mal configurado | el nodo cae al por defecto `200`; no rompe la ejecución |
| Fallo de la app al avisar | la app ya no espera a n8n (ver receptor): ningún evento bloquea una venta |

## Criterios de aceptación

Los de [issue #62](https://github.com/IA-P1-BCN/g1-n8n/issues/62), verificados por `tests/us-09/` con evidencia en `docs/evidencia/us-09/`:

1. **Escenario A — venta sobre el umbral** (`escenario-a-venta-sobre-umbral.py`): registrar por API (`POST /api/ventas`, que la app propaga como `venta.registrada`) una venta superior al umbral → Marisa recibe el aviso con los datos de esa venta.
2. **Escenario B — cambiar el umbral sin editar el flujo** (`escenario-b-umbral-cambiado.py`): subir la variable `UMBRAL_VENTA_GRANDE` en `.env` recreando n8n; una venta entre el umbral antiguo y el nuevo NO genera aviso; una venta por encima del nuevo, sí. Se restaura el umbral original al salir.

## Notas de arquitectura

- **Entra por el Receptor, no por su cuenta**: ningún webhook propio; añadirlo a más eventos = conectar otra salida del Switch.
- **Un IF, sin datos en el flujo**: la única lógica es comparar contra la variable; el aviso es plantilla del evento.
- **`errorWorkflow = Flujo 08 · Aviso de fallo`** y `executionOrder: v1` como el resto de sub-flujos.
