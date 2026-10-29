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



### US-20 · Mapa del proceso de apartado ([#38](https://github.com/IA-P1-BCN/g1-n8n/issues/38), PR #128, 2026-10-28)

- **Prompts (textuales de la sesión)**:
  1. *(28/10)* «Hagamos esta tarea: Mapa BPMN del proceso de apartado [US-20 #38]»
  2. *(28/10)* «Quiero visualizar los dos diagramas… o dime la ruta exacta para abrirlos en bpmn.io. No modifiques nada ni hagas push»
  3. *(28/10)* «Tenemos un error al intentar abrir los diagramas en bpmn.io: unsupported bpmnElement for BPMNPlane: …»
  4. *(28/10)* «Haz PR» → PR #128 abierta; commit posterior del nº real en la bitácora
  5. *(28/10)* «Haz pull de la main para traer los cambios» → entran US-17/#125 (receptor sin scaffold + fallback), US-18/#127 (`task demo`); conflicto de `AGENTS.md` resuelto en el PR (merge de main en la rama)
  6. *(28/10)* «Elimina el readme.md … dentro de mapa-proceso-apartado. En el readme.md del proyecto añade solo los links para visualizar los diagramas»
  7. *(28/10)* «Haz los flujos con mermaid, que en readme.md del proyecto esté el link para ver los flujos sin tener que arrastrar ficheros. No los hagas en BPMN. En el readme haz que el título sea legible, haz visibilidad de apartado»
  8. *(29/10)* «clean the readme.md. Make it look polish and more readable.»
- **Decisiones**:
  - *Rechazar* (iteración final del equipo): los `.bpmn` y su «arrastrar a bpmn.io» — se sustituyen por **Mermaid** en `flujos.md`, que GitHub pinta al abrir la página; el README solo enlaza.
  - *Rechazar*: README dedicado del mapa (2.ª iteración) — quedó sustituido por `flujos.md` como única página del mapa.
  - *Aceptar*: el apartado del mapa pasa a **sección propia del README** (`### Mapa del proceso: hoy vs automatizado`, título legible y visible, no una subsección enterrada en los flujos).
  - *Aceptar*: diagramas generados/editables con un script Python (temporal), dibujados solo con **lo construido** (Receptor · Webhook tienda, Flujos 01/02/08); ramas `venta.registrada`/`apartado.vencido` reservadas (04 · US-09, 06 · US-07, sin conectar) y Bizum a mano como notas honestas.
  - *Aceptar*: tras el sync con main, la nota del Switch cita los flujos reservados con su número real (04 · venta, US-09; 06 · vencido, US-07).
  - *Aceptar*: `task importar` tras traer cambios de main cuando toquen `workflows/` — el n8n local seguía con el Receptor viejo y `task test` fallaba de nombre/fallback (carrera de «executions» post-rearranque, un solo rerun y en verde).
  - *Aceptar*: reestructuración y pulido del `README.md` (servicios con Swagger, mapa de proceso con tabla comparativa de valor de negocio, puesta en marcha secuencial en 5 pasos con callouts GitHub, catálogo de flujos, comandos de prueba con flags explícitos e inclusión de `task test`).
- **Errores → correcciones**: ver tabla (E13 · inline de jq, E14 · namespaces y plane del BPMN, E15 · «Switchán»).
- **Resultado**: `README.md` reestructurado y pulido sin pérdida de información; `docs/business/mapa-proceso-apartado/flujos.md` con los 2 bloques Mermaid (validados con `mermaid-cli`: 2/2 renderizan), link desde el README y regla actualizada en AGENTS.md; los `.bpmn` eliminados del repo.


### Dev · `task payload` para probar el receptor con payloads propios (2026-10-28)

- **Prompts (textuales de la sesión)**:
  1. *(28/10)* «puedes crear un comando cli en task para crear payloads a medida para probar el flujo deben leer de fichero el payload»
  2. *(28/10)* «no necesito tests, estos comandos son para pruebas y comprobaciones del developer, pon ejemplos en el readme y documenta»
- **Decisiones**:
  - *Aceptar*: `task payload -- fichero.json` con `scripts/enviar-payload.py` (solo stdlib): lee y **valida** el fichero antes del POST, evitando el JSON inline que se rompe en PowerShell (E3).
  - *Aceptar*: `--esperar` consulta Executions con la clave local del `.env` y muestra la rama del Switch, reutilizando el criterio de US-17; sin `--esperar` no necesita credenciales.
  - *Rechazar*: tests automáticos del comando — es herramienta de desarrollo, no un criterio de aceptación; se verifica a mano en la PR y se documenta en el README.
- **Resultado**: `payloads/` con los 4 eventos, task `payload`, sección «Probar el receptor con un payload propio» en el README y línea en AGENTS.md. Probado con los 4 eventos (con `--esperar`) y los casos de error: fichero inexistente, JSON roto y falta `evento`.
### US-17 · Receptor · Webhook tienda ([#26](https://github.com/IA-P1-BCN/g1-n8n/issues/26), PR #125, 2026-10-27/28)

- **Prompts (textuales de la sesión)**:
  1. *(27/10)* «quiero hacer esta tarea, [US-17 #26]»
  2. *(27/10)* «el flujo 01 y 02 no se toca?»
  3. *(27/10)* «explicame entonces el nuevo workflow que haria?»
  4. *(27/10)* «cual seria el uso de este switch? si no modificamos US-05»
  5. *(27/10)* «ok al plan, us-05 como esta»
- **Decisiones**:
  - *Aceptar*: el receptor **ya existía** (llegó con US-01/US-02); US-17 se cierra con spec, renombrado, fallback y la suite que demuestra las 4 ramas. No se tocan Flujo 01/02.
  - *Aceptar*: la evidencia del reparto se lee de la **API de Executions** de n8n (`runData['Repartir por evento'].data.main`), con la clave local `API_KEY` del `.env`; así las ramas 3/4 (aún sin sub-flujo) también quedan probadas sin inventar correos.
  - *Aceptar*: el Switch sigue leyendo `{{ $json.evento }}` (no `{{ $json.body.evento }}`): `Evento y datos` ya extrae `body`, y su validación es la que provoca el fallo que prueba US-05. La equivalencia queda documentada en la spec.
  - *Aceptar*: `fallbackOutput: "extra"` renombrado «evento desconocido»: un evento no contemplado se ve en la ejecución en vez de descartarse en silencio.
  - *Aceptar*: tests con los payloads que manda la app (no se crean apartados/ventas reales): deterministas, idempotentes y sin ensuciar la base.
  - *Rechazar*: `responseMode: responseNode` para devolver la rama en la respuesta HTTP — cambiaría el comportamiento del webhook y rompería la evidencia de US-05 (body inválido → 200).
- **Errores → correcciones**: ver tabla (E13 · volumen obsoleto del importador, E14 · export con EACCES).
- **Resultado**: `specs/receptor-webhook-tienda.md`, `tests/us-17/` (33 PASS), evidencia versionada en `docs/evidencia/us-17/`, `task test` verde (US-05 incluida), importador arreglado (compose + `--stdout`).

### US-18 · Datos de prueba y script de demo (2026-10-28)

- **Prompts (textuales de la sesión)**:
  1. *(28/10)* «prs mergeadas, ahora necesito hacer esta task https://github.com/IA-P1-BCN/g1-n8n/issues/31»
  2. *(28/10)* «task demo: debe tener un flag para empezar de cero totalmente, limpio; poner en agents un ejemplo de cada flujo, un escenario preparado en task demo (para flujos actuales y añadidos posterior); debe mostrar el resumen en el output de los escenarios para tener una guía rápida; debe poner un ejemplo de ejecución de un custom payload con el task payload»
  3. *(28/10)* «en el taskfile, debes poner si hay flags, siempre documenta nuevos comandos en readme y docs relacionados, añade esta regla a agents.md si no existe»
- **Plan (#32)**: script de host contra la API (no un flujo de n8n: no depende del webhook ni de credenciales SMTP y se repite sin abrir el editor). `task demo` → `scripts/demo.py` (solo stdlib): un apartado liquidado con abono inicial + abonos parciales de varias formas, uno a 5 días de vencer (`fecha`, la del campo de migración) con un abono parcial, uno fuera de plazo vencido con su vale y tres ventas de hoy (efectivo, tarjeta, bizum). Al final **verifica por GET** lo creado (liquidado con 0 pendiente, 3 abonos, vale y ventas de hoy) → exit 0/1.
- **Decisiones**:
  - *Aceptar*: `task demo` como comando de desarrollador, sin tests automáticos (la historia no tiene sub-issue de «Pruebas y evidencia»): la comprobación va dentro del script y la evidencia del run en la PR.
  - *Aceptar*: usar `fecha` para el apartado por vencer y el vencido; así se demuestran los avisos y el vale sin esperar 90 días.
  - *Aceptar*: `--limpio` vacía las tablas con `docker compose exec tienda` (sin reiniciar ni re-sembrar) y el buzón por la API de Mailpit; así no se pierden los flujos de n8n.
  - *Aceptar*: la **guía rápida** la imprime el propio script con los ids reales de la corrida (apartado/venta → flujo → Mailpit), y AGENTS obliga a añadir escenario + payload al crear un flujo.
  - *Rechazar*: crear los datos con un flujo de n8n — mismo resultado con más piezas (webhook, credenciales) y sin ventaja para la demo.
  - *Rechazar*: `docker compose down -v` para limpiar: se lleva por delante n8n y obliga a `task importar`; el flag toca solo los datos de la app y el buzón.
- **Resultado**: `scripts/demo.py`, task `demo`, sección «Datos frescos para la demo» en README (tabla de escenarios), fila en la guía de la app, regla de escenarios y de **comandos/flags documentados** en AGENTS.md y esta entrada. Ejecutado con `--limpio` contra el stack local: apartados #1/#2/#3, ventas #1-#3, vale `VALE-00003`, 6 correos en Mailpit; `exit 0`. Evidencia en la PR.

### US-03 (prep) · Avisos del banco en Mailpit ([#11](https://github.com/IA-P1-BCN/g1-n8n/issues/11), 2026-10-29)

- **Prompts (textuales de la sesión)**:
  1. *(29/10)* «ayudame con esta tarea https://github.com/IA-P1-BCN/g1-n8n/issues/11»
  2. *(29/10)* «antes de decidir, hay que crear unos correos en mailpit con sus respectivos importes y los emisores tienen que ser de bancos ficticios»
- **Plan**: antes de la spec y el flujo del Flujo 03, dejar la entrada lista: los avisos del banco de `data/correos/` cargados en el buzón de Mailpit por un script de host (solo stdlib), reutilizando el patrón de `scripts/demo.py`.
- **Decisiones**:
  - *Aceptar*: repartir los 9 `.eml` entre **tres bancos ficticios** (`Banco Peralta`, `Caja Rivera`, `Banco Castaño`) sobre dominios reservados `.example` (no imitan a ningún banco real); así el remitente del Flujo 03 no queda cableado a uno solo. Importes, ordenantes y conceptos intactos.
  - *Aceptar*: cargar por la API de Mailpit (`POST /api/v1/send`) en vez de SMTP, que no está publicado al host; `task correos` con `--limpio` (vacía el buzón) y `--solo` (prefijos), documentados en README y en el `desc` del task.
  - *Aplazar* (hasta la spec, sub-issue #12): el disparador del flujo (evento + Form Trigger vs IMAP real) y el modelo de IA para extraer ordenante/importe/concepto — se deciden en la spec SDD.
- **Resultado**: `data/correos/*.eml` con remitentes de bancos ficticios, `scripts/correos-banco.py`, task `correos` y sección en README. Cargado por Docker (host sin Python; `python:3.12-alpine` en la red `g1-n8n_default`, `MAILPIT_URL=http://mailpit:8025`): **9/9 correos** en el buzón. Luego, instalado Python en el host (E16) y reejecutado `task correos -- --limpio` de forma nativa: **9/9**.

### US-03 · Spec SDD + Flujo 03 · Abonos a distancia ([#11](https://github.com/IA-P1-BCN/g1-n8n/issues/11), 2026-10-29)

- **Prompts (textuales de la sesión)**:
  1. *(29/10)* «ayudame con esta tarea https://github.com/IA-P1-BCN/g1-n8n/issues/11»
  2. *(29/10)* decisiones elegidas por la tech lead: modelo **Groq** (gratis), disparador **evento `aviso.banco` + Form Trigger**, alcance **spec + flujo + tests** en esta sesión.
- **Decisiones**:
  - *Aceptar*: **la IA solo extrae** `{ordenante, importe, concepto}` (nodo `informationExtractor` + `lmChatGroq`); todas las decisiones (buscar apartado, reglas, registrar) viven en nodos **Code/IF**, no en el prompt.
  - *Aceptar*: entrada doble a la misma lógica — rama `aviso.banco` del receptor único (para tests e2e por HTTP, como US-17) **y** Form Trigger para pegar el aviso en desarrollo; IMAP real documentado para producción.
  - *Aceptar*: búsqueda por API con **comparación normalizada** (sin acentos/mayúsculas, por tokens) porque el banco escribe «CARMEN RUIZ GARCIA» y la app guarda «Carmen Ruiz»; regla de decisión: nº de apartado en el concepto > único candidato activo; 0 / concepto vacío / varios → preguntar a Marisa; `POST …/abonos` con **On Error → Continue** y el 422 (de más / plazo vencido) → avisar con el motivo.
  - *Aceptar*: `forma_pago: "bizum"` también para transferencias — el enum de la app (`efectivo|tarjeta|bizum`) no tiene «transferencia»; limitación anotada en la spec.
  - *Rechazar*: que la IA decida el apartado o el registro (el enunciado lo prohíbe: «la IA solo extrae»); que el flujo mande el recibo (lo manda el Flujo 02 al dispararse `abono.registrado`).
- **Resultado**: `specs/flujo-03-abonos-a-distancia.md`, `workflows/flujo-03-abonos-a-distancia.json` (16 nodos; `valida_flujos` OK), rama `aviso.banco` + `Ejecutar Flujo 03` en el receptor, Mermaid de `flujos.md` y tablas del README actualizados. Credenciales `Groq (abonos a distancia)` y `API tienda (X-API-Key)` creadas en n8n por su API (secretos fuera del repo). **Validado end-to-end** contra el stack. `tests/us-03/` (un script por escenario A–H; cada uno RESETEA la app, crea su fixture por API, dispara el aviso por `aviso.banco` y comprueba executions de n8n + Mailpit + estado del apartado): **43 PASS / 0 FAIL**, evidencia versionada en `docs/evidencia/us-03/`. `task test` entero verde (us-03, us-05, us-17). La rama nueva del receptor obligó a actualizar `tests/us-17/ayudantes.py` (`RAMAS` + `INDICE_FALLBACK` 4 → 5): el contrato del Switch cambió al añadir `aviso.banco`.

### Tareas transversales (2026-10-22/28)

- US-17 · Receptor único `Receptor · Webhook tienda` (prompt reconstruido: «un único webhook con Switch por evento») — scaffold en PRs #111/#118; spec, renombrado, fallback y evidencia en la PR #125.
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
| E13 | 28/10 | `task importar` decía «Successfully imported» pero la instancia seguía con el nombre/opciones viejos: el script montaba el volumen `paso-firme_n8n_data` (nombre del proyecto anterior) mientras el stack usa `g1-n8n_n8n_data` | Comparar la API de n8n después de importar: `versionId` sin cambiar y el Switch sin `fallbackOutput` | El importador usa `docker compose run` del servicio `n8n` (misma imagen y volumen del compose, sin nombres a mano); se quitan `IMAGEN_N8N`/`VOLUMEN_N8N` del Taskfile | Un import que no falla no es un import que aplica: verifica el estado en la instancia, no el exit code |
| E14 | 28/10 | El paso de activación fallaba con `EACCES: permission denied, open '/out/export.json'`: el CLI corre como `node` (uid 1000) y no puede escribir en el `mkdtemp` del host (0700, uid 501); `chmod 777` tampoco basta en macOS | Error del `export:workflow` dentro de `task importar` | Se exporta con `export:workflow --all --stdout` y se captura la salida en Python: sin fichero ni montaje `/out` | Para leer datos de un contenedor, `--stdout` + parseo en el host evita permisos de volúmenes |
| E15 | 28/10 | `scripts/demo.py` calculaba `RAIZ` con `parents[2]` (fuera del repo): no encontraría el `.env` y la clave saldría vacía (`401`) | Revisión del script antes de ejecutarlo | `parents[1]` (la raíz del repo es el padre de `scripts/`) | Ruta de un fichero de `scripts/`: `parents[1]`, no `parents[2]`; revisar antes del primer run |
| E16 | 29/10 | `task correos` (y por igual `demo`/`payload`/`test`) fallaba con «Python was not found... Microsoft Store»: en la máquina `carito` `python`/`py`/`python3` eran stubs de la App Execution Alias, sin Python real | `exit status 49` al lanzar la task; `where.exe python` → solo `WindowsApps\python.exe` de 0 bytes | Instalado Python 3.12 con `winget install Python.Python.3.12 --scope user`; queda delante del stub en el PATH; se carga el buzón por Docker mientras tanto (`python:3.12-alpine` en la red `g1-n8n_default`, `MAILPIT_URL=http://mailpit:8025`) | Las tasks de host necesitan Python real; el stub de la Store intercepta `python` en Windows. Entre contenedores, Mailpit es `mailpit:8025` (no `localhost`) |
| E17 | 29/10 | Flujo 03 fallaba en el nodo Groq: `404 The model llama-3.3-70b-versatile does not exist or you do not have access to it` | Primera ejecución real (status error; saltó el Flujo 08) | Consultado `GET api.groq.com/openai/v1/models` con la clave; la cuenta no tiene Llama de chat, sí `openai/gpt-oss-20b` (tool-calling) → fijado ese modelo y reimportado | No asumir el nombre del modelo del proveedor: listar los modelos disponibles de la cuenta antes de fijarlo en el nodo |
