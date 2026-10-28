# Bitácora de IA

> Entregable 8 (US-21, [issue #41](https://github.com/IA-P1-BCN/g1-n8n/issues/41)) · trazabilidad de prompts y decisiones con el agente.
> Convención: cada tarea del nivel Esencial añade una entrada en «Registro por tarea» (prompts textuales cuando la sesión los conservó; marcados *(reconstruido)* cuando se recuperan de issues/PRs) y todo error del agente va a la tabla de errores, con su corrección. Regla de equipo en [`AGENTS.md`](../AGENTS.md) («Trazabilidad»).

## Herramientas y modelos

| Cuándo | Herramienta | Modelo / versión | Para qué |
|---|---|---|---|
| todo el proyecto | OpenCode (CLI de agente de código) | GLM · `glm-5.3-flash-free` (Z.ai) | specs SDD, flujos n8n, PRs, tests e2e, docs |
| desde US-01 | **MCP `n8n-mcp`** (servidor MCP del repo, `.opencode/mcp/`) | n8n-mcp (npm) | docs y versiones de nodos, validación de workflows (`validate_workflow`), templates de referencia |
| desde US-01 | `gh` CLI · Docker CLI · PowerShell · Python 3.14 · Task 3.54.0 | — | issues/PRs, stack local, shell, suites e2e, runner de tests |

No se han usado otros modelos ni generadores de imagen/código n8n comercial.

## Registro por tarea

### US-01 · Flujo 01 · Confirmación de apartado ([#1](https://github.com/IA-P1-BCN/g1-n8n/issues/1), PR #111, 2026-10-22)

- **Prompts** *(reconstruidos a partir de la issue y PR; la sesión original no conservó los prompts textuales)*:
  1. «Crea la spec SDD del Flujo 01 con el vocabulario del GLOSSARY y los dos escenarios de la issue (con correo / sin correo).»
  2. «Construye el sub-workflow según la spec: IF por email y dos correos SMTP; exportalo a `workflows/`.»
  3. «Añade el receptor `POST /webhook/tienda` con Switch por evento y conecta `apartado.creado` al Flujo 01.»
- **Decisiones**: IF por email antes de enviar (Escenario B sin que el flujo falle); SMTP Mailpit con credencial de pruebas; receptor como scaffold del US-17.
- **Resultado**: escenario A importes exactos de la app; B avisa a la tienda — evidencia en PR #111.

### US-02 · Flujo 02 · Recibo de cada abono ([#6](https://github.com/IA-P1-BCN/g1-n8n/issues/6), PR #118, 2026-10-22)

- **Prompts** *(reconstruidos; misma sesión de flujo que US-01 + iteraciones sobre el JSON)*:
  1. «Escribe la spec del Flujo 02: usa los importes del evento tal cual, cubre abono parcial y abono que liquida.»
  2. «Construye el flujo y conecta la rama `abono.registrado` del receptor; revisa los textos con el glosario.»
  3. «Prueba los tres casos en la app (parcial, liquida, sin email) y exporta el JSON.»
- **Errores → correcciones**: ver tabla (E1 · ramas del IF invertidas).
- **Decisiones**: `datos.importe` distingue recibo parcial/final por `datos.estado`; los datos nunca se recalculan en n8n.

### US-05 · Flujo 08 · Aviso de fallo ([#21](https://github.com/IA-P1-BCN/g1-n8n/issues/21), PR #120, 2026-10-26/27)

- **Prompts (texuales de la sesión)**:
  1. *(26/10)* «Tengo que hacer esta tarea dentro del proyecto, con respecto a la PR no la hagas todavía. Hazme saber cuando todo este hecho para yo revisar los flujos uno a uno antes de confirmarla: [US-05 con sus dos escenarios y sus sub-issues #22/#23/#24/#25]»
  2. *(26/10)* «perfecto, haz la PR»
  3. *(26/10)* «haz hecho el subissue de pruebas y evidencias?»
  4. *(27/10)* «sus tareas de evidencia, la #24 debe tener tests que se puedan reproducir y debe guardarse la evidencia del output de cada test»
  5. *(27/10)* «Considera las evidencias como tests, crea una carpeta llamada tests organizado por suites. Modifica el agents.md scorde a este cambio.»
  6. *(27/10)* «Crea un scripts para ejecutar los tests o ya creaste otra cosa para ejecutarlos?»
  7. *(27/10)* «Instala taskfile, y pon una task para los test»
- **Decisiones**:
  - *Aceptar*: `Error Trigger` + aviso construido desde una **lista blanca de 5 campos** (flujo, paso, error, cuándo, enlace) sin stack ni parámetros — cubre el Escenario B sin secretos por diseño.
  - *Aceptar*: apuntar el error workflow vía `settings.errorWorkflow` en cada JSON (sobrevive a cada arranque del `n8n-import`); el Flujo 08 no se apunta a sí mismo.
  - *Rechazar*: configurar el error workflow a mano en la UI (se perdería en cada re-importación) y adjuntar solo capturas como evidencia (Mailpit se vacía — ocurrió).
  - *Aceptar*: señuelos de credenciales (`password`/`apikey`) dentro del evento de prueba para verificar el filtro de secretos.
  - Elección del usuario: suites en Python (stdlib), outputs versionados, Taskfile para orquestar.
- **Resultado**: `tests/us-05/` (13 + 4 PASS), evidencia versionada, `task test` como comando del repo.

### US-22 · Importación manual de flujos + nuevos tasks `install`/`arrancar` ([#44](https://github.com/IA-P1-BCN/g1-n8n/issues/44), PR #124, 2026-10-27/28)

- **Prompts (textuales de la sesión)**:
  1. *(27/10)* «Trabajemos en esta tarea: README con importación de flujos y lista de credenciales — quita el script `n8n-import` del docker-compose y pásalo a scripts/ en Python con su task en Taskfile para importar a voluntad»
  2. *(28/10)* «Prueba delante de mí el import, task importar»
  3. *(28/10)* «Crea un task para arrancar los servicios y un task install que copie el .env y haz PR»
- **Decisiones**:
  - *Aceptar*: importación **manual, a voluntad** (`task importar`) en vez del servicio one-shot `n8n-import` del compose — con `settings.errorWorkflow` ya fijado en los JSON, la re-importación conserva los apuntadores.
  - *Rechazar*: implementación del importador en Node (`.mjs`, propuesta del agente) — el equipo lo quiere en Python como el resto de scripts (solo stdlib).
  - *Aceptar*: el importador orquesta el CLI de n8n en contenedores one-shot al volumen de datos (`import:credentials`, `import:workflow`, `export:workflow`, `publish:workflow`) porque la entrypoint del shell de la imagen no enruta `node` directamente; para/rearranca n8n y sale 1 ante el mínimo fallo.
  - Elección del usuario: tasks `install` (copia `.env.example` → `.env` sin sobreescribir) y `arrancar` (`docker compose up -d`).
- **Errores → correcciones**: ver tabla (E11 · buffered bajo task, E12 · carrera de arranque en frío).
- **Resultado**: `task importar` probado end-to-end (importa 1 credencial + 4 flujos, 4 activados y rearranca); documentación nueva en README (`task install` → `task arrancar` → `task importar`, tabla de flujos y credenciales sin valores); stack sencillo de levantar de cero.



### US-20 · Mapa BPMN del proceso de apartado ([#38](https://github.com/IA-P1-BCN/g1-n8n/issues/38), PR #128, 2026-10-28)

- **Prompts (textuales de la sesión)**:
  1. *(28/10)* «Hagamos esta tarea: Mapa BPMN del proceso de apartado [US-20 #38]»
  2. *(28/10)* «Quiero visualizar los dos diagramas… o dime la ruta exacta para abrirlos en bpmn.io. No modifiques nada ni hagas push»
  3. *(28/10)* «Tenemos un error al intentar abrir los diagramas en bpmn.io: unsupported bpmnElement for BPMNPlane: …»
- **Decisiones**:
  - *Aceptar*: diagramas **BPMN 2.0** ficheros versionados (`proceso-hoy.bpmn`, `proceso-automatizado.bpmn` en `docs/business/mapa-proceso-apartado/`) generados con un script Python (temporal, no versionado) — el criterio pide BPMN/Miro/Excalidraw y así queda editable y exportable.
  - *Aceptar*: automatizado dibujado solo con **lo construido** (Receptor · Webhook tienda, Flujos 01/02/08); las ramas `venta.registrada`/`apartado.vencido` del Switch y los abonos a distancia van como **notas** de pendientes, no como flujos inventados.
- **Errores → correcciones**: ver tabla (E13 · inline de jq, E14 · namespaces y plane del BPMN, E15 · «Switchán»).
- **Resultado**: los dos diagramas abren en bpmn.io y en las vistas locales (bpmn-js); validación con `bpmn-moddle` (0 warnings) e importación del viewer OK.



### Tareas transversales (2026-10-22/28)

- US-17 · Receptor único `Receptor · Webhook tienda` (prompt reconstruido: «un único webhook con Switch por evento») — en PRs #111/#118.
- 28/10 · infra desmonta `n8n-import` (US-22, esta PR): `task install`/`task arrancar`/`task importar` en Taskfile.
- US-16 · CI: validación de JSON de flujos (`scripts/valida_flujos.py` en cada PR) — PR #112.
- Infra · auto-importar/activar `workflows/` y `credentials/` en cada arranque (servicio one-shot `n8n-import`) — PR #115.
- US-19 · contexto de agente: `AGENTS.md` con negocio, URLs, convenciones e import/export — PR #119.
- US-21 · esta bitácora (esta PR).
- Prompts de la sesión de infra (27/10): «Crea un script para ejecutar los tests», «Instala taskfile, y pon una task para los test», «Crea la bitácora IA docs» ([#41](https://github.com/IA-P1-BCN/g1-n8n/issues/41)).

## Errores y alucinaciones del agente (y cómo se corrigieron)

| # | Fecha | Qué pasó | Cómo se detectó | Corrección | Lección |
|---|---|---|---|---|---|
| E1 | 22/10 | Flujo 02: ramas del IF «¿El abono lo liquida?» invertidas (true→parcial, false→recibo final): los escenarios A y B salían «cruzados» | Primera pasada de pruebas con la app | Se corrigieron las conexiones del IF antes de la segunda pasada (PR #118) | Re-importar y probar cada iteración del JSON, no fiarse del editor |
| E2 | 26/10 | Draft de la spec/flujo 08 con frases corruptas en español («nodo Set medicinal», «al-danger») durante la redacción del agente | Lectura propia antes del commit | Ediciones que dejaron el texto limpio | Revisar el texto generado commit a commit: el agente puede solapar ediciones |
| E3 | 26/10 | JSON del webhook escapado a mano en PowerShell → n8n responde 422 «Failed to parse request body» | Respuesta del servidor | Construir el body con `ConvertTo-Json`/ficheros auxiliares | No construir JSON por concatenación en el shell; usar estructuras serializables |
| E4 | 26/10 | Asumido el endpoint Mailpit `DELETE /api/v1/messages/{id}` en la práctica («Method Not Allowed») y campos con mayúscula/mínuscula (`Id` vs `ID`) no identificados | 405 del API y `KeyError` en Python | No hace falta borrar el buzón (los tests filtran por ids nuevos); helper tolerante a `ID`/`Id` | Leer el contrato del API real: PowerShell oculta el case de las claves |
| E5 | 26/10 | `api()` devolvía tupla `(status, cuerpo)` pero se usaba como dict → `AttributeError` | Traceback del test | Devolver el cuerpo ya desempaquetado en `esperar_aviso` | No mezclar la firma de funciones al refactorizar |
| E6 | 26/10 | El test 2 (fallo del Receptor) cogía el aviso del Receptor del test 1 (id nuevo no rastreado en el snapshot) | FAIL con valor de otro test | Re-snapshot de ids de Mailpit antes de cada disparo | Los tests deben aislar su trigger del estado creado por tests previos |
| E7 | 26/10 | UnicodeEncodeError (cp1252) al imprimir el asunto con emoji 🛠 en la consola Windows | Traceback en la 1.ª ejecución | `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` | Windows + consola cp1252: forzar UTF-8 cuando se imprime contenido externo |
| E8 | 27/10 | Typo `linha` (portugués) en el runner antes de ejecutarlo | Revisión propia previa a la 1.ª ejecución | Corregido a `linea` | Ni en código breve: revisar identificadores antes de ejecutar |
| E9 | 27/10 | `Taskfile.yml` no parseaba («mapping values are not allowed») por el `desc` con dos puntos y guiones literales sin citar | `task test` falla al parsear | Citar la descripción | YAML: citar cualquier escalar con `:` interior |
| E10 | 26/10 | `AGENTS.md` decía `docker exec g1-n8n-n8n-1` y el contenedor real es `paso-firme-n8n-1` (el compose se llama así) | «No such container» al exportar el flujo | Se usó el nombre real en toda la sesión; fichero corregido en esta PR | La documentación desactualizada del AGENTS.md guía al error (lo avisa el propio AGENTS.md) |
| E11 | 28/10 | `task importar` colgado sin salida durante minutos: Python `stdout` va buffered en tuberías y el progreso de docker no se veía (el abort del usuario cortó una corrida que funcionaba) | Timeout de 5 min sin output | `python -u scripts/n8n-importar.py` en el task y salida paso a paso (`-u` + `print` con `·`) que ya existía | Con task/pipes, forzar unbuffered (`-u`) o se queda ciego qué está ejecutando |
| E12 | 28/10 | La suite e2e falló justo tras `task importar` (n8n recién rearrancado): el webhook devolvía error de conexión (status 0) durante el arranque de n8n | 2 FAIL — «webhook acepta el evento» y «aviso recibido» | `webhook_datos` reintenta (ventana ~30 s) también ante error de conexión, no solo 404/200 | Tras un rearranque de n8n, espera a que el webhook responda: integrar el warm-up en los tests |
| E13 | 28/10 | Consultas jq con comillas dentro de PowerShell se rompían («accepts 1 arg(s)») al ver sub-issues de la #38 | Fallos y salidas vacías del CLI | Inspeccionar la estructura real del JSON y procesarla con `ConvertFrom-Json` de PowerShell, sin jq | Ante un salido raro de `gh`, inspeccionar el JSON bruto y adaptar el recorrido, no repetir el mismo comando |
| E14 | 28/10 | Los BPMN no abrían en bpmn.io: namespaces `dc`/`di` equivocados (20100923/20100924 en vez de los estándar DD/20100524) y el `BPMNPlane` apuntaba al Participant y no a la Collaboration | «unsupported bpmnElement for BPMNPlane» del usuario |_NS corregidos a `http://www.omg.org/spec/DD/20100524/{DC,DI}` y plane → `collab_*`; validación a nivel moddle (0 warnings) e importación del viewer | Los namespaces DI del BPMN 2.0 son exactos: BPMN/20100524/DI + DD/20100524/{DC,DI}; probar el fichero antes de darlo por bueno |
| E15 | 28/10 | Nota del diagrama automatizado con texto corrupto («El Switchán») y `ConvertTo-Json` envolviendo el XML como objeto en la vista | Capturas del visor (texto y error «required args») | Texto corregido; vista regenerada con `json.dumps` de Python | Volver a pasar captura de pantalla antes de dar un diagrama por versionado |
