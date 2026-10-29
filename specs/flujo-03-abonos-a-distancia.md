# Spec SDD · Flujo 03 · Abonos a distancia (Bizum o transferencia)

> **Historia**: US-03 ([issue #11](https://github.com/IA-P1-BCN/g1-n8n/issues/11)) · **Nivel**: 🟢 Esencial · **Vocabulario**: [`GLOSSARY.md`](../GLOSSARY.md)
>
> Marisa recibe avisos del banco cuando un cliente paga por **Bizum** o **transferencia**. Este flujo lee el aviso, **la IA solo extrae** ordenante, importe y concepto, y **las decisiones las toma el flujo con la API**: a qué apartado va, si se puede registrar o si hay que preguntar a Marisa. El **recibo al cliente lo manda el Flujo 02** de forma automática (al registrar el abono, la app emite `abono.registrado`).

## Ontología (entidades que toca el flujo)

| Entidad | Atributos usados | De dónde sale |
|---|---|---|
| **AvisoBanco** | `asunto`, `cuerpo` | el correo del banco (entrada del flujo) |
| **PagoExtraído** | `ordenante`, `importe` (€), `concepto` | lo que **extrae la IA** del aviso (nada más) |
| **Apartado** | `id`, `cliente`, `estado`, `pendiente`, `fecha_limite`, `email` | API de la app (`GET /api/apartados`) |
| **Abono** | `importe`, `forma_pago` | lo que **registra el flujo** (`POST …/abonos`) |

La IA no decide ni inventa apartados: convierte texto libre del banco en los tres campos de `PagoExtraído`. Todo lo demás (buscar, validar reglas, registrar) es del flujo contra la API.

## Disparador

Dos entradas que alimentan la **misma lógica**, para desarrollo y para pruebas, sin depender de un correo real:

1. **Receptor único** — nueva rama `aviso.banco` del Switch de [`Receptor · Webhook tienda`](receptor-webhook-tienda.md) → `Ejecutar Flujo 03`. Es la puerta que usan las **pruebas e2e** (POST por HTTP, igual que US-17) y por la que un *Email Trigger* IMAP entregaría el aviso en producción:

   ```json
   { "evento": "aviso.banco", "datos": { "asunto": "Has recibido un Bizum de 10,00 €", "cuerpo": "…Importe: 10,00 EUR\nOrdenante: CARMEN RUIZ GARCIA\nConcepto: zuecos…" } }
   ```

2. **Form Trigger** (desarrollo) — formulario de n8n con dos campos (`asunto`, `cuerpo`) para **pegar** el aviso a mano mientras se desarrolla (criterio del enunciado: «pegar el texto en un Form Trigger para no depender del correo»).

> **Producción**: se añade un *Email Trigger (IMAP)* sobre la cuenta real de Marisa que normaliza el correo a `{asunto, cuerpo}` y entra por la misma lógica. No se incluye en esta historia (requiere cuenta y credencial reales); queda documentado aquí.

## Entradas

- `asunto`, `cuerpo`: el texto del aviso del banco, tal cual llega.
- **IA (extracción, Groq)**: a partir de `cuerpo`+`asunto` devuelve `{ ordenante, importe, concepto }`. `importe` numérico en euros; `concepto` cadena vacía si el aviso no lo trae.
- **API de la app** (cabecera `X-API-Key`, credencial de n8n): fuente de verdad de los apartados y única vía para registrar el abono.

## Decisiones del flujo (no de la IA)

Orden de decisión, con el correo de `data/correos/` que cubre cada rama:

1. **¿Es un pago?** Si el aviso **no** tiene línea `Importe … EUR` → **se ignora** (ni registro ni pregunta). → `08_publicidad_banco`.
2. **Extracción IA** de `{ordenante, importe, concepto}`.
3. **¿El concepto trae nº de apartado?** (`apartado N`) → se usa ese apartado directamente (`GET /api/apartados/{N}`). → `02_bizum_jorge` («apartado 2 bota»).
4. **Sin nº explícito → buscar por ordenante** entre los apartados **activos** (`GET /api/apartados?estado=activo`), con comparación **normalizada** (sin acentos ni mayúsculas, por tokens de nombre/apellido; el aviso viene en mayúsculas y sin tildes, la app guarda «Lucía Gómez»):
   - **0 candidatos** → cliente desconocido → **preguntar a Marisa**. → `07_transferencia_desconocido`.
   - **concepto vacío** (no permite desambiguar un ordenante abreviado) → **preguntar a Marisa**. → `05_bizum_romero` («ROMERO D», sin concepto).
   - **más de 1 candidato activo** → varios apartados posibles → **preguntar a Marisa**.
   - **exactamente 1 candidato** y concepto no vacío → **intentar registrar** (paso 5). → `01_bizum_carmen`, `09_bizum_silvia`, `03_transferencia_lucia`, `04_bizum_laura`, `06_bizum_paula`.
5. **Registrar el abono** `POST /api/apartados/{id}/abonos` con `{ importe, forma_pago: "bizum" }` y **On Error → Continue** (un `4xx` no debe tumbar el flujo):
   - **201** → abono registrado. La app emite `abono.registrado` y el **Flujo 02** envía el recibo. Si deja el pendiente en 0 €, el apartado queda **liquidado** y el recibo del Flujo 02 avisa de que puede recoger sus zapatos. → `01`/`09` (activo), `03_transferencia_lucia` (liquida).
   - **422** → la app rechazó por una regla → **avisar a Marisa con el motivo** que da la app (`detail`):
     - importe **supera lo pendiente** → `04_bizum_laura`.
     - **plazo vencido** (apartado fuera de plazo; sigue `activo` hasta que el Flujo 06 lo venza) → `06_bizum_paula`.

**Avisos a Marisa** (preguntar o avisar) = correo a la tienda (HTML) con el aviso original, lo que extrajo la IA, el apartado candidato si lo hay y el motivo; en desarrollo se ven en Mailpit. **El flujo nunca registra un abono en los casos dudosos ni de error.**

## Salidas

| Resultado | Qué hace el flujo | Correo(s) |
|---|---|---|
| Pago claro, dentro de reglas | `POST …/abonos` (201) | recibo al cliente **vía Flujo 02** |
| Pago que liquida | igual; el apartado queda liquidado | recibo final del cliente **vía Flujo 02** |
| No es un pago | nada | — |
| Dudoso (desconocido / sin concepto / varios) | nada en la app | **pregunta a Marisa** (tienda) |
| Rechazado por la app (de más / fuera de plazo) | nada se registra | **aviso a Marisa** con el motivo (tienda) |

## Casos de error

| Caso | Comportamiento |
|---|---|
| Aviso sin `Importe … EUR` (publicidad) | Rama «no es un pago» → se ignora, el flujo termina bien |
| `POST …/abonos` devuelve 422 | **On Error → Continue**: no falla; se avisa a Marisa con `detail` |
| La IA no devuelve `importe` o `ordenante` | Se trata como dudoso → preguntar a Marisa (nunca se registra a ciegas) |
| `GET`/`POST` de la API caído o 5xx, o fallo del nodo Groq | El flujo falla → lo captura el **Flujo 08 · Aviso de fallo** (`settings.errorWorkflow`) |
| El `importe` extraído no cuadra con el del asunto | Se usa el del **cuerpo** (`Importe … EUR`); el asunto es orientativo |

## Criterios de aceptación

Los de la issue (US-03), verificados por `tests/us-03/` y su evidencia en `docs/evidencia/us-03/`. Un escenario por correo de `data/correos/` (A–H), comprobando para cada uno: que se registró el abono **o** no se registró nada, el estado del apartado tras el pago, y el correo capturado en Mailpit (recibo del cliente vía Flujo 02, o pregunta/aviso a Marisa). La evidencia se lee en las **executions** de n8n (`GET /api/v1/executions/{id}`) y en el buzón de Mailpit; nada de comprobación solo-manual.

## Notas de arquitectura

- **IA solo extrae** (Groq, nodo `@n8n/n8n-nodes-langchain`): modelo gratuito y rápido, con nodo nativo. La clave va a una **credencial de n8n** (`credentials/`, cifrada), **nunca** en el JSON del flujo. Las decisiones viven en nodos del flujo (IF/Switch/Code), no en el prompt.
- **Por qué buscar por API y no fiarse del nombre del aviso**: el banco escribe en mayúsculas, sin tildes y a veces abreviado; la app es la fuente de verdad. La comparación normaliza acentos y mayúsculas y exige **un único** candidato activo (o nº de apartado explícito) para registrar.
- **`forma_pago: "bizum"`**: el enum de la app es `efectivo | tarjeta | bizum` (no hay «transferencia»). Los pagos a distancia (Bizum **y** transferencia) se registran como `bizum`, la única forma electrónica del enum. Limitación conocida: el cierre diario (Flujo 05) no distinguirá transferencia de Bizum.
- **El recibo no lo manda este flujo**: al registrar el abono, la app dispara `abono.registrado` → Receptor → **Flujo 02**. Así no se duplica la plantilla del recibo (criterio US-03: «el cliente recibe su recibo (US-02)»).
- **Receptor**: nueva rama `aviso.banco` en el Switch → `Ejecutar Flujo 03` (un sub-workflow por evento, regla de AGENTS). `settings.errorWorkflow = Flujo 08` en el flujo.
- **Avisos a Marisa**: nodos *Send Email* (SMTP) con la credencial `SMTP Mailpit (pruebas)`; en producción, una credencial SMTP real. `toEmail` de prueba sustituible por el correo real de la tienda.
