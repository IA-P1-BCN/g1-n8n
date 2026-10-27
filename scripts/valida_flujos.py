#!/usr/bin/env python3
"""Valida los JSON de los flujos n8n de la carpeta workflows/.

Reglas que comprueba en cada fichero (cualquier fallo no pasa el CI):

1. JSON parseable y sin BOM.
2. Estructura n8n completa: `name` no vacío, `nodes` con al menos 1 nodo,
   `connections` como objeto y `settings.executionOrder` definido.
3. Cada nodo: `id` y `name` únicos, `type` con formato `paquete_tipoNodo`,
   `typeVersion` numérico y `parameters`/`position` bien formados.
4. El flujo tiene al menos un disparador (webhook o trigger de sub-workflow).
5. `connections`: todo nodo de origen/destino existe y los índices son válidos.
6. Expresiones `{{ ... }}` balanceadas dentro de los `parameters`.
7. `credentials` de cada nodo: {tipo: {id, name}}.

Uso:  python3 scripts/valida_flujos.py  [carpeta]
      (carpeta por defecto: workflows/)
"""

import glob
import json
import os
import re
import sys

RE_NODE_TYPE = re.compile(r"^(@[a-z0-9-]+/)?([a-z0-9-]+\.)[a-zA-Z0-9_.@\[\]]+$")
RE_TRIGGER_HINT = re.compile(r"(webhook|Trigger|TriggerNode|formTrigger|scheduleTrigger)$|[Tt]rigger$|\.webhook$")
RE_EXPR_OPEN = "{{"
RE_EXPR_CLOSE = "}}"

errores_totales = 0


def error(nombre_fichero, donde, texto):
    global errores_totales
    errores_totales += 1
    print(f"  ✗ {os.path.basename(nombre_fichero)} · {donde}: {texto}")


def validar_expressions(nombre_fichero, donde, valor):
    """Las expresiones `{{ ... }}` de n8n deben estar balanceadas."""
    if isinstance(valor, str):
        opens = valor.count(RE_EXPR_OPEN)
        closes = valor.count(RE_EXPR_CLOSE)
        if opens != closes:
            error(nombre_fichero, donde, f"expresión desbalanceada ({opens} '{{{{' vs {closes} '}}}}')")
        return
    if isinstance(valor, dict):
        for clave, elemento in valor.items():
            validar_expressions(nombre_fichero, f"{donde}.{clave}", elemento)
    elif isinstance(valor, list):
        for i, elemento in enumerate(valor):
            validar_expressions(nombre_fichero, f"{donde}[{i}]", elemento)


def validar_credentials(nombre_fichero, nodo):
    credenciales = nodo.get("credentials")
    if credenciales is None:
        return
    if not isinstance(credenciales, dict):
        error(nombre_fichero, f"nodo «{nodo.get('name')}»", "`credentials` no es un objeto")
        return
    for tipo, defi in credenciales.items():
        if not isinstance(defi, dict) or not defi.get("id") or not defi.get("name"):
            error(nombre_fichero, f"nodo «{nodo.get('name')}»", f"credencial `{tipo}` sin id/name")


def validar_flujo(nombre_fichero):
    ok_fichero = True

    # 1. JSON parseable
    try:
        with open(nombre_fichero, "rb") as descripto:
            contenido = descripto.read()
        if contenido.startswith(b"\xef\xbb\xbf"):
            error(nombre_fichero, "fichero", "BOM UTF-8 no permitido")
        flujo = json.loads(contenido.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as pe:
        error(nombre_fichero, "JSON", f"no parsea: {pe}")
        return

    if not isinstance(flujo, dict):
        error(nombre_fichero, "raíz", "el JSON raíz no es un objeto")
        return

    # 2. estructura n8n
    if not flujo.get("name"):
        error(nombre_fichero, "name", "falta o está vacío")
    nodes = flujo.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        error(nombre_fichero, "nodes", "falta o está vacío; un flujo necesita al menos 1 nodo")
        return
    if not isinstance(flujo.get("connections"), dict):
        error(nombre_fichero, "connections", "falta o no es un objeto")
        ok_fichero = False
    if not isinstance(flujo.get("settings"), dict) or "executionOrder" not in flujo.get("settings", {}):
        error(nombre_fichero, "settings.executionOrder", "falta (recomendado \"v1\")")
        ok_fichero = False

    # 3/4/6/7. nodos: unicidad, tipo, disparador, expressions, credenciales
    ids, names, triggers = set(), set(), 0
    for i, nodo in enumerate(nodes):
        donde = f"nodo[{i}]"
        if not isinstance(nodo, dict):
            error(nombre_fichero, donde, "no es un objeto")
            continue
        nombre_nodo = nodo.get("name")
        donde = f"nodo «{nombre_nodo}»" if nombre_nodo else donde

        node_id = nodo.get("id")
        if not node_id:
            error(nombre_fichero, donde, "sin `id`")
        elif node_id in ids:
            error(nombre_fichero, donde, f"`id` duplicado: {node_id}")
        ids.add(node_id)

        if not nombre_nodo:
            error(nombre_fichero, donde, "sin `name`")
        elif nombre_nodo in names:
            error(nombre_fichero, donde, f"`name` duplicado: {nombre_nodo}")
        names.add(nombre_nodo)

        tipo = nodo.get("type", "")
        if not tipo or not RE_NODE_TYPE.match(tipo):
            error(nombre_fichero, donde, f"`type` con formato inválido: «{tipo}»")
        else:
            if RE_TRIGGER_HINT.search(tipo):
                triggers += 1
        tv = nodo.get("typeVersion")
        if not isinstance(tv, (int, float)) or tv <= 0:
            error(nombre_fichero, donde, f"`typeVersion` inválido: {tv!r}")
        if not isinstance(nodo.get("parameters"), dict):
            error(nombre_fichero, donde, "`parameters` falta o no es objeto")
        pos = nodo.get("position")
        if not (isinstance(pos, list) and len(pos) == 2 and all(isinstance(p, (int, float)) for p in pos)):
            error(nombre_fichero, donde, f"`position` inválido: {pos!r}")

        validar_expressions(nombre_fichero, donde + ".parameters", nodo.get("parameters", {}))
        validar_credentials(nombre_fichero, nodo)

    if triggers == 0:
        error(nombre_fichero, "disparador", "el flujo no tiene ningún trigger (webhook/executeWorkflowTrigger/...)")

    # 5. connections: referencias existentes e índices válidos
    total_nodos = len(nodes)
    conexiones = flujo.get("connections")
    if isinstance(conexiones, dict):
        for origen, salidas in conexiones.items():
            if origen not in names:
                error(nombre_fichero, "connections", f"el origen «{origen}» no existe en nodos")
                continue
            if not isinstance(salidas, dict):
                error(nombre_fichero, f"connections.{origen}", "no es un objeto")
                continue
            for tipo_salida, puertos in salidas.items():
                if tipo_salida != "main":
                    continue
                if not isinstance(puertos, list):
                    error(nombre_fichero, f"connections.{origen}", f"salida `{tipo_salida}` no es lista")
                    continue
                for indice, puertos_mismo in enumerate(puertos):
                    if not isinstance(puertos_mismo, list):
                        continue
                    for conexion in puertos_mismo:
                        destino = conexion.get("node") if isinstance(conexion, dict) else None
                        if destino not in names:
                            error(
                                nombre_fichero,
                                f"connections.{origen}[{indice}]",
                                f"el destino «{destino}» no existe en nodos",
                            )
                        if isinstance(conexion, dict):
                            idx = conexion.get("index")
                            if not isinstance(idx, int) or idx < 0:
                                error(nombre_fichero, f"connections.{origen}[{indice}]", "index debe ser entero ≥ 0")

    if ok_fichero and errores_totales == 0:
        print(f"  ✓ {os.path.basename(nombre_fichero)} · «{flujo.get('name')}» · {total_nodos} nodos OK")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    carpeta = sys.argv[1] if len(sys.argv) > 1 else "workflows"
    ficheros = sorted(glob.glob(os.path.join(carpeta, "*.json")))
    if not ficheros:
        print(f"✗ No hay ficheros JSON en {carpeta}/ — nada que validar.")
        return 1
    print(f"Validando {len(ficheros)} fichero(s) en {carpeta}/:")
    for fichero in ficheros:
        validar_flujo(fichero)
    if errores_totales:
        print(f"\n✗ VALIDACIÓN FALLIDA: {errores_totales} error(es).")
        return 1
    print("\n✓ VALIDACIÓN CORRECTA.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
