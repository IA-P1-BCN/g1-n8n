# Spec SDD · Receptor · Webhook tienda

> **Historia**: US-17 ([issue #26](https://github.com/IA-P1-BCN/g1-n8n/issues/26)) · **Nivel**: 🟢 Esencial · **Vocabulario**: [`GLOSSARY.md`](../GLOSSARY.md)
>
> Infraestructura compartida por los flujos 01, 02, 04 y 06: un único webhook publicado reparte los eventos de la app con un Switch, para no duplicar receptores y poder añadir flujos sin tocar la app.

## Disparador

`POST /webhook/tienda`, la **Production URL** del flujo (activo y publicado):

- desde la app: `http://n8n:5678/webhook/tienda` (variable `N8N_WEBHOOK_URL` del `.env`; la app llama desde la red de Docker);
- desde el host o Swagger: `http://localhost:5678/webhook/tienda`.

Responde **en el acto** (`responseMode: onReceived`) con `{"message":"Workflow was started"}`: la Dependienta no espera a que se envíen los correos. Si n8n no responde, la app registra un aviso y sigue funcionando (`services/n8n.py`).

Es la **única puerta de entrada** de los eventos de la tienda: un flujo nuevo se engancha a una salida del Switch, no a un webhook nuevo.

## Entradas

Cuerpo JSON que envía la app: `{ "evento": "…", "datos": { … } }`. El nodo `Evento y datos` extrae `body` (`={{ $json.body }}`), así que el Switch y los sub-flujos trabajan con un item limpio `{ evento, datos }` (sin cabeceras ni metadatos del webhook).

| `evento` | Cuándo lo emite la app | `datos` |
|---|---|---|
| `apartado.creado` | `POST /api/apartados` | `id`, `fecha`, `cliente`, `telefono`, `email`, `producto`, `talla`, `precio`, `abonado`, `pendiente`, `fecha_limite`, `estado` |
| `abono.registrado` | `POST /api/apartados/{id}/abonos` | los del apartado **ya actualizado** + `importe` de este abono |
| `venta.registrada` | `POST /api/ventas` | `id`, `fecha`, `concepto`, `importe`, `forma_pago` |
| `apartado.vencido` | `POST /api/apartados/{id}/vencer` | `apartado` (con `estado: vencido`) y `vale` (`codigo`, `apartado_id`, `fecha`, `importe`) |

El receptor **no valida reglas del negocio ni toca la app**: solo enruta el payload tal cual.

## Salidas

El Switch `Repartir por evento` compara `{{ $json.evento }}` con una regla por evento y renombra cada salida con el nombre del evento:

| Salida | Destino | Estado |
|---|---|---|
| `apartado.creado` | `Ejecutar Flujo 01` · Confirmación de apartado | conectada |
| `abono.registrado` | `Ejecutar Flujo 02` · Recibo de cada abono | conectada |
| `venta.registrada` | `Ejecutar Flujo 04` · Aviso de ventas grandes | conectada |
| `apartado.vencido` | — | reservada para el Flujo 06 (US-07) |
| `evento desconocido` (fallback) | — | el evento no se pierde: queda visible en la ejecución |

Cada rama entrega al sub-flujo el item `{ evento, datos }`. Una ejecución del receptor termina en `success` con `lastNodeExecuted = Repartir por evento` cuando la rama no tiene destino todavía.

## Casos de error

| Caso | Comportamiento |
|---|---|
| Body sin objeto JSON (`[1,2,3]`, texto…) | `Evento y datos` falla → ejecución del receptor en error → aviso del Flujo 08 (probado en US-05) |
| `evento` desconocido o vacío | No casa con ninguna regla → salida `evento desconocido`; la ejecución termina bien y el evento queda en Executions |
| Fallo del sub-flujo | El padre y el hijo fallan → Flujo 08 avisa del flujo y del paso |
| n8n caído | La app no espera: registra «No se pudo avisar a n8n» y sigue (ningún evento bloquea una venta) |
| Evento repetido | No hay deduplicación: el receptor enruta cada POST (idempotencia es responsabilidad de cada flujo) |

## Criterios de aceptación

Los de la historia (issue #26), verificados por `tests/us-17/` y su evidencia en `docs/evidencia/us-17/`:

1. **Publicación** — el flujo está activo y atiende su Production URL `/webhook/tienda` (y no el webhook de pruebas): `escenario-a-publicacion.py`.
2. **`apartado.creado`** — el Switch lo manda a su rama y esa rama ejecuta el Flujo 01: `escenario-b-apartado-creado.py`.
3. **`abono.registrado`** — su rama, que ejecuta el Flujo 02: `escenario-c-abono-registrado.py`. El evento se lee del cuerpo (`$json.body.evento`, normalizado a `$json.evento` por `Evento y datos`).
4. **`venta.registrada`** — su rama, que ejecuta el Flujo 04 (US-09): `escenario-d-venta-registrada.py`.
5. **`apartado.vencido`** — su rama (sin destino aún): `escenario-e-apartado-vencido.py`.

La evidencia se lee en **Executions** (`GET /api/v1/executions/{id}`): el Switch guarda sus items por salida, así que el test comprueba que solo la rama esperada lleva el evento.

## Notas de arquitectura

- **Un receptor, N flujos**: la app solo conoce una URL; añadir un flujo = conectar una salida del Switch a un `Ejecutar Flujo NN`. Sin cambios en la app ni en el resto de flujos.
- **Por qué hay un nodo Set antes del Switch**: normaliza el webhook a `{ evento, datos }` (los sub-flujos solo ven el dominio) y es además la validación que convierte un body inválido en el fallo que prueba US-05. Por eso el Switch compara `{{ $json.evento }}` —la lectura de `body.evento` ya hecha— en lugar de repetir `{{ $json.body.evento }}`.
- **Fallback nombrado**: un evento que no case no se descarta en silencio; aparece en la salida `evento desconocido` de la ejecución.
- **Aislamiento de fallos**: cada rama es un sub-flujo; si uno falla, el resto de eventos siguen repartiéndose igual.
- **Errores**: `settings.errorWorkflow = Flujo 08 · Aviso de fallo` en el receptor y en cada sub-flujo.
- **Sin credenciales ni llamadas a la app**: el receptor solo enruta; los correos y las consultas viven en los sub-flujos.
