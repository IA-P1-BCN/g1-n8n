# Spec SDD · Flujo 02 · Recibo de cada abono

> **Historia**: US-02 ([issue #6](https://github.com/IA-P1-BCN/g1-n8n/issues/6)) · **Nivel**: 🟢 Esencial · **Vocabulario**: [`GLOSSARY.md`](../GLOSSARY.md)

## Disparador

Sub-workflow, llamado por el **Receptor de eventos** a través de la salida `abono.registrado` de su Switch cuando la app notifica un abono registrado:

```json
{ "evento": "abono.registrado", "datos": { "id": 25, "fecha": "2026-10-20", "cliente": "Carmen Ruiz", "email": "…", "telefono": "…", "producto": "Botín piel marrón", "talla": "38", "precio": 89.9, "abonado": 40.0, "pendiente": 49.9, "fecha_limite": "2027-01-18", "estado": "activo", "importe": 30.0 } }
```

La app envía el evento en segundo plano al registrar el abono (`services/n8n.py`) con **el apartado ya actualizado** y el `importe` de este abono. El receptor no toca `datos`; este flujo consume su salida tal cual.

## Entradas

- `datos.*`: los campos del evento `abono.registrado` (**no se recalcula nada**: los importes que llegan son los que se muestran, igual que en la app). `datos.importe` es lo pagado en este abono; `datos.abonado` el total ya abonado; `datos.pendiente` lo que queda; `datos.estado` el estado del apartado tras el abono (`activo` si queda pendiente, `liquidado` si se liquidó).

## Salidas

1. **Cliente con email · abono parcial** (Escenario A, `datos.estado` = `activo`) → recibo (HTML) con: importe de este abono, total ya abonado, pendiente y fecha límite.
   - Asunto: `👟 Recibo de tu abono · Zapatería Paso Firme`
   - Cuerpo: `datos.importe` € hoy, `datos.abonado` € ya abonado en total, `datos.pendiente` € por pagar, límite `datos.fecha_limite`.
2. **Cliente con email · abono que liquida** (Escenario B, `datos.estado` = `liquidado`) → recibo con las mismas cifras y aviso de que ya puede recoger sus zapatos.
   - Asunto: `👟 Último abono recibido · ¡puedes recoger tus zapatos!`
   - Cuerpo: cifras (`pendiente` 0 €) + mensaje «ya puedes recoger tus zapatos» + vale implícito: ninguna rama modifica la app.
3. **Cliente sin email** → no se envía nada al cliente; **aviso a la tienda** (HTML) para que apunte el recibo y lo entregue en persona. `datos.email` nulo/vacío → rama `false` del primer IF.
4. Ninguna rama modifica la app (constatación).

## Casos de error

| Caso | Comportamiento |
|---|---|
| `datos.email` vacío | Rama `false` → aviso a la tienda (el flujo **no** falla) |
| `datos.estado` distinto de `activo`/`liquidado` | No debería llegar (la app solo registra abonos en activos): cae del segundo IF por `activo` sin enviar nada |
| Error de envío (SMTP/API) | El flujo falla → lo captura el futuro Error Workflow (US-05) |
| Evento equivocado (`apartado.creado`, ...) | No se ejecuta nada (el receptor solo llama a este flujo con `abono.registrado`) |

## Criterios de aceptación

Los de la issue (US-02): de ahí a la prueba de usuario (Escenario A: recibo con el importe pagado y lo que queda, coincidiendo con la app; Escenario B: al liquidar, el mensaje avisa de que ya puede recoger sus zapatos).

## Notas de arquitectura

- Mismo patrón que el Flujo 01 (US-01): **IF por email + IF por estado**, dos nodos *Send Email* hacia el cliente y uno de aviso a la tienda.
- **Envío de correo**: nodos *Send Email* (SMTP) con la credencial `SMTP Mailpit (pruebas)` → durante el desarrollo los correos se ven en el buzón de pruebas Mailpit. Para **producción** basta asignar a los nodos una credencial SMTP real (u OAuth2 de Gmail) con los mismos campos.
- El Receptor de eventos conecta la salida `abono.registrado` de su Switch a un Execute Workflow que llama a este flujo (una rama = un sub-workflow, guía de la app §6).
- Los correos de prueba van con remitente `n8n@paso-firme.local`; el aviso a la tienda tiene un `toEmail` de prueba (`cambia-esta-direccion@paso-firme.local`) que hay que sustituir por el correo real de la tienda.
