# Paso Firme

Orquestación de n8n sobre la API de la tienda: flujos de confirmación de apartados, ventas y notificaciones. Infrastructure local via docker-compose (tienda + n8n + MailPit).

## Instalación

### Requisitos

- [Docker](https://docs.docker.com/get-docker/)
- [Task](https://taskfile.dev/) (v3.54 o superior — el runner de `task install`, `task arrancar`, `task importar` y `task test`)
- [Python](https://www.python.org/) (v3.11 o superior — scripts de la carpeta `scripts/`)

### 1. Clonar el repositorio

```bash
git clone https://github.com/IA-P1-BCN/g1-n8n.git
cd g1-n8n
```

### 2. Configurar el `.env`

```bash
task install
```

(Copia `.env.example` a `.env`; si ya existía, no lo sobreescribe.) Edita `.env`:

```env
API_KEY=cambia-esta-clave
N8N_WEBHOOK_URL=http://n8n:5678/webhook/tienda
SEED=1
```

> **Nota:** la clave `API_KEY` se obtiene dentro de la interfaz de n8n: **Settings > n8n API** (en el paso 5 verás cómo usarla en opencode).

### 3. Arrancar los servicios

```bash
task arrancar
```

Después de la primera arrancada (o tras el `down -v`), importa flujos y credenciales: `task importar` (ver [paso 4](#4-flujos-de-n8n-importar-y-credenciales)).

| Servicio | URL                       | Descripción                                        |
| -------- | ------------------------- | -------------------------------------------------- |
| tienda   | http://localhost:8000     | API de la tienda (SQLite en volumen persistente)   |
| n8n      | http://localhost:5678     | Editor de n8n                                      |
| mailpit  | http://localhost:8025     | Buzón de pruebas: correos enviados por los flujos  |

Con `SEED=1` la tienda se arranca con datos la primera vez (usa `SEED=0` para arrancar vacía).

### 4. Flujos de n8n: importar y credenciales

Los flujos viven en `workflows/` y las credenciales que usan van en `credentials/` (en claro en el repo; n8n las cifra al importarlas). La importación **no es automática**: se lanza a voluntad con:

```bash
task importar
```

(`scripts/n8n-importar.py`: para n8n, sube credenciales y flujos al CLI de n8n en contenedores one-shot con el volumen de datos, activa los flujos que queden inactivos y rearranca n8n.) Lánzalo **al levantar el stack por primera vez** y **tras editar o añadir** cualquier JSON. En local el SMTP apunta a Mailpit (`mailpit:1025`, sin TLS), así que cualquier correo que envía un flujo se ve en http://localhost:8025.
Si haces cambios en el editor de n8n, expórtalos al fichero exacto de `workflows/`:

```bash
docker exec paso-firme-n8n-1 n8n export:workflow --all --stdout > workflows/flujo-nn-nombre.json
```

#### Flujos incluidos

| Flujo | Fichero en `workflows/` | Disparador | Credenciales / variables |
|---|---|---|---|
| Flujo 01 · Confirmación de apartado | `flujo-01-confirmacion-apartado.json` | evento `apartado.creado` vía receptor | SMTP Mailpit (pruebas) |
| Flujo 02 · Recibo de cada abono | `flujo-02-recibo-de-cada-abono.json` | evento `abono.registrado` vía receptor | SMTP Mailpit (pruebas) |
| Flujo 08 · Aviso de fallo | `flujo-08-aviso-de-fallo.json` | *Error Trigger*: se dispara solo si otro flujo falla (el resto lo apuntan en sus ajustes) | SMTP Mailpit (pruebas) |
| Receptor · Webhook tienda | `receptor-webhook-tienda.json` | `POST /webhook/tienda` (la app avisa aquí) | — |

#### Credenciales y variables (lista completa, sin valores)

| Credencial / variable | Tipo | Qué hay que configurar (valores en tu entorno, no en el repo) | La usan los flujos |
|---|---|---|---|
| `SMTP Mailpit (pruebas)` | SMTP | servidor (`mailpit` en la red de Docker), puerto, usuario y contraseña (Mailpit no los pide en local) y TLS desactivado | 01, 02 y 08 |
| credencial SMTP real (producción) | SMTP u OAuth2 de Gmail | asignarla a los nodos de correo en lugar de la de Mailpit | 01, 02 y 08 |
| `API_KEY` (`.env`) | variable de la app | clave que exige la API de la tienda; la generas en n8n con **Settings > n8n API** | app ↔ n8n |
| `N8N_WEBHOOK_URL` (`.env`) | variable de la app | URL del receptor de n8n para los eventos de la tienda | todos los eventos |
| `cambia-esta-direccion@paso-firme.local` | `toEmail` de los avisos a la tienda | **sustituir por el correo real de la tienda** antes de pasar a producción | 01, 02 y 08 |

Ninguna credencial pide valores dentro de los JSON de `workflows/`: se referencian por id/nombre y los valores viven en `credentials/` (o en n8n) — nunca los subas al repo.

Más documentación: [guía de la app](docs/guia-de-la-app.md) (para qué sirve cada endpoint y cómo probarlo) y [glosario del dominio](GLOSSARY.md) (Abono, Pendiente, Liquidado, Vale…, el vocabulario de flujos y mensajes) — o sigue abajo para probar el receptor con un payload propio.

#### Probar el receptor con un payload propio

En vez de escribir el JSON a mano en la terminal (se escapa mal, sobre todo en PowerShell), guárdalo en un fichero y lánzalo:

```bash
task payload -- payloads/venta-registrada.json
```

```
· payload: payloads/venta-registrada.json
· evento: venta.registrada
· destino: http://localhost:5678/webhook/tienda
· respuesta: 200 · {"message": "Workflow was started"}
```

Añade `--esperar` para ver en la terminal la ejecución y a qué rama del Switch fue (necesita la clave `API_KEY` del `.env`):

```bash
task payload -- payloads/abono-registrado.json --esperar
```

```
· ejecución: 154 · success · último paso: Repartir por evento
· rama: abono.registrado · 1 item(s)
```

Hay ejemplos listos para copiar y retocar en `payloads/` (`apartado-creado.json`, `abono-registrado.json`, `venta-registrada.json`, `apartado-vencido.json`). El mínimo es un objeto con `evento` y `datos`:

```json
{
  "evento": "venta.registrada",
  "datos": { "id": 501, "fecha": "2026-10-27", "concepto": "Botín piel marrón · 38", "importe": 89.9, "forma_pago": "efectivo" }
}
```

- Destino: variable `N8N_URL` (por defecto `http://localhost:5678`) o `--url`. Ojo: el `.env` guarda `http://n8n:5678/...`, que es la URL interna de Docker para la app; desde el host usa la de por defecto.
- Códigos de salida: `0` bien · `1` fichero, JSON o `evento` inválido (o respuesta distinta de 200) · `2` uso. Al lanzarlo con `task`, cualquier fallo termina con el código 201 del propio task.

### 5. Configurar el MCP de n8n en opencode

El proyecto ya incluye la configuración del MCP en `opencode.json` (`.opencode/mcp/n8n-mcp.cjs`). El arranque es cross-platform:

- **macOS**: no requiere instalación adicional (usa `npx` como fallback).
- **Windows**: instala el paquete una única vez:

  ```bash
  npm install -g n8n-mcp
  ```

Después, abre el proyecto con opencode y el servidor MCP de n8n estará disponible. Las herramientas de documentación de nodos funcionan ya; si además quieres que gestione los workflows de tu n8n real, crea un token en n8n (Settings > n8n API) y añádelo al environment del MCP en `opencode.json`:

```json
"environment": {
  "N8N_API_URL": "http://localhost:5678",
  "N8N_API_KEY": "tu-clave"
}
```
