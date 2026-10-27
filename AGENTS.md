# AGENTS.md

## Agent skills

### Issue tracker

GitHub Issues on a Projects board — milestones as epics, stories as issues, tech tasks as sub-issues. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: `GLOSSARY.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.


REGLAS GENERALES
- protege la rama main, pr con 1 review
- usa conventional commit y conventional branches
- usa TDD

## Reglas del negocio y datos
- Reglas del sistema de apartado (abono inicial mín. 5 €, plazo 90 días, estados activo/liquidado/vencido, vale…): `docs/business/business-rules.md`
- Datos de partida (Excel actual y avisos del banco de `data/correos/`): `docs/business/business-data.md`

## Pruebas de aceptación (sub-issues "Pruebas y evidencia")
- La evidencia **son tests**: cada historia lleva una suite e2e en `tests/us-NN/` con un script por escenario de aceptación (solo stdlib); los helpers compartidos viven en `tests/us-NN/ayudantes.py`.
- Cada test ejecuta los escenarios contra el stack local (n8n/app/mailpit por HTTP localhost, URLs sobre-escribibles por env, sin credenciales) y termina con exit code.
- **Comando de referencia:** `task test` (todas las suites; una sola: `task test -- us-NN`), vía Taskfile.yml y `scripts/ejecutar-tests.py`.
- El **output de cada test** (payload, respuesta, avisos/mensajes capturados y resultado de cada criterio) se versiona en `docs/evidencia/us-NN/` y se lista en `resumen-escenario-*.txt`; la evidencia solo-manual (curl o capturas) no vale: el buzón de Mailpit se vacía y las ejecuciones de n8n se pierden.
- El sub-issue de pruebas considera "hecho" cuando el `task test` pasa (todas las suites de la historia) y los outputs versionados están en la PR.

## URLs
| Servicio | URL | Para qué |
|---|---|---|
| App de la tienda | http://localhost:8000 | Registrar apartados, abonos y ventas, y descargar todo en **Excel** |
| Documentación de la API | http://localhost:8000/docs | Probar los endpoints que usará n8n (Swagger) |
| n8n | http://localhost:5678 | Construir las automatizaciones |
| mailpit | http://localhost:8025 | Gestor de correos |

## IA Agents
Usamos agente Opencode y MCP n8n-mcp. Trazabilidad de prompts, decisiones y errores del agente: `docs/ai-log.md` (una entrada por tarea; todo error detectado se registra con su corrección).

## Convenciones de nombres
| Artefacto | Convención | Ejemplo |
|---|---|---|
| Flujo (workflow en n8n) | `Flujo NN · Nombre` | `Flujo 02 · Recibo de cada abono` |
| Fichero del flujo | `workflows/flujo-nn-nombre.json` (kebab-case) | `flujo-02-recibo-de-cada-abono.json` |
| Spec SDD | `specs/flujo-nn-nombre.md` | `specs/flujo-02-recibo-de-cada-abono.md` |
| Suite de pruebas | `tests/us-nn/` (una por historia, un script por escenario) | `tests/us-02/` |
| Evidencia | `docs/evidencia/us-nn/resumen-escenario-*.txt` | `docs/evidencia/us-05/resumen-escenario-a.txt` |
| Rama | conventional: `feat\|docs\|test/us-nn-tarea` (kebab-case) | `feat/us-02-recibo-abono` |
| Commit | conventional: `feat\|docs\|fix\|test(us-NN): …` | `feat(us-02): recibo de cada abono` |
| Nodos | en español, descriptivos; pregunta si es IF/Switch | `¿El cliente tiene email?`, `Repartir por evento` |
| Receptor y sub-flujos | receptor único `Receptor · Webhook tienda`; un sub-workflow por evento | nodo `Ejecutar Flujo 02` |

## Importar / exportar flujos
- **Importar:** manual, a voluntad — `task importar` (`scripts/n8n-importar.py`, Python: para n8n, sube `credentials/` y `workflows/` al CLI de n8n en contenedores one-shot con el volumen de datos, activa los flujos y lo rearranca). Lánzalo al levantar el stack por primera vez y tras editar cualquier JSON.
- **Exportar:** desde el editor de n8n (Download) o CLI al fichero exacto de `workflows/`:
  `docker exec paso-firme-n8n-1 n8n export:workflow --id=<ID> --stdout > workflows/flujo-nn-nombre.json`
- **Credenciales:** en el JSON solo se referencian por id/nombre; los valores van en `credentials/` (n8n las cifra al subirlas), nunca en claro dentro del workflow.
- **Vocabulario:** los nombres de flujos, nodos y mensajes usan el de `GLOSSARY.md` (Abono, Pendiente, Liquidado, Vale…).
- **Probar a mano:** `task payload -- payloads/venta-registrada.json` envía el payload de un fichero al receptor (evita JSON inline en el shell); con `--esperar` muestra la ejecución y la rama del Switch. Ejemplos en `payloads/`.

## Forma de trabajo
1. **Contexto antes que flujos:** crear un `AGENTS.md` en la raíz con el negocio y sus reglas del apartado, los servicios integrados, las convenciones de nombres de flujos y nodos, cómo importar y exportar flujos.
2. **SDD & Ontologías:** antes de pedirle nada al agente, cada automatización se define con *Spec-Driven Development* en una spec (`specs/`) con el disparador, las entradas, las salidas, los casos de error y los criterios de aceptación, apoyada en una ontología del dominio: entidades del negocio (`Cliente`, `Producto`, `Apartado`, `Abono`, `Venta`, `CierreDiario`…), sus atributos, relaciones y reglas. Así el agente y el equipo comparten el mismo vocabulario y no inventan conceptos.
3. **Tareas pequeñas:** en pareja, repartid los flujos para no pisaros; una tarea del Kanban equivale a un flujo (o parte de uno), una rama y una Pull Request con el JSON exportado.
4. **Revisión humana obligatoria:** todo flujo generado se importa, se prueba con datos de ejemplo y se revisa en la PR antes de mergear. Hay que prestar especial atención a la seguridad: credenciales, datos personales y webhooks expuestos.
5. **Pruebas como contrato:** cada flujo tiene datos de prueba (pinned data o payloads de ejemplo) y un resultado esperado. Si una prueba falla, se arregla el flujo, no se cambia la prueba.
6. **Trazabilidad:** registrar los prompts más relevantes y las decisiones que se tomaron (qué se aceptó, qué se rechazó y por qué).

## Cosas que no debe hacer el agente IA
- no escribir credenciales en el JSON.
- no activar flujos en producción.
- No dejes instrucciones obsoletas: La información desactualizada en un AGENTS.md es peor que no tener archivo. Si cambias comandos de compilación o tests y no actualizas el archivo, estarás guiando al agente al error.
- No sobrecargues el archivo con exceso de líneas (evita el "bloat"): Mantén la extensión reducida (idealmente por debajo de las 200 líneas o centrado en 20-30 líneas esenciales). No metas políticas de seguridad globales, historia arquitectónica completa o notas de incorporación que no tengan que ver con la tarea inmediata
