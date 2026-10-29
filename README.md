# Paso Firme

> Sistema de automatizaciÃ³n y orquestaciÃ³n con **n8n** sobre la API de la zapaterÃ­a Paso Firme. Automatiza el ciclo de vida de los apartados (confirmaciones, recibos de abonos y avisos) y la gestiÃ³n de notificaciones a clientes y dependientes.

Infraestructura local orquestada mediante Docker Compose (`tienda` + `n8n` + `mailpit`).

---

## Servicios disponibles

Una vez arrancado el stack, los siguientes servicios quedan disponibles en local:

| Servicio | URL local | DescripciÃ³n |
|---|---|---|
| **App de la tienda** | [http://localhost:8000](http://localhost:8000) | API de la tienda (SQLite en volumen persistente) y exportaciÃ³n a Excel |
| **DocumentaciÃ³n API** | [http://localhost:8000/docs](http://localhost:8000/docs) | Explorador interactivo Swagger para probar endpoints y webhooks |
| **Editor de n8n** | [http://localhost:5678](http://localhost:5678) | Interfaz visual para construir, importar y monitorizar flujos |
| **Mailpit** | [http://localhost:8025](http://localhost:8025) | BuzÃ³n de pruebas para inspeccionar los correos enviados por los flujos |

---

## Mapa del proceso: hoy vs automatizado

El ciclo completo de apartado de la zapaterÃ­a estÃ¡ modelado en **Mermaid** â [ver los flujos del proceso](docs/business/mapa-proceso-apartado/flujos.md): GitHub renderiza los diagramas directamente al abrir la pÃ¡gina, sin necesidad de visores externos ni importar ficheros.

### Â¿QuÃ© cambia con n8n?

| Aspecto | Proceso actual (a mano) | Proceso automatizado (n8n) |
|---|---|---|
| **Registro del apartado** | Libreta de papel, post-its y calculadora | App web de la tienda con persistencia en base de datos |
| **ConfirmaciÃ³n al cliente** | Verbal en mostrador; el cliente no conserva comprobante | Correo automÃ¡tico con datos del apartado (`apartado.creado` â Flujo 01) |
| **Recibos de abonos** | AnotaciÃ³n manual en libreta y cÃ¡lculo mental del saldo | Correo automÃ¡tico con saldo restante o aviso de liquidaciÃ³n (`abono.registrado` â Flujo 02) |
| **Control de vencidos** | Repaso manual diario de fichas (frecuentes olvidos) | Recordatorios automÃ¡ticos a 7d y 1d + vencimiento por API con envÃ­o del Vale al cliente y aviso de zapatos que vuelven a la venta a Marisa (Flujo 06) |
| **Aviso de ventas grandes** | Marisa no se entera de las ventas grandes mientras no estÃ© en la tienda | Correo automÃ¡tico cuando la venta pasa del umbral (`venta.registrada` â Flujo 04) |

| **GestiÃ³n de incidencias** | Errores silenciosos que nadie nota | Flujo 08 captura fallos de ejecuciÃ³n y avisa de inmediato a Marisa (`errorWorkflow`) |
| **MigraciÃ³n del Excel antiguo** | Pasar filas del Excel una a una a mano | Flujo 09 limpia fechas/importes/nombres de `data/*.csv`, carga por API sin duplicar y envÃ­a informe de casos dudosos |

---

## Puesta en marcha

### Requisitos previos

- [Docker Desktop](https://docs.docker.com/get-docker/) (o daemon de Docker equivalente)
- [Task](https://taskfile.dev/) (v3.54 o superior â runner de tareas del proyecto)
- [Python](https://www.python.org/) (v3.11 o superior â para scripts de utilidades y suites de pruebas)

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
> `task install` copia `.env.example` a `.env` Ãºnicamente si este no existe previamente; nunca sobreescribe tu configuraciÃ³n actual.

Edita el fichero `.env` segÃºn tus necesidades:

```env
API_KEY=cambia-esta-clave
N8N_WEBHOOK_URL=http://n8n:5678/webhook/tienda
SEED=1
UMBRAL_VENTA_GRANDE=200
```

- `API_KEY`: Clave que se genera en la interfaz de n8n (**Settings > n8n API**). La suite de tests `tests/us-17/` y el flag `--esperar` de `task payload` la usan para consultar las ejecuciones en la API interna de n8n.
- `N8N_WEBHOOK_URL`: URL interna de red Docker por la que la app notifica al receptor de n8n.
- `UMBRAL_VENTA_GRANDE`: ventas por encima de este importe (â¬) avisan a Marisa por correo (Flujo 04); el escenario B de `tests/us-09/` lo cambia solo para probar que no hay que editar el flujo.
- `SEED`: Con `SEED=1` la tienda se inicializa con historial de datos la primera vez. Usa `SEED=0` para arrancar con base de datos vacÃ­a.

### 3. Arrancar los servicios

Levanta los contenedores en segundo plano:

```bash
task arrancar
```

### 4. Importar flujos y credenciales en n8n

Los flujos y credenciales del repositorio **no se cargan automÃ¡ticamente** en el contenedor; deben importarse explÃ­citamente:

```bash
task importar
```

Este comando (`scripts/n8n-importar.py`):
1. Detiene momentÃ¡neamente la instancia de n8n para evitar bloqueos en SQLite.
2. Ejecuta un contenedor *one-shot* con el CLI oficial de n8n compartiendo el volumen de datos.
3. Importa las credenciales desde `credentials/` y los flujos desde `workflows/`.
4. Activa todos los flujos importados.
5. Rearranca el servicio de n8n.

> [!TIP]
> Ejecuta `task importar` siempre tras levantar el stack por primera vez (o tras un `docker compose down -v`), asÃ­ como cada vez que edites o descargues cambios en ficheros de `workflows/` o `credentials/`.

Si modificas flujos desde la interfaz web de n8n, expÃ³rtalos al fichero correspondiente del repositorio:

```bash
docker exec paso-firme-n8n-1 n8n export:workflow --all --stdout > workflows/flujo-nn-nombre.json
```

### 5. Configurar el MCP de n8n en opencode

El repositorio incluye la configuraciÃ³n lista para usar en `.opencode/mcp/n8n-mcp.cjs` y `opencode.json`:

- **macOS**: Funciona de forma automÃ¡tica vÃ­a `npx`.
- **Windows**: Requiere instalar el paquete globalmente una sola vez:

  ```bash
  npm install -g n8n-mcp
  ```

Para habilitar la gestiÃ³n activa de workflows desde opencode, aÃ±ade tu API key de n8n en `opencode.json`:

```json
"environment": {
  "N8N_API_URL": "http://localhost:5678",
  "N8N_API_KEY": "tu-clave"
}
```

---

## Flujos de n8n

### CatÃ¡logo de flujos incluidos

| Flujo | Fichero en `workflows/` | Disparador | Credenciales / variables |
|---|---|---|---|
| **Flujo 01 Â· ConfirmaciÃ³n de apartado** | `flujo-01-confirmacion-apartado.json` | Evento `apartado.creado` vÃ­a receptor | SMTP Mailpit (pruebas) |
| **Flujo 02 Â· Recibo de cada abono** | `flujo-02-recibo-de-cada-abono.json` | Evento `abono.registrado` vÃ­a receptor | SMTP Mailpit (pruebas) |
| **Flujo 03 Â· Abonos a distancia** | `flujo-03-abonos-a-distancia.json` | Evento `aviso.banco` vÃ­a receptor + *Form Trigger* (pegar aviso) | Groq (abonos a distancia), API tienda (X-API-Key), SMTP Mailpit (pruebas) |
| **Flujo 06 Â· Recordatorios de vencimiento** | `flujo-06-recordatorios-vencimiento.json` | Programado cada maÃ±ana (09:00) o manual: avisa a 7 dÃ­as y 1 dÃ­a sin duplicar; vence por API los fuera de plazo, envÃ­a el Vale al cliente y avisa a Marisa de los zapatos que vuelven a la venta | SMTP Mailpit (pruebas), `API_KEY` |
| **Flujo 07 Â· Informe mensual** | `flujo-07-informe-mensual.json` | Programado dÃ­a 1 de mes (08:00) o manual | SMTP Mailpit (pruebas), `API_KEY` |
| **Flujo 08 Â· Aviso de fallo** | `flujo-08-aviso-de-fallo.json` | *Error Trigger*: se dispara automÃ¡ticamente si cualquier flujo falla | SMTP Mailpit (pruebas) |
| **Flujo 04 Â· Aviso de ventas grandes** | `flujo-04-aviso-ventas-grandes.json` | Evento `venta.registrada` vÃ­a receptor | SMTP Mailpit (pruebas), `UMBRAL_VENTA_GRANDE` |
| **Flujo 09 Â· MigraciÃ³n del Excel** | `flujo-09-migracion-excel.json` | *Manual Trigger*: lee `/data-fuentes/*.csv` (`./data:/data-fuentes:ro`), migra por API sin duplicar y envÃ­a informe de casos dudosos | SMTP Mailpit (pruebas), `API_KEY` (`.env`) |
| **Receptor Â· Webhook tienda** | `receptor-webhook-tienda.json` | `POST /webhook/tienda` (webhook Ãºnico) | â |

### Eventos del receptor y ramas del Switch

Un Ãºnico endpoint publicado (`/webhook/tienda`) recibe todos los eventos de la app y los distribuye mediante un nodo Switch (`Repartir por evento`). Su especificaciÃ³n formal estÃ¡ en [`specs/receptor-webhook-tienda.md`](specs/receptor-webhook-tienda.md).

| Evento recibido | Rama del Switch | Destino / Tratamiento |
|---|---|---|
| `apartado.creado` | `apartado.creado` | **Flujo 01** Â· ConfirmaciÃ³n de apartado |
| `abono.registrado` | `abono.registrado` | **Flujo 02** Â· Recibo de cada abono |
| `venta.registrada` | `venta.registrada` | **Flujo 04** Â· Aviso de ventas grandes |

| `apartado.vencido` | `apartado.vencido` | Reservada para **Flujo 06** (Vencimiento y Vale Â· US-07) |
| *(cualquier otro)* | `evento desconocido` | Se registra en Executions de n8n sin perderse |

### Credenciales y variables

> [!IMPORTANT]
> Los ficheros JSON de `workflows/` nunca contienen contraseÃ±as ni claves en claro: solo referencian credenciales por identificador. Los valores sensibles residen en `credentials/` (o se configuran en n8n) y nunca deben subirse al repositorio.

| Credencial / variable | Tipo | ConfiguraciÃ³n requerida | Utilizada por |
|---|---|---|---|

| `SMTP Mailpit (pruebas)` | SMTP | Host `mailpit`, puerto `1025`, sin autenticaciÃ³n ni TLS | Flujos 01, 02, 03, 06, 07, 08 y 09 |

| Credencial SMTP producciÃ³n | SMTP / Gmail OAuth2 | Credenciales reales del servidor de correo de la tienda | Flujos 01, 02, 03, 06, 07, 08 y 09 |

| `Groq (abonos a distancia)` | Groq API | Clave gratuita de [console.groq.com](https://console.groq.com) (crÃ©ala en n8n, **nunca** en el JSON) | Flujo 03 (solo extracciÃ³n con IA) |

| `API tienda (X-API-Key)` | Header Auth | Cabecera `X-API-Key` con el valor de `API_KEY` del `.env`; la usa n8n para llamar a la API de la app | Flujo 03 |

| `API_KEY` (`.env`) | Token de API | Token generado en n8n (**Settings > n8n API**) | ComunicaciÃ³n app â n8n (Flujos 03, 06, 07 y 09) |

| `N8N_WEBHOOK_URL` (`.env`) | URL HTTP | DirecciÃ³n del receptor (`http://n8n:5678/webhook/tienda`) | Notificaciones de la app |

| `cambia-esta-direccion@paso-firme.local` | Email destino | Sustituir por el correo real de Marisa antes de ir a producciÃ³n | Flujos 01, 02, 03, 06, 07, 08 y 09 |

| `UMBRAL_VENTA_GRANDE` (`.env`) | Umbral (â¬) | Ventas por encima de este importe avisan a Marisa; por defecto `200` | Flujo 04 |


---

## Pruebas y desarrollo

### Datos frescos para la demo (`task demo`)

Genera de forma limpia y por API los escenarios de prueba para demostrar el funcionamiento del sistema:

```bash
task demo             # AÃ±ade un juego de datos de prueba sobre el estado actual
task demo -- --limpio # VacÃ­a previamente la app y Mailpit para empezar de cero
```

- `--limpio`: VacÃ­a apartados, abonos, ventas, vales y correos de Mailpit; **no altera n8n ni borra flujos/credenciales**.
- Escenarios creados:
  1. Un apartado nuevo con abonos sucesivos **hasta liquidarlo**.
  2. Un apartado **a punto de vencer** y otro **vencido con su vale emitido**.
  3. **Ventas del dÃ­a** en efectivo, tarjeta y Bizum.

#### GuÃ­a rÃ¡pida de escenarios de demo

| Flujo | Escenario de `task demo` | DÃ³nde comprobar el resultado |
|---|---|---|
| **01 Â· ConfirmaciÃ³n de apartado** | Apartado liquidado | Correo Â«Apartado confirmadoÂ» en Mailpit |
| **02 Â· Recibo de cada abono** | Sus 3 abonos y el abono parcial del apartado Â«por vencerÂ» | Correos Â«Recibo de tu abonoÂ» y Â«Ãltimo abono recibidoÂ» |
| **04 Â· Cierre diario** *(pendiente)* | Ventas de hoy en efectivo, tarjeta y Bizum | Cuadre de caja |
| **06 Â· Recordatorios de vencimiento** | Apartado Â«por vencerÂ» (7 dÃ­as) | Correo Â«Tu apartado vence en 7 dÃ­asÂ» en Mailpit (y Â«MaÃ±ana vence tu apartadoÂ» a 1 dÃ­a) |
| **06 Â· Vencimiento y vale** | Apartado fuera de plazo (`fecha_limite < hoy`) | `POST /api/apartados/{id}/vencer`, correo Â«Tu vale por apartado vencidoÂ» al cliente y correo Â«Apartados vencidos hoy: â¦ vuelven a la ventaÂ» a Marisa |
| **08 Â· Aviso de fallo** | No depende de datos: se prueba forzando un error | Correo de aviso tÃ©cnico a Marisa |
| **09 Â· MigraciÃ³n del Excel** | CSV reales de `data/` (montados en `/data-fuentes:ro`) | 7 apartados, 3 abonos y 6 ventas en la app + correo Â«Informe de migraciÃ³n del ExcelÂ» en Mailpit |

### Avisos del banco en Mailpit (`task correos`)

Carga en el buzÃ³n de Mailpit los avisos del banco de [`data/correos/`](data/correos/) (Bizum, transferencias y publicidad de **bancos ficticios** sobre dominios reservados `.example`), que es la entrada que leerÃ¡ el **Flujo 03 Â· Abonos a distancia**:

```bash
task correos             # Entrega los 9 avisos a Mailpit (http://localhost:8025)
task correos -- --limpio # VacÃ­a antes el buzÃ³n para empezar de cero
```

- `--limpio`: VacÃ­a el buzÃ³n de Mailpit antes de cargar (no toca la app ni n8n).
- `--solo 01,03`: Carga solo esos avisos, por el prefijo del nombre del fichero.
- Cada aviso conserva su importe, ordenante y concepto; el script comprueba al final que todos estÃ¡n en el buzÃ³n y lista remitente e importe. Los tres bancos ficticios (`Banco Peralta`, `Caja Rivera`, `Banco CastaÃ±o`) permiten verificar que el flujo no depende de un Ãºnico remitente.

### Probar el receptor con un payload propio (`task payload`)

EnvÃ­a un evento simulado al receptor de n8n leyendo un fichero JSON:

```bash
task payload -- payloads/venta-registrada.json
```

```text
Â· payload: payloads/venta-registrada.json
Â· evento: venta.registrada
Â· destino: http://localhost:5678/webhook/tienda
Â· respuesta: 200 Â· {"message": "Workflow was started"}
```

AÃ±ade `--esperar` para inspeccionar la ejecuciÃ³n y la rama del Switch alcanzada (requiere `API_KEY` en `.env`):

```bash
task payload -- payloads/abono-registrado.json --esperar
```

```text
Â· ejecuciÃ³n: 154 Â· success Â· Ãºltimo paso: Repartir por evento
Â· rama: abono.registrado Â· 1 item(s)
```

- **Flags disponibles**:
  - `--esperar`: Consulta la API de n8n hasta que termine la ejecuciÃ³n (o venza el timeout).
  - `--url <URL>`: Destino alternativo (por defecto `http://localhost:5678`).
  - `--timeout <segundos>`: Tiempo mÃ¡ximo de espera (30 s por defecto).
- **Ficheros de ejemplo en `payloads/`**: `apartado-creado.json`, `abono-registrado.json`, `venta-registrada.json`, `apartado-vencido.json`. Estructura mÃ­nima requerida:

  ```json
  {
    "evento": "venta.registrada",
    "datos": {
      "id": 501,
      "fecha": "2026-10-27",
      "concepto": "BotÃ­n piel marrÃ³n Â· 38",
      "importe": 89.9,
      "forma_pago": "efectivo"
    }
  }
  ```

### EjecuciÃ³n de pruebas de aceptaciÃ³n (`task test`)

Ejecuta las suites de pruebas de aceptaciÃ³n automatizadas de extremo a extremo:

```bash
task test             # Ejecuta todas las suites en tests/
task test -- us-17    # Ejecuta Ãºnicamente la suite de una historia de usuario
```

---

## DocumentaciÃ³n del proyecto

- [Glosario del dominio](GLOSSARY.md) â TÃ©rminos y definiciones oficiales (*Apartado*, *Abono*, *Liquidado*, *Vale*â¦).
- [Reglas del negocio](docs/business/business-rules.md) â Plazos, importes mÃ­nimos, polÃ­ticas de vencimiento y vales.
- [Datos de partida](docs/business/business-data.md) â Estructura del Excel histÃ³rico y notificaciones bancarias.
- [GuÃ­a tÃ©cnica de la app](docs/guia-de-la-app.md) â Detalle de endpoints, autenticaciÃ³n y base de datos.
- [Mapa de flujos del proceso](docs/business/mapa-proceso-apartado/flujos.md) â Diagramas Mermaid de los flujos actual y automatizado.
- [BitÃ¡cora de IA](docs/ai-log.md) â Trazabilidad de decisiones de diseÃ±o, prompts y resoluciÃ³n de incidencias.
