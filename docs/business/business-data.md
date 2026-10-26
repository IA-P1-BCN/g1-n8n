## 🗂️ Datos de partida

En [`data/`](data/) tenéis una muestra del Excel actual de la tienda, tal y como lo lleva Marisa:

- [`excel_actual_apartados.csv`](data/excel_actual_apartados.csv): apartados y abonos mezclados en la misma hoja.
- [`excel_actual_ventas.csv`](data/excel_actual_ventas.csv): ventas del día y el total mensual sumado a mano.

Son datos **reales del día a día**, con lo que eso implica: fechas en distintos formatos, nombres escritos de varias maneras, importes con el símbolo €, teléfonos que faltan, un abono inicial por debajo del mínimo y totales calculados a mano. Sirven para el flujo de **migración** (nivel medio): limpiarlos y cargarlos en la app por API.

En [`data/correos/`](data/correos/) tenéis **avisos del banco** como los que recibe Marisa cuando un cliente paga por Bizum o transferencia. Sirven para el flujo de **abonos a distancia** (nivel esencial) y están pensados para los apartados de ejemplo de la app. Hay casos fáciles y casos trampa:

| Correo | Qué tiene que pasar |
|---|---|
| `01_bizum_carmen`, `09_bizum_silvia` | El nombre coincide con un único apartado activo: se registra el abono |
| `02_bizum_jorge` | El ordenante está abreviado, pero el concepto trae el nº de apartado |
| `03_transferencia_lucia` | Paga justo lo que falta: el apartado queda **liquidado** |
| `04_bizum_laura` | Paga **más** de lo pendiente: la app lo rechaza y hay que avisar a Marisa |
| `05_bizum_romero` | Solo apellido e inicial y sin concepto: hay que preguntar a Marisa antes de registrar nada |
| `06_bizum_paula` | El apartado está **fuera de plazo**: no se puede abonar, hay que avisar a Marisa |
| `07_transferencia_desconocido` | No coincide con ningún cliente: preguntar a Marisa |
| `08_publicidad_banco` | No es un pago: se ignora |

Para probarlos, enviad estos correos (asunto y cuerpo) a la cuenta que lea n8n. Mientras desarrolláis, también podéis pegar el texto en un formulario de n8n (Form Trigger) para no depender del correo.
