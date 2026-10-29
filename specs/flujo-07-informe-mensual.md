# Spec SDD · Flujo 07 · Informe mensual

> **Historia**: US-08 ([issue #57](https://github.com/IA-P1-BCN/g1-n8n/issues/57)) · **Nivel**: 🟡 Medio · **Vocabulario**: [`GLOSSARY.md`](../GLOSSARY.md)

## Disparador

Flujo de ejecución periódica programada y manual:

1. **Programado** (`Schedule Trigger`): Se dispara automáticamente a las 08:00 del día 1 de cada mes (`0 8 1 * *`, zona horaria `Europe/Madrid`).
2. **Manual** (`Manual Trigger`): Permite ejecutar el flujo a demanda desde la interfaz de n8n o mediante el CLI (`n8n execute --id=pFlujo07InformeMensual`) para pruebas de aceptación y demostraciones.

## Entradas

Consultas a la API de la app de la tienda (`http://tienda:8000`, cabecera `X-API-Key: {{ $env.API_KEY }}`):

- `GET /api/ventas?desde={desde}&hasta={hasta}`: Ventas cobradas dentro del rango del mes anterior.
- `GET /api/abonos`: Abonos registrados en el sistema. Se filtran aquellos cuya fecha corresponde al mes del informe (`recaudacion_abonos`) y se analizan las fechas de último abono para identificar liquidaciones.
- `GET /api/apartados`: Catálogo completo de apartados. Se utiliza para:
  - Calcular el **Total pendiente de cobro**: suma del campo `pendiente` de todos los apartados con `estado == 'activo'`.
  - Contabilizar los **Apartados nuevos**: aquellos con `fecha` de creación en el mes del informe.
  - Contabilizar los **Apartados liquidados**: aquellos con `estado == 'liquidado'` cuya fecha de liquidación (último abono) cayó en el mes del informe.
- `GET /api/vales`: Vales de compra generados. Permite identificar los **Apartados vencidos**: aquellos con fecha de emisión del vale en el mes del informe.

### Determinación del periodo

- Por defecto, calcula automáticamente el primer y último día del mes inmediatamente anterior al momento de ejecución (ej. si se ejecuta el 1 de noviembre de 2026, el rango es `2026-10-01` a `2026-10-31`).
- Admite parámetros opcionales `{ "desde": "AAAA-MM-DD", "hasta": "AAAA-MM-DD", "periodo_texto": "..." }` en la invocación manual para permitir pruebas e2e y regeneración de informes de meses pasados.

## Salidas

Envío de un correo electrónico a Marisa (`toEmail: cambia-esta-direccion@paso-firme.local`):

- **Remitente**: `n8n@paso-firme.local` (mediante credencial `SMTP Mailpit (pruebas)`).
- **Asunto**: `📊 Informe mensual de {periodo_texto} · Zapatería Paso Firme`
- **Cuerpo (HTML)** con tabla formateada y clara:
  1. **Recaudación mensual del mes anterior**:
     - *Ventas directas*: Total cobrado en ventas sin apartado en el mes (`{total_ventas} €`).
     - *Abonos de apartados*: Total cobrado en abonos (iniciales y parciales) en el mes (`{total_abonos} €`).
     - *Recaudación total*: Suma de ventas y abonos (`{total_recaudacion} €`).
  2. **Estado de apartados y cartera**:
     - *Total pendiente de cobro*: Lo que el barrio le debe a Marisa (suma de pendientes de apartados activos, `{total_pendiente} €`).
     - *Apartados nuevos del mes*: Cantidad de apartados iniciados en el mes.
     - *Apartados liquidados del mes*: Cantidad de apartados completamente saldados en el mes.
     - *Apartados vencidos del mes*: Cantidad de apartados vencidos convertidos en vales en el mes.

## Casos de error

| Caso | Comportamiento |
|---|---|
| La API de la tienda no responde o devuelve 4xx/5xx | El flujo falla inmediatamente; `errorWorkflow` (**Flujo 08 · Aviso de fallo**) captura el error y avisa a Marisa |
| Mes sin ventas o sin abonos (0 registros) | El flujo procesa listas vacías sin fallar, calculando importes en `0.00 €` y conteos en `0` |
| Fallo en el servidor de correo (SMTP) | El nodo de correo falla y se dispara la alerta técnica en `errorWorkflow` |

## Criterios de aceptación

Correspondientes a la historia padre US-08:

- **Escenario A — Informe del día 1**:
  - 1. Ejecutar el flujo el día 1 de mes (o forzarlo manualmente con un periodo).
  - 2. Comprobar que el correo incluye la recaudación del mes anterior con ventas y abonos por separado.
  - 3. Comprobar que incluye el total pendiente de cobro y los apartados nuevos, liquidados y vencidos del mes.
  - 4. Verificar que los importes coinciden exactamente con los datos de la app.

## Notas de arquitectura

- **Identificador de flujo**: `pFlujo07InformeMensual`.
- **Fichero**: `workflows/flujo-07-informe-mensual.json`.
- **Credenciales**: Utiliza la credencial preconfigurada `SMTP Mailpit (pruebas)` para el nodo de correo. La clave de la API de la tienda se inyecta desde `$env.API_KEY`.
- **Error Workflow**: El flujo tiene configurado en sus `settings` `"errorWorkflow": "pFlujo08AvisoFallo"` para trazabilidad total de incidencias.
