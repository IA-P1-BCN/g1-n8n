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

### 4. Importar los flujos en n8n

Los flujos viven en `workflows/`. Importa los JSON desde el editor de n8n (en proyectos se generan en la UI: `Workflows > Import from File`).

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
