# Spec SDD · Flujo 09 · Migración del Excel

> **Historia**: US-10 ([issue #67](https://github.com/IA-P1-BCN/g1-n8n/issues/67)) · **Nivel**: 🟡 Medio · **Vocabulario**: [`GLOSSARY.md`](../GLOSSARY.md)

## Disparador

**Manual Trigger** (`Al ejecutar manualmente`, `n8n-nodes-base.manualTrigger`): es una operación puntual de carga histórica que lanza Marisa o el equipo desde el editor de n8n (o por CLI con `n8n execute --id=<ID>`). No expone ningún webhook para evitar una superficie de escritura innecesaria.

## Entradas

Dos ficheros CSV montados en solo lectura dentro del contenedor de n8n (`/data-fuentes/`, desde `./data` del repositorio):

1. `/data-fuentes/excel_actual_apartados.csv` (`fecha,cliente,telefono,modelo,talla,precio,abono,resta,notas`):
   - Mezcla la apertura de cada **apartado** (con su **abono inicial**) y los **abonos** posteriores en la misma hoja.
   - Trae fechas en formatos `DD/MM/AAAA` (`02/09/2026`) y `D/M/AA` (`7/9/26`), nombres con mayúsculas inconsistentes (`Carmen Ruiz` / `carmen ruiz`), importes con símbolo `€` (`15€`) y teléfonos vacíos o con/sin espacios.
2. `/data-fuentes/excel_actual_ventas.csv` (`fecha,concepto,importe,forma_pago`):
   - Mezcla **ventas** de mostrador, apuntes de abonos de apartados (`abono inicial apartado`, `Abono Ana Torres mocasin`, `(apartado)`) y una fila final de suma manual (`TOTAL SEPTIEMBRE (a mano)`).

Además, el flujo consulta el estado actual de la app mediante la API REST (`http://tienda:8000/api/...`, autenticada con la cabecera `X-API-Key`):
- `GET /api/apartados`
- `GET /api/abonos`
- `GET /api/ventas`

## Reglas de limpieza, agrupación e idempotencia

1. **Normalización de campos**:
   - **Fechas**: `D/M/AA` o `DD/MM/AAAA` → ISO `AAAA-MM-DD` (años de 2 cifras `26` → `2026`). Si una fila no tiene fecha válida (como `TOTAL SEPTIEMBRE (a mano)`), no se migra como venta.
   - **Importes**: se quita `€` y espacios, convirtiendo coma decimal a punto si existiera → número (`float`).
   - **Cliente**: limpieza de espacios y normalización a *Title Case* conservando tildes (`carmen ruiz` → `Carmen Ruiz`) para agrupar sin duplicar personas.
   - **Teléfono**: limpieza de espacios extremos (`null` si está vacío).
   - **Forma de pago**: si la hoja de ventas registra la forma de pago de un abono o apartado de la misma fecha/importe (p. ej. `bizum` en el apartado de Sofía Navarro del `06/10/2026`), se conserva; por defecto `efectivo`.
2. **Agrupación de apartados y abonos** (por `cliente` normalizado + `modelo` + `talla`):
   - Las filas del grupo se ordenan cronológicamente.
   - La **primera fila** del grupo define el **apartado** (`precio`, `abono_inicial` = columna `abono`, `fecha` original).
   - Si el **abono inicial** es menor de **5 €** (regla de negocio de [`docs/business/business-rules.md`](../docs/business/business-rules.md)), el apartado **se rechaza como caso dudoso** y tampoco se cargan los abonos posteriores de ese mismo grupo: todo el grupo pasa al informe para que Marisa decida.
   - Las **filas siguientes** del grupo (`notas` con `abono` o liquidación) son **abonos** posteriores (`importe` = columna `abono`, `fecha` original) sobre el apartado creado.
3. **Filtrado de la hoja de ventas**:
   - Se excluyen las filas sin fecha válida (`TOTAL SEPTIEMBRE (a mano)`).
   - Se excluyen los apuntes cuyo `concepto` corresponde a un **abono** o **apartado** (contiene `abono` o `apartado`), porque en la app los abonos ya se registran en su apartado y cuentan automáticamente en las **ventas del día**.
4. **Idempotencia (ejecutar dos veces no duplica datos)**:
   - Un **apartado** se considera ya migrado si en `GET /api/apartados` existe uno con el mismo `(cliente normalizado, producto normalizado, talla, fecha)`. Si ya existe, se reutiliza su `id` sin llamar a `POST /api/apartados`.
   - Un **abono** posterior se considera ya migrado si en `GET /api/abonos` existe un abono para ese `apartado_id` con la misma `(fecha, importe)` (descontando el abono inicial cuando comparte fecha e importe).
   - Una **venta** se considera ya migrada si en `GET /api/ventas` existe una con la misma `(fecha, concepto normalizado, importe)`.

## Salidas

1. **Carga en la app por API** (conservando la `fecha` original en cada `POST`):
   - `POST /api/apartados` → con los datos actuales de `data/`, crea **7 apartados** (`Carmen Ruiz`, `Jorge Martín`, `Ana Torres`, `Pedro Sanz`, `Rosa Díaz`, `Miguel Ángel López` y `Sofía Navarro`).
   - `POST /api/apartados/{id}/abonos` → crea **3 abonos posteriores** (`Carmen Ruiz` 20 € el `2026-09-05`, `Jorge Martín` 30 € el `2026-09-12`, `Ana Torres` 20 € el `2026-10-03`).
   - `POST /api/ventas` → crea **6 ventas** (`Calcetines pack 3`, `Bota montaña T41`, `Plantillas gel`, `Zapatilla casa T38`, `Botín piel negro T40` y `Crema calzado`).
2. **Informe de migración y casos dudosos a Marisa** (correo HTML por SMTP con la credencial `SMTP Mailpit (pruebas)`):
   - Remitente: `n8n@paso-firme.local`
   - Destinatario: `cambia-esta-direccion@paso-firme.local`
   - Asunto: `📋 Informe de migración del Excel · casos dudosos para revisar`
   - Cuerpo: resumen de registros migrados/omitidos por idempotencia y tabla detallada de **casos dudosos no cargados** para que Marisa decida (incluyendo a **Lucía Gómez**, `Sandalia tacón negra` T37 del `03/09/2026` con abono inicial de `4 € < 5 €` y su liquidación asociada de `41 €` del `20/09/2026`, además de las filas descartadas de la hoja de ventas).

## Casos de error

| Caso | Comportamiento |
|---|---|
| Abono inicial `< 5 €` o fila dependiente de un apartado dudoso | **No se carga en la app**; el flujo no falla y lo incluye en el informe de casos dudosos para Marisa |
| Fila de suma manual o sin fecha (`TOTAL SEPTIEMBRE (a mano)`) | Se descarta de las ventas y se documenta en el resumen/informe sin detener el flujo |
| Re-ejecución del flujo con datos ya cargados | Los registros existentes se detectan por API y se omiten (`0` duplicados); el informe se envía igualmente |
| Fichero CSV ausente o API de la tienda caída / `401` | El nodo falla y detiene la ejecución → la captura el **Flujo 08 · Aviso de fallo** (`settings.errorWorkflow`) |

## Criterios de aceptación

Los de la historia ([issue #67](https://github.com/IA-P1-BCN/g1-n8n/issues/67)), verificados automáticamente por `tests/us-10/` y su evidencia en `docs/evidencia/us-10/`:

- **Escenario A — Carga limpia** (`escenario-a-carga-limpia.py`): tras ejecutar el flujo con los CSV de `data/`, la API devuelve los 7 apartados, sus 3 abonos posteriores y las 6 ventas con sus fechas originales (`2026-09-02`, `2026-09-07`, etc.), nombres normalizados (`Carmen Ruiz`) e importes numéricos limpios (`15.0` sin `€`), sin duplicar como ventas los apuntes de abonos.
- **Escenario B — Sin duplicados** (`escenario-b-sin-duplicados.py`): al volver a ejecutar el flujo completo, el número de apartados, abonos y ventas en la API no cambia (`0` duplicados).
- **Escenario C — Casos dudosos** (`escenario-c-casos-dudosos.py`): el caso dudoso de **Lucía Gómez** (abono inicial de `4 €` menor del mínimo de `5 €` y su fila posterior de `41 €`) **no** aparece en `GET /api/apartados` y **sí** aparece listado con el motivo en el correo de informe enviado a Marisa en Mailpit.

## Notas de arquitectura

- **Montaje de datos en solo lectura**: `docker-compose.yml` monta `./data:/data-fuentes:ro` en el servicio `n8n`, de modo que el flujo lee los CSV reales del repositorio sin incrustarlos en el JSON.
- **Autenticación con la API de la tienda**: la variable `API_KEY` del `.env` se pasa al contenedor `n8n` en `docker-compose.yml` para que el flujo autentique sus peticiones a `http://tienda:8000` sin escribir ninguna clave en el JSON del workflow ni en el repositorio.
- **Manejo de errores transversal**: `settings.errorWorkflow = pFlujo08AvisoFallo` conecta cualquier fallo inesperado con el Flujo 08 (US-05).
