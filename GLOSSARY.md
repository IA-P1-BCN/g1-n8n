# Zapatería Paso Firme · Sistema de apartados

Glosario del dominio del proyecto de automatización con n8n de la zapatería Paso Firme. Es la fuente de verdad del vocabulario: úsalo tal cual en issues, specs, flujos y mensajes a clientes.

## Personas

**Marisa**: La dueña de la tienda. Destinataria de los cierres, informes y avisos del negocio.
_Avoid_: propietaria, jefa

**Dependienta**: La empleada que atiende la tienda y registra apartados, abonos y ventas en la app.
_Avoid_: vendedora

**Cliente**: Persona que compra o aparta zapatos. Recibe confirmaciones, recibos y recordatorios.
_Avoid_: comprador, usuario

## El apartado

**Apartar**: Reservar un producto dejando un abono inicial y pagarlo a plazos hasta llevárselo.
_Avoid_: reservar, encargar

**Producto**: Un modelo de zapato en una talla concreta. Cada apartado corresponde a exactamente un producto.
_Avoid_: artículo, referencia

**Apartado**: La reserva de un producto que el cliente paga a plazos. Tiene precio, plazo y estado, y vive en la app (ya no en la libreta).
_Avoid_: reserva, pedido, layaway

**Plazo**: Los 90 días desde la fecha del apartado para liquidarlo por completo.

**Abono**: Pago parcial de un apartado, de cualquier importe, sin superar lo pendiente.
_Avoid_: pago, entrega a cuenta, ingreso

**Abono inicial**: El primer abono, mínimo de 5 €, hecho en el momento de apartar. Cuenta como cobro del día.
_Avoid_: entrada, señal, depósito

**Pendiente**: Lo que falta por pagar de un apartado; al llegar a 0 € el apartado queda liquidado.
_Avoid_: saldo, deuda, resto

## Estados de un apartado

**Activo**: Estado de un apartado vigente: admite abonos. Es el único estado que los admite.

**Liquidado**: Estado final de un apartado pagado por completo. El cliente puede recoger sus zapatos.
_Avoid_: pagado, cerrado

**Vencido**: Estado final de un apartado cuyo plazo terminó sin liquidarse: los zapatos vuelven a la venta y lo abonado se convierte en un vale (nunca se devuelve en efectivo).
_Avoid_: caducado, expirado, anulado

**Vencer**: Pasar un apartado activo fuera de plazo al estado vencido, generando su vale.

**Vale**: Lo abonado en un apartado vencido, convertido en un vale de compra canjeable en la tienda. Tiene código e importe.
_Avoid_: bono, cupón, cheque

**Liquidación**: El momento en que un abono deja el pendiente en 0 €.

## Ventas y caja

**Venta**: Compra directa al momento, sin apartado, registrada en la app.
_Avoid_: venta directa (término largo innecesario), cobro, ticket

**Ventas del día**: Cifra del día: ventas + abonos cobrados ese día (el abono inicial incluido).

**Recaudación mensual**: Todo lo cobrado en el mes, separando ventas y abonos de apartados.

**Cierre diario**: Resumen nocturno de lo cobrado en el día, desglosado por forma de pago.
_Avoid_: arqueo, cuadre de caja

**Total pendiente de cobro**: Suma del pendiente de todos los apartados activos: lo que el barrio le debe a Marisa.
_Avoid_: deuda total, saldo pendiente

**Forma de pago**: Cómo se paga un abono o una venta: efectivo, tarjeta o bizum.

**Bizum**: Pago móvil con el que los clientes abonan desde casa; llega como aviso del banco al correo de Marisa.
