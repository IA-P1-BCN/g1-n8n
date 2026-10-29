# Paso Firme

> Sistema de automatización y orquestación con **n8n** sobre la API de la zapatería Paso Firme. Automatiza el ciclo de vida de los apartados (confirmaciones, recibos de abonos y avisos) y la gestión de notificaciones a clientes y dependientes.

Infraestructura local orquestada mediante Docker Compose (`tienda` + `n8n` + `mailpit`).

---

## Servicios disponibles

Una vez arrancado el stack, los siguientes servicios quedan disponibles en local:

| Servicio | URL local | Descripción |
|---|---|---|
| **App de la tienda** | [http://localhost:8000](http://localhost:8000) | API de la tienda (SQLite en volumen persistente) y exportación a Excel |
| **Documentación API** | [http://localhost:8000/docs](http://localhost:8000/docs) | Explorador interactivo Swagger para probar endpoints y webhooks |
| **Editor de n8n** | [http://localhost:5678](http://localhost:5678) | Interfaz visual para construir, importar y monitorizar flujos |
| **Mailpit** | [http://localhost:8025](http://localhost:8025) | Buzón de pruebas para inspeccionar los correos enviados por los flujos |

---

## Mapa del proceso: hoy vs automatizado

El ciclo completo de apartado de la zapatería está modelado en **Mermaid** — [ver los flujos del proceso](docs/business/mapa-proceso-apartado/flujos.md): GitHub renderiza los diagramas directamente al abrir la página, sin necesidad de visores externos ni importar ficheros.

### ¿Qué cambia con n8n?

| Aspecto | Proceso actual (a mano) | Proceso automatizado (n8n) |
|---|---|---|
| **Registro del apartado** | Libreta de papel, post-its y calculadora | App web de la tienda con persistencia en base de datos |
| **Confirmación al cliente** | Verbal en mostrador; el cliente no conserva comprobante | Correo automático con datos del apartado (`apartado.creado` → Flujo 01) |
| **Recibos de abonos** | Anotación manual en libreta y cálculo mental del saldo | Correo automático con saldo restante o aviso de liquidación (`abono.registrado` → Flujo 02) |
| **Control de vencidos** | Repaso manual diario de fichas (frecuentes olvidos) | Detección automática y emisión del Vale para la tienda (Flujo 06, reservado) |
| **Cierre diario** | Suma manual de caja, tickets y reconciliación con el banco | Reconciliación automática de ventas y formas de pago (Flujo 04, reservado) |
| **Gestión de incidencias** | Errores silenciosos que nadie nota | Flujo 08 captura fallos de ejecución y avisa de inmediato a Marisa (`errorWorkflow`) |
| **Migración del Excel antiguo** | Pasar filas del Excel una a una a mano | Flujo 09 limpia fechas/importes/nombres de `data/*.csv`, carga por API sin duplicar y envía informe de casos dudosos |

---

## Puesta en marcha

### Requisitos previos

- [Docker Desktop](https://docs.docker.com/get-docker/) (o daemon de Docker equivalente)
- [Task](https://taskfile.dev/) (v3.54 o superior — runner de tareas del proyecto)
- [Python](https://www.python.org/) (v3.11 o superior — para scripts de utilidades y suites de pruebas)

### 1. Clonar el repositorio

```bash
git clone https://github.com/IA-P1-BCN/g1-n8n.git
cd g1-n8n
```

### 2. Configurar el `.env`

Genera el fichero de variables de entorno a partir de la plantilla:

```bash
task install
```

> [!NOTE]
> `task install` copia `.env.example` a `.env` únicamente si este no existe previamente; nunca sobreescribe tu configuración actual.

Edita el fichero `.env` según tus necesidades:

```env
API_KEY=cambia-esta-clave
N8N_WEBHOOK_URL=http://n8n:5678/webhook/tienda
SEED=1
```

- `API_KEY`: Clave que se genera en la interfaz de n8n (**Settings > n8n API**). La suite de tests `tests/us-17/` y el flag `--esperar` de `task payload` la usan para consultar las ejecuciones en la API interna de n8n.
- `N8N_WEBHOOK_URL`: URL interna de red Docker por la que la app notifica al receptor de n8n.
- `SEED`: Con `SEED=1` la tienda se inicializa con historial de datos la primera vez. Usa `SEED=0` para arrancar con base de datos vacía.

### 3. Arrancar los servicios

Levanta los contenedores en segundo plano:

```bash
task arrancar
```

### 4. Importar flujos y credenciales en n8n

Los flujos y credenciales del repositorio **no se cargan automáticamente** en el contenedor; deben importarse explícitamente:

```bash
task importar
```

Este comando (`scripts/n8n-importar.py`):
1. Detiene momentáneamente la instancia de n8n para evitar bloqueos en SQLite.
2. Ejecuta un contenedor *one-shot* con el CLI oficial de n8n compartiendo el volumen de datos.
3. Importa las credenciales desde `credentials/` y los flujos desde `workflows/`.
4. Activa todos los flujos importados.
5. Rearranca el servicio de n8n.

> [!TIP]
> Ejecuta `task importar` siempre tras levantar el stack por primera vez (o tras un `docker compose down -v`), así como cada vez que edites o descargues cambios en ficheros de `workflows/` o `credentials/`.

Si modificas flujos desde la interfaz web de n8n, expórtalos al fichero correspondiente del repositorio:

```bash
docker exec paso-firme-n8n-1 n8n export:workflow --all --stdout > workflows/flujo-nn-nombre.json
```

### 5. Configurar el MCP de n8n en opencode

El repositorio incluye la configuración lista para usar en `.opencode/mcp/n8n-mcp.cjs` y `opencode.json`:

- **macOS**: Funciona de forma automática vía `npx`.
- **Windows**: Requiere instalar el paquete globalmente una sola vez:

  ```bash
  npm install -g n8n-mcp
  ```

Para habilitar la gestión activa de workflows desde opencode, añade tu API key de n8n en `opencode.json`:

```json
"environment": {
  "N8N_API_URL": "http://localhost:5678",
  "N8N_API_KEY": "tu-clave"
}
```

---

## Flujos de n8n

### Catálogo de flujos incluidos

| Flujo | Fichero en `workflows/` | Disparador | Credenciales / variables |
|---|---|---|---|
| **Flujo 01 · Confirmación de apartado** | `flujo-01-confirmacion-apartado.json` | Evento `apartado.creado` vía receptor | SMTP Mailpit (pruebas) |
| **Flujo 02 · Recibo de cada abono** | `flujo-02-recibo-de-cada-abono.json` | Evento `abono.registrado` vía receptor | SMTP Mailpit (pruebas) |
| **Flujo 08 · Aviso de fallo** | `flujo-08-aviso-de-fallo.json` | *Error Trigger*: se dispara automáticamente si cualquier flujo falla | SMTP Mailpit (pruebas) |
| **Flujo 09 · Migración del Excel** | `flujo-09-migracion-excel.json` | *Manual Trigger*: lee `/data-fuentes/*.csv` (`./data:/data-fuentes:ro`), migra por API sin duplicar y envía informe de casos dudosos | SMTP Mailpit (pruebas), `API_KEY` (`.env`) |
| **Receptor · Webhook tienda** | `receptor-webhook-tienda.json` | `POST /webhook/tienda` (webhook único) | — |

### Eventos del receptor y ramas del Switch

Un único endpoint publicado (`/webhook/tienda`) recibe todos los eventos de la app y los distribuye mediante un nodo Switch (`Repartir por evento`). Su especificación formal está en [`specs/receptor-webhook-tienda.md`](specs/receptor-webhook-tienda.md).

| Evento recibido | Rama del Switch | Destino / Tratamiento |
|---|---|---|
| `apartado.creado` | `apartado.creado` | **Flujo 01** · Confirmación de apartado |
| `abono.registrado` | `abono.registrado` | **Flujo 02** · Recibo de cada abono |
| `venta.registrada` | `venta.registrada` | Reservada para **Flujo 04** (Cierre diario · US-09) |
| `apartado.vencido` | `apartado.vencido` | Reservada para **Flujo 06** (Vencimiento y Vale · US-07) |
| *(cualquier otro)* | `evento desconocido` | Se registra en Executions de n8n sin perderse |

### Credenciales y variables

> [!IMPORTANT]
> Los ficheros JSON de `workflows/` nunca contienen contraseñas ni claves en claro: solo referencian credenciales por identificador. Los valores sensibles residen en `credentials/` (o se configuran en n8n) y nunca deben subirse al repositorio.

| Credencial / variable | Tipo | Configuración requerida | Utilizada por |
|---|---|---|---|
| `SMTP Mailpit (pruebas)` | SMTP | Host `mailpit`, puerto `1025`, sin autenticación ni TLS | Flujos 01, 02, 08 y 09 |
| Credencial SMTP producción | SMTP / Gmail OAuth2 | Credenciales reales del servidor de correo de la tienda | Flujos 01, 02, 08 y 09 |
| `API_KEY` (`.env`) | Token de API | Token generado en n8n (**Settings > n8n API**) | Comunicación app ↔ n8n (y Flujo 09) |
| `N8N_WEBHOOK_URL` (`.env`) | URL HTTP | Dirección del receptor (`http://n8n:5678/webhook/tienda`) | Notificaciones de la app |
| `cambia-esta-direccion@paso-firme.local` | Email destino | Sustituir por el correo real de Marisa antes de ir a producción | Flujos 01, 02, 08 y 09 |

---

## Pruebas y desarrollo

### Datos frescos para la demo (`task demo`)

Genera de forma limpia y por API los escenarios de prueba para demostrar el funcionamiento del sistema:

```bash
task demo             # Añade un juego de datos de prueba sobre el estado actual
task demo -- --limpio # Vacía previamente la app y Mailpit para empezar de cero
```

- `--limpio`: Vacía apartados, abonos, ventas, vales y correos de Mailpit; **no altera n8n ni borra flujos/credenciales**.
- Escenarios creados:
  1. Un apartado nuevo con abonos sucesivos **hasta liquidarlo**.
  2. Un apartado **a punto de vencer** y otro **vencido con su vale emitido**.
  3. **Ventas del día** en efectivo, tarjeta y Bizum.

#### Guía rápida de escenarios de demo

| Flujo | Escenario de `task demo` | Dónde comprobar el resultado |
|---|---|---|
| **01 · Confirmación de apartado** | Apartado liquidado | Correo «Apartado confirmado» en Mailpit |
| **02 · Recibo de cada abono** | Sus 3 abonos y el abono parcial del apartado «por vencer» | Correos «Recibo de tu abono» y «Último abono recibido» |
| **04 · Cierre diario** *(pendiente)* | Ventas de hoy en efectivo, tarjeta y Bizum | Cuadre de caja |
| **06 · Vencimiento y vale** *(pendiente)* | Apartado vencido con su vale | Emisión y archivo de vale |
| **08 · Aviso de fallo** | No depende de datos: se prueba forzando un error | Correo de aviso técnico a Marisa |
| **09 · Migración del Excel** | CSV reales de `data/` (montados en `/data-fuentes:ro`) | 7 apartados, 3 abonos y 6 ventas en la app + correo «Informe de migración del Excel» en Mailpit |

### Probar el receptor con un payload propio (`task payload`)

Envía un evento simulado al receptor de n8n leyendo un fichero JSON:

```bash
task payload -- payloads/venta-registrada.json
```

```text
· payload: payloads/venta-registrada.json
· evento: venta.registrada
· destino: http://localhost:5678/webhook/tienda
· respuesta: 200 · {"message": "Workflow was started"}
```

Añade `--esperar` para inspeccionar la ejecución y la rama del Switch alcanzada (requiere `API_KEY` en `.env`):

```bash
task payload -- payloads/abono-registrado.json --esperar
```

```text
· ejecución: 154 · success · último paso: Repartir por evento
· rama: abono.registrado · 1 item(s)
```

- **Flags disponibles**:
  - `--esperar`: Consulta la API de n8n hasta que termine la ejecución (o venza el timeout).
  - `--url <URL>`: Destino alternativo (por defecto `http://localhost:5678`).
  - `--timeout <segundos>`: Tiempo máximo de espera (30 s por defecto).
- **Ficheros de ejemplo en `payloads/`**: `apartado-creado.json`, `abono-registrado.json`, `venta-registrada.json`, `apartado-vencido.json`. Estructura mínima requerida:

  ```json
  {
    "evento": "venta.registrada",
    "datos": {
      "id": 501,
      "fecha": "2026-10-27",
      "concepto": "Botín piel marrón · 38",
      "importe": 89.9,
      "forma_pago": "efectivo"
    }
  }
  ```

### Ejecución de pruebas de aceptación (`task test`)

Ejecuta las suites de pruebas de aceptación automatizadas de extremo a extremo:

```bash
task test             # Ejecuta todas las suites en tests/
task test -- us-17    # Ejecuta únicamente la suite de una historia de usuario
```

---

## Documentación del proyecto

- [Glosario del dominio](GLOSSARY.md) — Términos y definiciones oficiales (*Apartado*, *Abono*, *Liquidado*, *Vale*…).
- [Reglas del negocio](docs/business/business-rules.md) — Plazos, importes mínimos, políticas de vencimiento y vales.
- [Datos de partida](docs/business/business-data.md) — Estructura del Excel histórico y notificaciones bancarias.
- [Guía técnica de la app](docs/guia-de-la-app.md) — Detalle de endpoints, autenticación y base de datos.
- [Mapa de flujos del proceso](docs/business/mapa-proceso-apartado/flujos.md) — Diagramas Mermaid de los flujos actual y automatizado.
- [Bitácora de IA](docs/ai-log.md) — Trazabilidad de decisiones de diseño, prompts y resolución de incidencias.
