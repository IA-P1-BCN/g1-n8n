# Mapa BPMN del proceso de apartado (hoy vs automatizado)

> **US-20** ([issue #38](https://github.com/IA-P1-BCN/g1-n8n/issues/38)) · entregable 1 del enunciado.
> Vocabulario: [`GLOSSARY.md`](../../../GLOSSARY.md). Reglas del apartado: [`business-rules.md`](../business-rules.md).

Dos diagramas BPMN 2.0 (abrible en [bpmn.io](https://demo.bpmn.io), Miro o Excalidraw):

| Fichero | Qué dibuja |
|---|---|
| [`proceso-hoy.bpmn`](proceso-hoy.bpmn) | El proceso **actual**: libreta, Excel y calculadora; avisos del banco revisados a mano |
| [`proceso-automatizado.bpmn`](proceso-automatizado.bpmn) | El proceso **con n8n**: la app de la tienda y los flujos construidos (Receptor · Webhook tienda, Flujos 01, 02 y 08) |

## Qué cambia con n8n (resumen para la presentación)

| Hoy (a mano) | Con los flujos de n8n |
|---|---|
| Marisa apunta cada apartado en la **libreta** y calcula pendiente y plazo a 90 días con la **calculadora** | La **app** calcula pendiente y fecha límite al apartar (reglas del abono mín. 5 € y plazo 90 días se aplican solas) |
| El aviso del **banco** (Bizum/transferencia) se localiza a ojo en la libreta: nombres abreviados, pagos sin concepto… | El evento llega por webhook (`POST /webhook/tienda`) y son los datos de la app los que aparecen en el correo, sin recalcular nada |
| Cada abono se copia a mano al Excel y se recalcula lo pendiente | El **Flujo 02** envía el recibo (parcial o final cuando **liquidado**) en el momento del registro |
| Vencidos y cifras del día/mes se suman a mano: si se salta un día, un apartado **vence** sin que nadie lo vea | (Flujos 03 y 04, `apartado.vencido` y `venta.registrada`, son el siguiente paso: el Switch del Receptor ya las tiene preparadas) |
| Si algo falla (un correo no sale, un cobro se pierde) no hay rastro | El **Flujo 08** avisa a la tienda por email de cualquier fallo de un flujo (`errorWorkflow` en sus ajustes) |
| El cliente se entera de su apartado cuando Marisa lo llama | El **Flujo 01** manda la confirmación en segundos si hay email; si no, avisa a la tienda para llamar |

## Los mapas en Mermaid (se renderizan en GitHub)

Mismo contenido que los BPMN, en Mermaid para verlos sin salir del repo. **Cuando se cree o modifique un flujo de n8n, actualiza este bloque y el BPMN automatizado en la misma PR** (regla en [`AGENTS.md`](../../../AGENTS.md)).

### Proceso actual (a mano)

```mermaid
flowchart LR
  subgraph Cliente
    st(["Cliente quiere apartar un par"])
    pago["Paga el apartado y su abono (en tienda o Bizum/transferencia)"]
  end
  subgraph Marisa["Marisa · a mano"]
    lib["Apuntar en la libreta: cliente, producto, talla y abono (mín 5 €)"]
    calc["Calcular pendiente y fecha límite (90 días) con la calculadora"]
    avis["Avisar al cliente a mano (llamada o WhatsApp)"]
    local["Localizar el pago en la libreta y el Excel"]
    gv{"¿Coincide el pago?"}
    preg["Buscar y preguntar a mano (nombre abreviado, pago sin concepto…)"]
    exl["Apuntar el abono en el Excel y recalcular pendiente"]
    gc{"¿Pendiente = 0 €?"}
    ent["Entregar el par y liquidar el apartado"]
    lq(("Apartado liquidado"))
    diario(["Cada día"])
    repaso["Repasar vencimientos: apartados con más de 90 días"]
    venc["Deshacer el apartado: zapatos a la venta y vale de compra"]
    ev(("Apartado vencido · vale para el cliente"))
    cierre(["Fin del día / fin de mes"])
    dia["Sumar a mano las ventas y cobros del día"]
    mes["Sumar a mano la recaudación del mes"]
    cif(("Cifras del día y del mes (a mano)"))
  end
  st --> lib --> calc --> avis --> pago --> local --> gv
  gv -- Sí --> exl --> gc
  gv -- No --> preg -- "Revisa el pago otra vez" --> gv
  gc -- "Sí · liquidado" --> ent --> lq
  gc -- "No · espera el siguiente abono" --> local
  diario --> repaso --> venc --> ev
  cierre --> dia --> mes --> cif
```

### Proceso automatizado con n8n

```mermaid
flowchart LR
  subgraph Marisa["Marisa (dueña)"]
    regA["Registrar el apartado en la app (abono inicial ≥ 5 €)"]
    regB["Registrar el abono en la app"]
  end
  subgraph Cliente
    st(["Cliente quiere apartar un par"])
    pago["Paga en tienda, o Bizum/transferencia (aviso del banco)"]
  end
  subgraph App["App de la tienda"]
    guarda["Valida y guarda el apartado (activo, pendiente, fecha límite)"]
    wh["Avisa a n8n: POST /webhook/tienda — evento apartado.creado"]
    validaB["Valida el abono (no supera lo pendiente) y actualiza (parcial o liquidado)"]
    wh2["Avisa a n8n: POST abono.registrado"]
  end
  subgraph N8N
    recep["Receptor · Webhook tienda: Evento y datos + Repartir por evento"]
    falla(["Fallo de un flujo (SMTP u otro)"])
    f08["Flujo 08 · Aviso de fallo"]
    ef8(("Email de aviso a la tienda"))
    f01["Flujo 01 · Confirmación de apartado"]
    ge{"¿El cliente tiene email?"}
    mail["Email de confirmación (producto, importes, fecha límite)"]
    econf(("Cliente confirmado por email"))
    aviso["Email de aviso a la tienda (sin email)"]
    eaviso(("La tienda contacta al cliente"))
    f02["Flujo 02 · Recibo de cada abono"]
    gl{"¿El abono lo liquida?"}
    mfin["Email de recibo final (par listo para recoger)"]
    efin(("Recibo final enviado"))
    mpar["Email de recibo parcial (queda por abonar)"]
    epar(("Recibo parcial enviado"))
  end
  st --> regA --> guarda --> wh --> recep --> f01 --> ge
  ge -- Sí --> mail --> econf
  ge -- "No · sin email" --> aviso --> eaviso
  pago --> regB --> validaB --> wh2 --> recep
  recep --> f02 --> gl
  gl -- "Sí · liquidado" --> mfin --> efin
  gl -- "No · recibo parcial" --> mpar --> epar
  falla --> f08 --> ef8
```

> El Switch «Repartir por evento» también tiene salidas `venta.registrada` y `apartado.vencido`: aún sin conectar (US-03/US-04 pendientes). Los Bizum/transferencia se revisan a mano: el flujo de abonos a distancia queda pendiente (nivel medio).

## Criterios de la historia

- [x] 1. Proceso **actual** dibujado (libreta, Excel, calculadora, avisos del banco a mano) — `proceso-hoy.bpmn`.
- [x] 2. Proceso **automatizado** con los flujos construidos — `proceso-automatizado.bpmn`.
- [x] 3. Diagrama **versionado en docs/** (BPMN 2.0, editable en bpmn.io y exportable a Miro/Excalidraw desde el propio formato).
