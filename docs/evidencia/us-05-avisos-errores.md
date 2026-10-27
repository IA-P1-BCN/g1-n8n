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

## Pruebas (suites en `tests/us-05/`) ✅

La suite de la historia da vida a los escenarios de aceptación contra el stack local
(solo necesita n8n + mailpit arriba), un test por escenario:

```bash
python tests/us-05/escenario-a-fallo-provocado.py   # Escenario A: fallo provocado → aviso con flujo, paso y error
python tests/us-05/escenario-b-sin-secretos.py      # Escenario B: el aviso no incluye contraseñas ni claves
# N8N_URL / MAILPIT_URL sobreescriben http://localhost:5678 y http://localhost:8025
```

`ayudantes.py` concentra los helpers (API de Mailpit y n8n, extracción de los campos del aviso, escritura de la evidencia) para que cada test sea independiente: registra los ids ya presentes en Mailpit, dispara su propio fallo y espera su aviso — las suites son re-ejecutables (idempotentes).

Resultado de la última ejecución: **13 PASS / 0 FAIL** (Escenario A) y **4 PASS / 0 FAIL** (Escenario B).

- **Escenario A** — `apartado.creado` con `datos.email = "nadie"` → aviso con flujo
  (`Flujo 01 · Confirmación de apartado`), paso (`Enviar resumen al cliente`), error
  (`No recipients defined`) y enlace a la ejecución; más el aviso del Receptor (paso
  `Ejecutar Flujo 01`). Y webhook con body `[1,2,3]` → aviso con paso `Evento y datos`
  y error `The 'JSON Output' in item 0 does not contain a valid JSON object`.
- **Escenario B** — el evento lleva señuelos `password`/`apikey`; el aviso **no** los
  contiene (Text/HTML: `false`), solo los cinco campos de la lista blanca.

Evidencia del output de cada test, versionada en `docs/evidencia/us-05/`:

| Fichero | Contenido |
|---|---|
| `resumen-escenario-a.txt`, `resumen-escenario-b.txt` | Resultado PASS/FAIL de cada criterio y total por suite |
| `escenario-a-fallo-flujo-01-payload.json`, `-webhook.json`, `-aviso.json` | Evento, respuesta del webhook y aviso completo (Mailpit) |
| `escenario-a-fallo-flujo-01-receptor-aviso.json` | Aviso del Receptor (falla del sub-flujo y del padre) |
| `escenario-a-fallo-receptor-payload.txt`, `-webhook.json`, `-aviso.json` | Fallo en el Receptor (body inválido) |
| `escenario-b-sin-secretos-payload.json`, `-webhook.json`, `-aviso.json` | Evento con señuelos y aviso |
| `escenario-b-busqueda-secretos.txt` | Búsqueda de los señuelos en Text/HTML: `false` |

## Primera ejecución (manual, 26/10/2026)

Mismas provocaciones hechas a mano con curl; los avisos quedaron en Mailpit esa tarde
(p. ej. id `4S5Wwz84ldq1zNPzYgYCow`, paso `Enviar resumen al cliente`, error `No recipients defined`,
y body `[1,2,3]` → id `5krAfyLh0w4sNQ5VOUNImo`, paso `Evento y datos`). Mailpit se ha vaciado
desde entonces: la evidencia conservada es la versionada arriba, reproducible con el script.
