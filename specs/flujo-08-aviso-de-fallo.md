# Spec SDD · Flujo 08 · Aviso de fallo

> **Historia**: US-05 ([issue #21](https://github.com/IA-P1-BCN/g1-n8n/issues/21)) · **Nivel**: 🟢 Esencial · **Vocabulario**: [`GLOSSARY.md`](../GLOSSARY.md)

## Disparador

**Error Workflow**: se lanza solo cuando falla la ejecución de otro flujo. Nodo *Error Trigger* (`n8n-nodes-base.errorTrigger`); no lo llama el receptor ni ningún otro flujo.

Cada flujo del proyecto (Receptor, Flujos 01, 02 y los que vengan) lo apunta en sus ajustes (`settings.errorWorkflow` = `pFlujo08AvisoFallo`), así que cualquier fallo queda en las **executions** y a la vez dispara este aviso. Este flujo **no** se apunta a sí mismo (un fallo del aviso no puede volver a avisar).

La app no hace nada nuevo: sus eventos ya van al receptor, y si n8n no responde la tienda sigue funcionando (`services/n8n.py`). Quien detecta el fallo es n8n.

## Entradas

n8n entrega al Error Trigger los datos de la ejecución fallida:

- `workflow.name` e `workflow.id`: el flujo que falló.
- `execution.id` y `execution.url`: enlace a la ejecución fallida (fuera de Docker el host es `localhost`).
- `execution.lastNodeExecuted`: el **paso** donde se detuvo.
- `execution.error.message`: el **error** tal cual lo reporta n8n.
- El resto (`stack`, parámetros del nodo, datos de entrada, cabeceras…) queda **fuera**: este flujo solo lee los campos autorizados de la lista de arriba (nodo *Set* con lista blanca).

## Salidas

1. **Aviso a la tienda** (HTML, un correo por fallo):
   - Remitente: `n8n@paso-firme.local`
   - Destinatario: `cambia-esta-direccion@paso-firme.local` (sustituir por el correo real de la tienda al pasar a producción)
   - Asunto: `🛠 Aviso de fallo · <flujo>`
   - Cuerpo: tabla con **flujo**, **paso**, **error**, fecha/hora (Europe/Madrid) y el enlace a la ejecución fallida para abrirla en n8n.
2. Ninguna rama toca la app ni re-envía el evento: el aviso es solo para Marisa y el equipo.

## Casos de error

| Caso | Comportamiento |
|---|---|
| El propio aviso falla (ej. SMTP caído) | El fallo se queda en la lista de **executions** de n8n; no re-dispara este flujo (un Error Workflow no se apunta a sí mismo) |
| Campos ausentes o inesperados del error | El *Set* de lista blanca deja el campo vacío y el aviso sale igual, con lo que haya |
| Fallo apuntado a este flujo | Ninguno: este flujo no tiene `errorWorkflow` apuntado |

## Privacidad (Escenario B)

El aviso se construye **solo** con los cinco campos de la lista blanca (`flujo`, `paso`, `error`, `cuándo`, enlace). No se incluyen: ni **stack** de la excepción, ni parámetros del nodo fallido, ni datos de entrada ni cabeceras — los datos del cliente nunca salen en un aviso de fallo, solo la técnica. El cuerpo no imprime `$json` completo ni `Object.keys()`: campos concretos.

## Criterios de aceptación

Los de la historia (US-05), de ahí a la prueba de usuario:

- **Escenario A — Fallo provocado**: se para la app (o se fuerza un error en un flujo, p. ej. un evento sin `datos` que hace fallar el IF del Flujo 01) y llega el aviso con el **nombre del flujo**, el **paso** (último nodo ejecutado) y el **error**.
- **Escenario B — Sin secretos**: el aviso del escenario A no incluye contraseñas ni claves (ni credenciales ni parámetros del nodo). Evidencia en `docs/evidencia/us-05-avisos-errores.md`.

## Notas de arquitectura

- El JSON fija `settings.errorWorkflow` también en el **Receptor** y en los flujos 01 y 02, así el apuntador sobrevive a cada re-importación del `n8n-import` (los documentos importan por `id` y actualizan sus ajustes).
- **Envío de correo**: nodo *Send Email* (SMTP) con la credencial `SMTP Mailpit (pruebas)` → durante el desarrollo los avisos se ven en el buzón de pruebas Mailpit (http://localhost:8025). Para producción basta asignar una credencial SMTP real (u OAuth2 de Gmail) con los mismos campos.
- Al ser el flujo de fallo **trasversal**, se numera aparte de los flujos de evento (08 en adelante): no entra en el reparto del receptor.
