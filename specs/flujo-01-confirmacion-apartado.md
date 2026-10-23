# Spec SDD · Flujo 01 · Confirmación al apartado

> **Historia**: US-01 ([issue #1](https://github.com/IA-P1-BCN/g1-n8n/issues/1)) · **Nivel**: 🟢 Esencial · **Vocabulario**: [`GLOSSARY.md`](../GLOSSARY.md)

## Disparador

Sub-workflow, llamado por el **Receptor de eventos** (último scaffold de US-17) cuando llega el evento de la app:

```json
{ "evento": "apartado.creado", "datos": { "id": 25, "fecha": "2026-10-20", "cliente": "Carmen Ruiz", "email": "…", "producto": "Botín piel marrón", "talla": "38", "precio": 89.9, "abonado": 10.0, "pendiente": 79.9, "fecha_limite": "2027-01-18", "estado": "activo" } }
```

El receptor levanta el `body` del webhook con un nodo *Set* (`{evento, datos}` sin tocar los datos) y su Switch reparte por `evento` (guía de la app, §6).

## Entradas

- `datos.*`: los campos que la app envía en el evento `apartado.creado` (**no se recalcula nada**: los importes que llegan son los que se muestran).

## Salidas

1. **Cliente con email** → mensaje (HTML) con: producto, talla, precio, abonado, pendiente y fecha límite.
   - Asunto: `👟 Apartado confirmado · Zapatería Paso Firme`
   - Cuerpo: datos del apartado tal cual (`datos.precio` €, `datos.abonado` €, `datos.pendiente` €, límite `datos.fecha_limite`).
2. **Cliente sin email** (Escenario B) → no se envía nada al cliente; **aviso a la tienda** (HTML) para que contacte a la persona y asegure el envío. `datos.email` nulo/vacío → rama `false` del IF.
3. Ninguna rama modifica la app.

## Casos de error

| Caso | Comportamiento |
|---|---|
| `datos.email` vacío | Rama `false` → aviso a la tienda (el flujo **no** falla) |
| Error de envío (SMTP/API) | El flujo falla → lo captura el futuro Error Workflow (US-05) |
| Evento equivocado `apartado.creado` no llega | No se ejecuta nada (el receptor solo llama a este flujo con su evento) |

## Criterios de aceptación

Los de la issue (US-01): de ahí a la prueba de usuario (Escenario A: mensaje en <1 min con los importes de la app; Escenario B: sin email, el flujo no falla y avisa a la tienda).

## Notas de arquitectura

- **Un único webhook receptor** (`POST /webhook/tienda`, `N8N_WEBHOOK_URL`) con nodo **Switch** por `$json.evento` (tras un nodo *Set* que levanta `body`) lo comparten los 4 eventos del nivel Esencial.
- Cada flujo es un **sub-workflow** (Execute Workflow / When Executed by Another Workflow) → 1 rama + 1 PR por tarea.
- En esta PR el receptor va como **scaffold de US-17** con solo el evento `apartado.creado` conectado.
- **Envío de correo**: nodos *Send Email* (SMTP) con la credencial `SMTP Mailpit (pruebas)` → durante el desarrollo los correos se ven en el **buzón de pruebas Mailpit** (`docker-compose.yml`, web en http://localhost:8025). Para **producción** basta asignar a los dos nodos una credencial SMTP real (u OAuth2 de Gmail) con los mismos campos.
- Los correos de prueba van con remitente `n8n@paso-firme.local`; el aviso a la tienda tiene un `toEmail` de prueba (`cambia-esta-direccion@paso-firme.local`) que hay que sustituir por el correo real de la tienda.
