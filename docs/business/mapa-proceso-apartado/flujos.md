# Flujos del proceso · hoy vs automatizado

Los dos mapas del negocio en **Mermaid**: GitHub los pinta al abrir esta página, sin arrastrar ficheros.
Las reglas de negocio (Abono, Vale, Liquidado, plazo de 90 días…) están en [`docs/business/business-rules.md`](../business-rules.md).

## Proceso actual (íntegramente a mano)

```mermaid
flowchart LR
    subgraph LaneCliente["Lane · Cliente"]
        c1["Deja el zapato y pide el apartado"]
        c2["Paga el Abono inicial y los Abonos parciales"]
        c3["Recoge la mercancía"]
        c4["Recibe la llamada o el aviso del vencido"]
    end

    subgraph LaneMarisa["Lane · Marisa: papel, libreta y calculadora"]
        m1["Abre el Apartado en la libreta: Abono inicial de 5 € o más, plazo de 90 días"]
        m2["Anota cada Abono a mano"]
        m3{"¿Está Liquidado?"}
        m4["Cada día repasa las filas vencidas y avisa a mano"]
        m5["Avisos del banco: localiza y reconcilia los recibos a mano"]
        m6["Pasa los datos al Excel y los recalcula"]
        m7["Cierra la caja: suma a mano las cifras del día y del mes"]
        m8["Entrega la mercancía y archiva el Vale"]
    end

    c1 --> m1
    c2 --> m2
    m1 --> m6
    m2 --> m3
    m3 -- "Sí: Abonos completos" --> m8
    m3 -- "No: plazo cumplido" --> m4
    m4 --> c4
    c4 --> c2
    m8 --> c3
    m5 --> m6
    m6 --> m7
```

Papel, post-its y memoria: quien no esté ese día no lo ve, y el Excel solo es fiel si Marisa lo actualiza a mano.

## Proceso automatizado con n8n

```mermaid
flowchart LR
    subgraph LaneCliente["Lane · Cliente"]
        c1["Deja el zapato y pide el apartado"]
        c2["Paga los Abonos"]
        c3["Recoge la mercancía"]
        c4["Recibe los correos de la tienda"]
    end

    subgraph LaneMarisa["Lane · Marisa"]
        m1["Registra el Apartado y cada Abono en la app"]
        m2["Descarga el Excel a mano"]
        m3["Entrega la mercancía y archiva el Vale (a mano)"]
        m4["Recibe el Informe mensual por correo el día 1"]
    end

    subgraph LaneApp["Lane · App de la tienda"]
        a1["Valida y guarda el Apartado, el Abono y la Venta"]
        a2["Avisa a n8n: POST /webhook/tienda con el evento y sus datos"]
        a3["Deja el Excel listo para descargar"]
    end

    subgraph LaneN8N["Lane · n8n"]
        n1["Receptor · Webhook tienda"]
        n2["Evento y datos"]
        n3{"Repartir por evento"}
        f1["Flujo 01 · Confirmación de apartado"]
        f1c{"¿El cliente tiene email?"}
        f1m["Enviar correo «Apartado confirmado»"]
        f2["Flujo 02 · Recibo de cada abono"]
        f2c{"¿El Abono lo liquida?"}
        f2m["Enviar correo «Recibo de tu Abono»"]
        f2u["Enviar correo «Último Abono recibido»"]
        f4["Flujo 04 · cierre diario (rama venta.registrada, reservada a US-09, sin conectar)"]
        f6["Flujo 06 · Recordatorios y vencimientos (programado cada mañana)"]
        f6m["Enviar correo «Tu apartado vence en 7 días» / «Mañana vence tu apartado»"]
        f6v["Vencer apartado fuera de plazo (POST /api/apartados/{id}/vencer)"]
        f6vc["Enviar correo «Tu vale por apartado vencido» al cliente"]
        f6vm["Enviar correo «Zapatos que vuelven a la venta» a Marisa"]
        fx["Ramaapartado.vencido / evento desconocido: queda visible en Executions"]
        nm["Se registra y se acabó: sin correo"]
        f7["Flujo 07 · Informe mensual (programado día 1)"]
        f7m["Enviar correo «Informe mensual» a Marisa"]
        f8["Flujo 08 · Aviso de fallo a Marisa"]
        f9["Flujo 09 · Migración del Excel antiguo (data/*.csv → API sin duplicados)"]
        f9m["Enviar correo «Informe de migración del Excel» (casos dudosos)"]
    end

    c1 --> m1
    c2 --> m1
    m1 --> a1
    a1 --> a2
    a2 --> n1
    n1 --> n2
    n2 --> n3
    n3 -- "apartado.creado" --> f1
    f1 --> f1c
    f1c -- "Sí: tiene email" --> f1m
    f1m --> c4
    f1c -- "No: se registra y se acabó" --> nm
    n3 -- "abono.registrado" --> f2
    f2 --> f2c
    f2c -- "No: Abono parcial" --> f2m
    f2m --> c4
    f2c -- "Sí: liquida" --> f2u
    f2u --> c4
    n3 -- "venta.registrada" --> f4
    n3 -- "apartado.vencido" --> fx
    a1 -- "GET /api/apartados?estado=activo" --> f6
    f6 -- "vence en 7d o 1d" --> f6m
    f6m --> c4
    f6 -- "fecha_limite < hoy" --> f6v
    f6v --> a1
    f6v --> f6vc
    f6vc --> c4
    f6v --> f6vm
    f2u --> m3
    m3 --> c3
    a3 --> m2
    f1 -. "si un flujo falla" .-> f8
    f2 -.-> f8
    f6 -.-> f8
    f7 -.-> f8
    f7 --> f7m
    f7m --> m4
    f9 -.-> f8
    f9 -- "POST /api/apartados · abonos · ventas" --> a1
    f9 -- "casos dudosos (ej. abono inicial < 5 €)" --> f9m
    n3 -- "Cualquier otro evento" --> fx
```

Bizum y transferencia se revisan aún a mano hasta el flujo de Abonos a distancia; el **Flujo 06** envía cada mañana los recordatorios a 7 y 1 día y vence por API los apartados fuera de plazo (entregando el Vale al cliente y avisando a Marisa de los zapatos que vuelven a la venta); el informe mensual (**Flujo 07**) se ejecuta el día 1 de cada mes; la migración puntual de las hojas antiguas (`data/*.csv`) corre en el **Flujo 09**; el aviso de fallo (**Flujo 08**) entra con `errorWorkflow`: todos los flujos lo apuntan en sus ajustes.
