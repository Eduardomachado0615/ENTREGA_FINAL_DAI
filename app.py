from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from flask import Flask, jsonify, request
from database import obtener_conexion, crear_tablas

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False


RECURSOS: dict[str, dict[str, Any]] = {
    "clientes": {
        "tabla": "cliente", "pk": "cliente_id",
        "campos": ["nombre", "apellidos", "razon_social", "ruc", "telefono", "email"],
        "requeridos": ["nombre", "apellidos"], "booleanos": []
    },
    "contactos": {
        "tabla": "contacto", "pk": "contacto_id",
        "campos": ["cliente_id", "nombre_completo", "cargo",
                   "responsable_default", "responsable_backup"],
        "requeridos": ["cliente_id", "nombre_completo"],
        "booleanos": ["responsable_default", "responsable_backup"]
    },
    "direcciones": {
        "tabla": "direccion", "pk": "direccion_id",
        "campos": ["cliente_id", "contacto_id", "nombre_ubicacion",
                   "calle", "ciudad", "codigo_postal"],
        "requeridos": ["cliente_id", "nombre_ubicacion", "calle", "ciudad"],
        "booleanos": []
    },
    "eventos": {
        "tabla": "evento", "pk": "evento_id",
        "campos": ["cliente_id", "contacto_id", "direccion_id", "fecha_evento",
                   "hora_inicio", "hora_fin", "numero_asistentes",
                   "incluye_bebidas", "tipo_actividad", "tipo_servicio",
                   "presentacion", "estado"],
        "requeridos": ["cliente_id", "fecha_evento", "hora_inicio",
                       "hora_fin", "numero_asistentes"],
        "booleanos": ["incluye_bebidas"]
    },
    "menus": {
        "tabla": "menu", "pk": "menu_id",
        "campos": ["nombre", "descripcion_general", "precio_base_persona"],
        "requeridos": ["nombre", "precio_base_persona"], "booleanos": []
    },
    "items-menu": {
        "tabla": "item_menu", "pk": "item_id",
        "campos": ["menu_id", "nombre_completo", "descripcion", "categoria"],
        "requeridos": ["menu_id", "nombre_completo"], "booleanos": []
    },
    "empleados": {
        "tabla": "empleado", "pk": "responsable_id",
        "campos": ["nombre_completo", "cargo", "email", "telefono"],
        "requeridos": ["nombre_completo", "cargo"], "booleanos": []
    },
    "ordenes-servicio": {
        "tabla": "orden_servicio", "pk": "orden_id",
        "campos": ["evento_id", "responsable_id", "fecha_solicitud", "estado",
                   "hora_entrega", "hora_montaje", "requerimiento_personal",
                   "monto_total"],
        "requeridos": ["evento_id", "responsable_id", "fecha_solicitud", "monto_total"],
        "booleanos": ["requerimiento_personal"]
    },
    "pagos": {
        "tabla": "pago", "pk": "pago_id",
        "campos": ["orden_id", "fecha_pago", "monto", "metodo_pago", "tipo_pago"],
        "requeridos": ["orden_id", "monto", "metodo_pago", "tipo_pago"],
        "booleanos": []
    },
    "facturas": {
        "tabla": "factura", "pk": "factura_id",
        "campos": ["orden_id", "numero_factura", "fecha_emision",
                   "servicio_conforme", "estado_cofi"],
        "requeridos": ["orden_id", "numero_factura"],
        "booleanos": ["servicio_conforme"]
    },
    "controles-calidad": {
        "tabla": "control_calidad", "pk": "control_id",
        "campos": ["orden_id", "uso_manipulacion", "uso_mascarilla",
                   "uso_guantes", "red_cabello", "observaciones_sanitarias"],
        "requeridos": ["orden_id"],
        "booleanos": ["uso_mascarilla", "uso_guantes", "red_cabello"]
    },
    "conformidades": {
        "tabla": "conformidad", "pk": "conformidad_id",
        "campos": ["orden_id", "fecha_conformidad", "observacion_cliente",
                   "servicio_conforme", "firma_cliente", "firma_sazonera"],
        "requeridos": ["orden_id", "fecha_conformidad"],
        "booleanos": ["servicio_conforme"]
    }
}


def error(mensaje: str, codigo: int = 400):
    return jsonify({"ok": False, "error": mensaje}), codigo


def a_booleano(valor: Any) -> int:
    if isinstance(valor, bool):
        return int(valor)
    if valor in (0, 1, "0", "1"):
        return int(valor)
    if isinstance(valor, str):
        valor = valor.strip().lower()
        if valor in ("true", "si", "sí", "yes"):
            return 1
        if valor in ("false", "no"):
            return 0
    raise ValueError("Los booleanos deben enviarse como true/false o 1/0.")


def serializar(fila: sqlite3.Row | None, booleanos: list[str] | None = None):
    if fila is None:
        return None
    datos = dict(fila)
    for campo in booleanos or []:
        if datos.get(campo) is not None:
            datos[campo] = bool(datos[campo])
    return datos


def preparar(config: dict[str, Any], datos: dict[str, Any]) -> dict[str, Any]:
    desconocidos = set(datos) - set(config["campos"])
    if desconocidos:
        raise ValueError("Campos no permitidos: " + ", ".join(sorted(desconocidos)))
    resultado = {}
    for campo, valor in datos.items():
        resultado[campo] = a_booleano(valor) if campo in config["booleanos"] else valor
    return resultado


def obtener(resource: str, record_id: int):
    config = RECURSOS[resource]
    con = obtener_conexion()
    fila = con.execute(
        f"SELECT * FROM {config['tabla']} WHERE {config['pk']} = ?",
        (record_id,)
    ).fetchone()
    con.close()
    return serializar(fila, config["booleanos"])


def respuesta_integridad(exc: sqlite3.IntegrityError):
    texto = str(exc)
    if "FOREIGN KEY" in texto:
        return error("La llave foránea indicada no existe o el registro está siendo utilizado.", 409)
    if "UNIQUE" in texto:
        return error("Ya existe un registro con ese valor único.", 409)
    if "CHECK" in texto:
        return error("Un valor no cumple las reglas de validación.", 400)
    if "NOT NULL" in texto:
        return error("Falta un campo obligatorio.", 400)
    return error(f"Error de integridad: {texto}", 409)


@app.get("/")
def inicio():
    return jsonify({
        "ok": True,
        "mensaje": "API del Sistema de Eventos funcionando",
        "documentacion": "/api"
    })


@app.get("/api")
def documentacion():
    return jsonify({
        "recursos": list(RECURSOS),
        "crud": {
            "listar": "GET /api/<recurso>",
            "obtener": "GET /api/<recurso>/<id>",
            "crear": "POST /api/<recurso>",
            "actualizar": "PUT o PATCH /api/<recurso>/<id>",
            "eliminar": "DELETE /api/<recurso>/<id>"
        },
        "relacion_evento_menu": [
            "GET /api/eventos-menu",
            "POST /api/eventos-menu",
            "GET|PUT|DELETE /api/eventos-menu/<evento_id>/<menu_id>"
        ],
        "acciones": [
            "GET /api/clientes/<id>/detalle",
            "GET /api/eventos/<id>/detalle",
            "POST /api/eventos/<id>/programar",
            "POST /api/eventos/<id>/cancelar",
            "GET /api/ordenes-servicio/<id>/detalle",
            "POST /api/ordenes-servicio/<id>/procesar-pago",
            "POST /api/ordenes-servicio/<id>/generar-factura"
        ]
    })


@app.route("/api/<resource>", methods=["GET", "POST"])
def coleccion(resource: str):
    if resource not in RECURSOS:
        return error("Recurso no encontrado.", 404)
    config = RECURSOS[resource]

    if request.method == "GET":
        try:
            limite = min(max(int(request.args.get("limit", 100)), 1), 200)
            offset = max(int(request.args.get("offset", 0)), 0)
        except ValueError:
            return error("limit y offset deben ser enteros.")

        filtros, valores = [], []
        permitidos = set(config["campos"] + [config["pk"]])
        for clave, valor in request.args.items():
            if clave in ("limit", "offset"):
                continue
            if clave not in permitidos:
                return error(f"No se puede filtrar por '{clave}'.")
            filtros.append(f"{clave} = ?")
            valores.append(valor)

        sql = f"SELECT * FROM {config['tabla']}"
        if filtros:
            sql += " WHERE " + " AND ".join(filtros)
        sql += f" ORDER BY {config['pk']} DESC LIMIT ? OFFSET ?"
        valores += [limite, offset]

        con = obtener_conexion()
        filas = con.execute(sql, valores).fetchall()
        con.close()
        return jsonify({
            "ok": True,
            "cantidad": len(filas),
            "datos": [serializar(f, config["booleanos"]) for f in filas]
        })

    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return error("Debe enviar un JSON válido.")

    faltantes = [c for c in config["requeridos"] if datos.get(c) in (None, "")]
    if faltantes:
        return error("Faltan campos obligatorios: " + ", ".join(faltantes))

    try:
        datos = preparar(config, datos)
    except ValueError as exc:
        return error(str(exc))

    if resource == "eventos":
        if datos["hora_fin"] <= datos["hora_inicio"]:
            return error("hora_fin debe ser posterior a hora_inicio.")

    columnas = ", ".join(datos)
    signos = ", ".join("?" for _ in datos)
    con = obtener_conexion()
    try:
        cur = con.execute(
            f"INSERT INTO {config['tabla']} ({columnas}) VALUES ({signos})",
            list(datos.values())
        )
        con.commit()
        nuevo_id = cur.lastrowid
    except sqlite3.IntegrityError as exc:
        con.rollback()
        con.close()
        return respuesta_integridad(exc)
    con.close()

    return jsonify({
        "ok": True,
        "mensaje": "Registro creado.",
        "datos": obtener(resource, nuevo_id)
    }), 201


@app.route("/api/<resource>/<int:record_id>",
           methods=["GET", "PUT", "PATCH", "DELETE"])
def elemento(resource: str, record_id: int):
    if resource not in RECURSOS:
        return error("Recurso no encontrado.", 404)
    config = RECURSOS[resource]
    existente = obtener(resource, record_id)
    if existente is None:
        return error("Registro no encontrado.", 404)

    if request.method == "GET":
        return jsonify({"ok": True, "datos": existente})

    if request.method == "DELETE":
        con = obtener_conexion()
        try:
            con.execute(
                f"DELETE FROM {config['tabla']} WHERE {config['pk']} = ?",
                (record_id,)
            )
            con.commit()
        except sqlite3.IntegrityError as exc:
            con.rollback()
            con.close()
            return respuesta_integridad(exc)
        con.close()
        return jsonify({"ok": True, "mensaje": "Registro eliminado."})

    datos = request.get_json(silent=True)
    if not isinstance(datos, dict) or not datos:
        return error("Debe enviar un JSON con al menos un campo.")

    try:
        datos = preparar(config, datos)
    except ValueError as exc:
        return error(str(exc))

    if resource == "eventos":
        inicio = datos.get("hora_inicio", existente["hora_inicio"])
        fin = datos.get("hora_fin", existente["hora_fin"])
        if fin <= inicio:
            return error("hora_fin debe ser posterior a hora_inicio.")

    asignaciones = ", ".join(f"{campo} = ?" for campo in datos)
    con = obtener_conexion()
    try:
        con.execute(
            f"UPDATE {config['tabla']} SET {asignaciones} WHERE {config['pk']} = ?",
            list(datos.values()) + [record_id]
        )
        con.commit()
    except sqlite3.IntegrityError as exc:
        con.rollback()
        con.close()
        return respuesta_integridad(exc)
    con.close()

    return jsonify({
        "ok": True,
        "mensaje": "Registro actualizado.",
        "datos": obtener(resource, record_id)
    })


@app.route("/api/eventos-menu", methods=["GET", "POST"])
def eventos_menu():
    con = obtener_conexion()

    if request.method == "GET":
        filas = con.execute("""
            SELECT em.evento_id, em.menu_id, em.cantidad_proporcion,
                   e.fecha_evento, m.nombre AS nombre_menu
            FROM evento_menu em
            JOIN evento e ON e.evento_id = em.evento_id
            JOIN menu m ON m.menu_id = em.menu_id
            ORDER BY em.evento_id DESC
        """).fetchall()
        con.close()
        return jsonify({"ok": True, "datos": [dict(f) for f in filas]})

    datos = request.get_json(silent=True)
    requeridos = ("evento_id", "menu_id", "cantidad_proporcion")
    if not isinstance(datos, dict) or any(datos.get(c) in (None, "") for c in requeridos):
        con.close()
        return error("Debe enviar evento_id, menu_id y cantidad_proporcion.")

    try:
        con.execute(
            "INSERT INTO evento_menu(evento_id, menu_id, cantidad_proporcion) VALUES(?,?,?)",
            (datos["evento_id"], datos["menu_id"], datos["cantidad_proporcion"])
        )
        con.commit()
    except sqlite3.IntegrityError as exc:
        con.rollback()
        con.close()
        return respuesta_integridad(exc)
    con.close()
    return jsonify({"ok": True, "mensaje": "Menú asignado al evento."}), 201


@app.route("/api/eventos-menu/<int:evento_id>/<int:menu_id>",
           methods=["GET", "PUT", "PATCH", "DELETE"])
def evento_menu(evento_id: int, menu_id: int):
    con = obtener_conexion()
    fila = con.execute(
        "SELECT * FROM evento_menu WHERE evento_id=? AND menu_id=?",
        (evento_id, menu_id)
    ).fetchone()
    if fila is None:
        con.close()
        return error("Relación evento-menú no encontrada.", 404)

    if request.method == "GET":
        con.close()
        return jsonify({"ok": True, "datos": dict(fila)})

    if request.method == "DELETE":
        con.execute(
            "DELETE FROM evento_menu WHERE evento_id=? AND menu_id=?",
            (evento_id, menu_id)
        )
        con.commit()
        con.close()
        return jsonify({"ok": True, "mensaje": "Menú retirado del evento."})

    datos = request.get_json(silent=True)
    if not isinstance(datos, dict) or datos.get("cantidad_proporcion") in (None, ""):
        con.close()
        return error("Debe enviar cantidad_proporcion.")

    try:
        con.execute("""
            UPDATE evento_menu SET cantidad_proporcion=?
            WHERE evento_id=? AND menu_id=?
        """, (datos["cantidad_proporcion"], evento_id, menu_id))
        con.commit()
    except sqlite3.IntegrityError as exc:
        con.rollback()
        con.close()
        return respuesta_integridad(exc)

    fila = con.execute(
        "SELECT * FROM evento_menu WHERE evento_id=? AND menu_id=?",
        (evento_id, menu_id)
    ).fetchone()
    con.close()
    return jsonify({"ok": True, "datos": dict(fila)})


@app.get("/api/clientes/<int:cliente_id>/detalle")
def detalle_cliente(cliente_id: int):
    cliente = obtener("clientes", cliente_id)
    if cliente is None:
        return error("Cliente no encontrado.", 404)

    con = obtener_conexion()
    contactos = con.execute(
        "SELECT * FROM contacto WHERE cliente_id=?", (cliente_id,)
    ).fetchall()
    direcciones = con.execute(
        "SELECT * FROM direccion WHERE cliente_id=?", (cliente_id,)
    ).fetchall()
    eventos = con.execute(
        "SELECT * FROM evento WHERE cliente_id=? ORDER BY fecha_evento DESC",
        (cliente_id,)
    ).fetchall()
    con.close()

    return jsonify({"ok": True, "datos": {
        "cliente": cliente,
        "contactos": [serializar(f, ["responsable_default", "responsable_backup"])
                      for f in contactos],
        "direcciones": [dict(f) for f in direcciones],
        "eventos": [serializar(f, ["incluye_bebidas"]) for f in eventos]
    }})


@app.get("/api/eventos/<int:evento_id>/detalle")
def detalle_evento(evento_id: int):
    evento = obtener("eventos", evento_id)
    if evento is None:
        return error("Evento no encontrado.", 404)

    con = obtener_conexion()
    menus = con.execute("""
        SELECT m.*, em.cantidad_proporcion
        FROM evento_menu em
        JOIN menu m ON m.menu_id=em.menu_id
        WHERE em.evento_id=?
    """, (evento_id,)).fetchall()
    ordenes = con.execute("""
        SELECT os.*, e.nombre_completo AS responsable_nombre
        FROM orden_servicio os
        JOIN empleado e ON e.responsable_id=os.responsable_id
        WHERE os.evento_id=?
    """, (evento_id,)).fetchall()
    con.close()

    return jsonify({"ok": True, "datos": {
        "evento": evento,
        "menus": [dict(f) for f in menus],
        "ordenes_servicio": [serializar(f, ["requerimiento_personal"])
                             for f in ordenes]
    }})


@app.post("/api/eventos/<int:evento_id>/programar")
def programar_evento(evento_id: int):
    if obtener("eventos", evento_id) is None:
        return error("Evento no encontrado.", 404)
    con = obtener_conexion()
    con.execute("UPDATE evento SET estado='PROGRAMADO' WHERE evento_id=?", (evento_id,))
    con.commit()
    con.close()
    return jsonify({"ok": True, "mensaje": "Evento programado.",
                    "datos": obtener("eventos", evento_id)})


@app.post("/api/eventos/<int:evento_id>/cancelar")
def cancelar_evento(evento_id: int):
    if obtener("eventos", evento_id) is None:
        return error("Evento no encontrado.", 404)
    con = obtener_conexion()
    con.execute("UPDATE evento SET estado='CANCELADO' WHERE evento_id=?", (evento_id,))
    con.commit()
    con.close()
    return jsonify({"ok": True, "mensaje": "Evento cancelado.",
                    "datos": obtener("eventos", evento_id)})


@app.get("/api/ordenes-servicio/<int:orden_id>/detalle")
def detalle_orden(orden_id: int):
    orden = obtener("ordenes-servicio", orden_id)
    if orden is None:
        return error("Orden no encontrada.", 404)

    con = obtener_conexion()
    pagos = con.execute(
        "SELECT * FROM pago WHERE orden_id=? ORDER BY fecha_pago DESC", (orden_id,)
    ).fetchall()
    factura = con.execute(
        "SELECT * FROM factura WHERE orden_id=?", (orden_id,)
    ).fetchone()
    controles = con.execute(
        "SELECT * FROM control_calidad WHERE orden_id=?", (orden_id,)
    ).fetchall()
    conformidades = con.execute(
        "SELECT * FROM conformidad WHERE orden_id=?", (orden_id,)
    ).fetchall()
    total_pagado = con.execute(
        "SELECT COALESCE(SUM(monto),0) total FROM pago WHERE orden_id=?", (orden_id,)
    ).fetchone()["total"]
    con.close()

    return jsonify({"ok": True, "datos": {
        "orden": orden,
        "pagos": [dict(f) for f in pagos],
        "total_pagado": total_pagado,
        "saldo_pendiente": max(float(orden["monto_total"]) - float(total_pagado), 0),
        "factura": serializar(factura, ["servicio_conforme"]),
        "controles_calidad": [
            serializar(f, ["uso_mascarilla", "uso_guantes", "red_cabello"])
            for f in controles
        ],
        "conformidades": [serializar(f, ["servicio_conforme"]) for f in conformidades]
    }})


@app.post("/api/ordenes-servicio/<int:orden_id>/procesar-pago")
def procesar_pago(orden_id: int):
    orden = obtener("ordenes-servicio", orden_id)
    if orden is None:
        return error("Orden no encontrada.", 404)

    datos = request.get_json(silent=True)
    requeridos = ("monto", "metodo_pago", "tipo_pago")
    if not isinstance(datos, dict) or any(datos.get(c) in (None, "") for c in requeridos):
        return error("Debe enviar monto, metodo_pago y tipo_pago.")

    try:
        monto = float(datos["monto"])
    except (TypeError, ValueError):
        return error("monto debe ser numérico.")
    if monto <= 0:
        return error("monto debe ser mayor que cero.")

    con = obtener_conexion()
    total_anterior = con.execute(
        "SELECT COALESCE(SUM(monto),0) total FROM pago WHERE orden_id=?", (orden_id,)
    ).fetchone()["total"]
    saldo = float(orden["monto_total"]) - float(total_anterior)
    if monto > saldo + 0.0001:
        con.close()
        return error(f"El pago excede el saldo pendiente de {saldo:.2f}.")

    fecha = datos.get("fecha_pago") or datetime.now().isoformat(timespec="seconds")
    cur = con.execute("""
        INSERT INTO pago(orden_id, fecha_pago, monto, metodo_pago, tipo_pago)
        VALUES(?,?,?,?,?)
    """, (orden_id, fecha, monto, datos["metodo_pago"], datos["tipo_pago"]))

    total_nuevo = float(total_anterior) + monto
    nuevo_estado = "PAGADA" if total_nuevo >= float(orden["monto_total"]) else "PAGO_PARCIAL"
    con.execute(
        "UPDATE orden_servicio SET estado=? WHERE orden_id=?",
        (nuevo_estado, orden_id)
    )
    con.commit()
    pago_id = cur.lastrowid
    con.close()

    return jsonify({
        "ok": True,
        "mensaje": "Pago procesado.",
        "pago": obtener("pagos", pago_id),
        "total_pagado": total_nuevo,
        "saldo_pendiente": max(float(orden["monto_total"]) - total_nuevo, 0),
        "estado_orden": nuevo_estado
    }), 201


@app.post("/api/ordenes-servicio/<int:orden_id>/generar-factura")
def generar_factura(orden_id: int):
    if obtener("ordenes-servicio", orden_id) is None:
        return error("Orden no encontrada.", 404)

    datos = request.get_json(silent=True) or {}
    numero = datos.get("numero_factura") or f"FAC-{orden_id:06d}"
    fecha = datos.get("fecha_emision") or datetime.now().isoformat(timespec="seconds")

    con = obtener_conexion()
    try:
        cur = con.execute("""
            INSERT INTO factura(
                orden_id, numero_factura, fecha_emision,
                servicio_conforme, estado_cofi
            ) VALUES(?,?,?,?,?)
        """, (
            orden_id,
            numero,
            fecha,
            a_booleano(datos.get("servicio_conforme", False)),
            datos.get("estado_cofi", "EMITIDA")
        ))
        con.commit()
        factura_id = cur.lastrowid
    except sqlite3.IntegrityError as exc:
        con.rollback()
        con.close()
        return respuesta_integridad(exc)
    con.close()

    return jsonify({
        "ok": True,
        "mensaje": "Factura generada.",
        "datos": obtener("facturas", factura_id)
    }), 201


@app.errorhandler(404)
def ruta_no_encontrada(_):
    return error("Ruta no encontrada. Consulte GET /api.", 404)


if __name__ == "__main__":
    crear_tablas()
    app.run(debug=True, host="0.0.0.0", port=5000)
