# Evidencia · US-05 Avisos de errores (Flujo 08 · Aviso de fallo)

> Historia: US-05 (issue #21) · última ejecución: 27/10/2026 · stack local: tienda + n8n + Mailpit

## Preparación

- Flujo 08 importado y **activo** en n8n (`workflows/flujo-08-aviso-de-fallo.json`), con nodo *Error Trigger*.
- Receptor y Flujos 01/02 apuntan a él vía `settings.errorWorkflow = pFlujo08AvisoFallo` (export de n8n):

| Flujo | id | active | errorWorkflow |
|---|---|---|---|
| Flujo 01 · Confirmación de apartado | `pwLRoxMrKVfAR2XK` | true | `pFlujo08AvisoFallo` |
| Receptor · Webhook tienda | `HXZBeAF7TZrK4zfD` | true | `pFlujo08AvisoFallo` |
| Flujo 02 · Recibo de cada abono | `pFlujo02ReciboAbono` | true | `pFlujo08AvisoFallo` |
| Flujo 08 · Aviso de fallo | `pFlujo08AvisoFallo` | true | — (no se apunta a sí mismo) |

## Pruebas reproducibles ✅

El script e2e **`scripts/us-05-pruebas-evidencia.py`** (solo stdlib) reproduce los escenarios de
aceptación contra el stack local (solo necesita n8n + mailpit arriba):

```bash
python scripts/us-05-pruebas-evidencia.py        # exit code 1 si algún criterio falla
# N8N_URL / MAILPIT_URL sobreescriben http://localhost:5678 y http://localhost:8025
```

Resultado de la última ejecución (re-ejecutable, idempotente): **14 PASS / 0 FAIL**.

- **Test 1 · Escenario A + B** — `apartado.creado` con `datos.email = "nadie"` y señuelos
  `password`/`apikey` → aviso en Mailpit con flujo (`Flujo 01 · Confirmación de apartado`),
  paso (`Enviar resumen al cliente`), error (`No recipients defined`) y enlace a la ejecución;
  más el aviso del Receptor (paso `Ejecutar Flujo 01`). Los señuelos **no** aparecen en el aviso
  (Text/HTML: `false`).
- **Test 2 · Escenario A (Receptor)** — webhook con body `[1,2,3]` → aviso con flujo
  `Receptor · Webhook tienda`, paso `Evento y datos` y error
  `The 'JSON Output' in item 0 does not contain a valid JSON object`.

Evidencia del output de cada test, versionada en `docs/evidencia/us-05/`:

| Fichero | Contenido |
|---|---|
| `resumen.txt` | Resultado PASS/FAIL de cada criterio y total |
| `fallo-flujo-01-payload.json` | Evento enviado (con los señuelos) |
| `fallo-flujo-01-webhook.json` | Respuesta del webhook de n8n |
| `fallo-flujo-01-aviso.json` | Aviso completo recibido (Mailpit: asunto, Text, HTML) |
| `fallo-flujo-01-receptor-aviso.json` | Aviso del Receptor (padre) |
| `fallo-receptor-payload.txt` / `fallo-receptor-webhook.json` | Body inválido y respuesta |
| `fallo-receptor-aviso.json` | Aviso del fallo en el Receptor |
| `busqueda-secretos.txt` | Resultado de buscar los señuelos en Text/HTML: `false` |

## Primera ejecución (manual, 26/10/2026)

Mismas provocaciones hechas a mano con curl; los avisos quedaron en Mailpit esa tarde
(p. ej. id `4S5Wwz84ldq1zNPzYgYCow`, paso `Enviar resumen al cliente`, error `No recipients defined`,
y body `[1,2,3]` → id `5krAfyLh0w4sNQ5VOUNImo`, paso `Evento y datos`). Mailpit se ha vaciado
desde entonces: la evidencia conservada es la versionada arriba, reproducible con el script.
