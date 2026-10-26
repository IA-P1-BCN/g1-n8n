# Evidencia · US-05 Avisos de errores (Flujo 08 · Aviso de fallo)

> Historia: US-05 (issue #21) · fecha: 26/10/2026 · stack local: tienda + n8n + Mailpit

## Preparación

- Flujo 08 importado y **activo** en n8n (`workflows/flujo-08-aviso-de-fallo.json`), con nodo *Error Trigger*.
- Receptor y Flujos 01/02 apuntan a él vía `settings.errorWorkflow = pFlujo08AvisoFallo` (export de n8n):

| Flujo | id | active | errorWorkflow |
|---|---|---|---|
| Flujo 01 · Confirmación de apartado | `pwLRoxMrKVfAR2XK` | true | `pFlujo08AvisoFallo` |
| Receptor · Webhook tienda | `HXZBeAF7TZrK4zfD` | true | `pFlujo08AvisoFallo` |
| Flujo 02 · Recibo de cada abono | `pFlujo02ReciboAbono` | true | `pFlujo08AvisoFallo` |
| Flujo 08 · Aviso de fallo | `pFlujo08AvisoFallo` | true | — (no se apunta a sí mismo) |

## Escenario A — Fallo provocado ✅

1. **Fallo en el Flujo 01**: `POST http://localhost:5678/webhook/tienda` con el evento
   `apartado.creado` y `datos.email = "nadie"` (destinatario inválido para SMTP).
   El nodo **Enviar resumen al cliente** falla y n8n ejecuta el Error Workflow.
2. Aviso recibido en Mailpit (id `4S5Wwz84ldq1zNPzYgYCow`):

   - Asunto: `🛠 Aviso de fallo · Flujo 01 · Confirmación de apartado`
   - Tabla del cuerpo:
     - **Flujo**: `Flujo 01 · Confirmación de apartado`
     - **Paso**: `Enviar resumen al cliente`
     - **Error**: `No recipients defined`
     - **Cuándo**: `26/10/2026 14:53`
   - Enlace a la ejecución: `http://localhost:5678/workflow/pwLRoxMrKVfAR2XK/executions/19`

   Llegan además el aviso del Receptor (**Paso** `Ejecutar Flujo 01`, ejecución 18) y, con otro
   fallo provocado (webhook con body `[1,2,3]`, id `5krAfyLh0w4sNQ5VOUNImo`), el del nodo
   **Evento y datos** (`The 'JSON Output' in item 0 does not contain a valid JSON object`):
   el Error Workflow se ejecuta una vez por cada ejecución que falla.

Se comprueba lo pedido: **nombre del flujo**, **paso** y **error**, con enlace a la ejecución.

## Escenario B — Sin secretos ✅

1. El mismo evento del escenario A llevaba señuelos en `datos`: `password: "ULTRA-SECRETO-en82bxyz"`
   y `apikey: "AKIABADKEY123"`, para verificar que el aviso **no** los incluye.
2. Búsqueda de ambos valores en **Text** y **HTML** del aviso recibido: todo `False`.
3. El aviso solo contiene los cinco campos de la lista blanca del nodo *Resumir el fallo*
   (`flujo`, `paso`, `error`, `cuando`, `ejecucion`); no imprime el `stack`, los parámetros del
   nodo ni los datos de entrada del evento, así que ni secretos ni datos del cliente salen.
