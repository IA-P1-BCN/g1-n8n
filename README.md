# Paso Firme

Orquestación de n8n sobre la API de la tienda: flujos de confirmación de apartados, ventas y notificaciones. Infrastructure local via docker-compose (tienda + n8n + MailPit).

## Instalación

### Requisitos

- [Docker](https://docs.docker.com/get-docker/)
- [Node.js](https://nodejs.org/) (v20 o superior, necesario para opencode y el MCP de n8n)

### 1. Clonar el repositorio

```bash
git clone https://github.com/IA-P1-BCN/g1-n8n.git
cd g1-n8n
```

### 2. Configurar el `.env`

```bash
cp .env.example .env
```

Edita `.env`:

```env
API_KEY=cambia-esta-clave
N8N_WEBHOOK_URL=http://n8n:5678/webhook/tienda
SEED=1
```

> **Nota:** la clave `API_KEY` se obtiene dentro de la interfaz de n8n: **Settings > n8n API** (en el paso 5 verás cómo usarla en opencode).

### 3. Arrancar los servicios

```bash
docker compose up -d
```

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

Más documentación: [guía de la app](docs/guia-de-la-app.md) (para qué sirve cada endpoint y cómo probarlo) y [glosario del dominio](GLOSSARY.md) (Abono, Pendiente, Liquidado, Vale…, el vocabulario de flujos y mensajes).

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
