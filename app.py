from flask import Flask, jsonify, request
from database import obtener_conexion
import sqlite3


app = Flask(__name__)



# INICIO DE LA API
# =========================
@app.route("/")
def inicio():
    return jsonify({
        "mensaje": "API REST - Sistema Sazonara",
        "version": "1.0",
        "endpoints": [
            "GET /clientes",
            "GET /clientes/<id>",
            "POST /clientes",
            "PUT /clientes/<id>",
            "DELETE /clientes/<id>"
        ]
    }), 200


# CONSULTAR TODOS LOS CLIENTES
# =========================
@app.get("/clientes")
def consultar_clientes():

    conexion = obtener_conexion()

    try:
        clientes = conexion.execute("""
            SELECT
                cliente_id,
                nombre,
                apellidos,
                razon_social,
                ruc,
                telefono,
                email
            FROM cliente
            ORDER BY cliente_id
        """).fetchall()

        return jsonify([
            dict(cliente)
            for cliente in clientes
        ]), 200

    finally:
        conexion.close()


# CONSULTAR UN CLIENTE POR ID
# =========================
@app.get("/clientes/<int:id>")
def consultar_cliente(id):

    conexion = obtener_conexion()

    try:
        cliente = conexion.execute("""
            SELECT
                cliente_id,
                nombre,
                apellidos,
                razon_social,
                ruc,
                telefono,
                email
            FROM cliente
            WHERE cliente_id = ?
        """, (id,)).fetchone()

        if cliente is None:
            return jsonify({
                "error": "Cliente no encontrado"
            }), 404

        return jsonify(dict(cliente)), 200

    finally:
        conexion.close()



# AGREGAR CLIENTE
# =========================
@app.post("/clientes")
def agregar_cliente():

    datos = request.get_json()

    if datos is None:
        return jsonify({
            "error": "Debe enviar información en formato JSON"
        }), 400

    campos_obligatorios = [
        "nombre",
        "apellidos"
    ]

    for campo in campos_obligatorios:
        if campo not in datos or not str(datos[campo]).strip():
            return jsonify({
                "error": f"El campo {campo} es obligatorio"
            }), 400

    nombre = datos["nombre"].strip()
    apellidos = datos["apellidos"].strip()
    razon_social = datos.get("razon_social")
    ruc = datos.get("ruc")
    telefono = datos.get("telefono")
    email = datos.get("email")

    conexion = obtener_conexion()

    try:
        cursor = conexion.execute("""
            INSERT INTO cliente (
                nombre,
                apellidos,
                razon_social,
                ruc,
                telefono,
                email
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            nombre,
            apellidos,
            razon_social,
            ruc,
            telefono,
            email
        ))

        conexion.commit()

        nuevo_id = cursor.lastrowid

        cliente_creado = conexion.execute("""
            SELECT
                cliente_id,
                nombre,
                apellidos,
                razon_social,
                ruc,
                telefono,
                email
            FROM cliente
            WHERE cliente_id = ?
        """, (nuevo_id,)).fetchone()

        return jsonify({
            "mensaje": "Cliente agregado correctamente",
            "cliente": dict(cliente_creado)
        }), 201

    except sqlite3.Error as error:
        conexion.rollback()

        return jsonify({
            "error": "No se pudo agregar el cliente",
            "detalle": str(error)
        }), 500

    finally:
        conexion.close()



# ACTUALIZAR CLIENTE
# =========================
@app.put("/clientes/<int:id>")
def actualizar_cliente(id):

    datos = request.get_json()

    if datos is None:
        return jsonify({
            "error": "Debe enviar información en formato JSON"
        }), 400

    conexion = obtener_conexion()

    try:
        cliente_actual = conexion.execute("""
            SELECT *
            FROM cliente
            WHERE cliente_id = ?
        """, (id,)).fetchone()

        if cliente_actual is None:
            return jsonify({
                "error": "Cliente no encontrado"
            }), 404

        nombre = datos.get(
            "nombre",
            cliente_actual["nombre"]
        )

        apellidos = datos.get(
            "apellidos",
            cliente_actual["apellidos"]
        )

        razon_social = datos.get(
            "razon_social",
            cliente_actual["razon_social"]
        )

        ruc = datos.get(
            "ruc",
            cliente_actual["ruc"]
        )

        telefono = datos.get(
            "telefono",
            cliente_actual["telefono"]
        )

        email = datos.get(
            "email",
            cliente_actual["email"]
        )

        if not str(nombre).strip():
            return jsonify({
                "error": "El nombre no puede estar vacío"
            }), 400

        if not str(apellidos).strip():
            return jsonify({
                "error": "Los apellidos no pueden estar vacíos"
            }), 400

        conexion.execute("""
            UPDATE cliente
            SET
                nombre = ?,
                apellidos = ?,
                razon_social = ?,
                ruc = ?,
                telefono = ?,
                email = ?
            WHERE cliente_id = ?
        """, (
            nombre,
            apellidos,
            razon_social,
            ruc,
            telefono,
            email,
            id
        ))

        conexion.commit()

        cliente_actualizado = conexion.execute("""
            SELECT
                cliente_id,
                nombre,
                apellidos,
                razon_social,
                ruc,
                telefono,
                email
            FROM cliente
            WHERE cliente_id = ?
        """, (id,)).fetchone()

        return jsonify({
            "mensaje": "Cliente actualizado correctamente",
            "cliente": dict(cliente_actualizado)
        }), 200

    except sqlite3.Error as error:
        conexion.rollback()

        return jsonify({
            "error": "No se pudo actualizar el cliente",
            "detalle": str(error)
        }), 500

    finally:
        conexion.close()



# ELIMINAR CLIENTE
# =========================
@app.delete("/clientes/<int:id>")
def eliminar_cliente(id):

    conexion = obtener_conexion()

    try:
        cliente = conexion.execute("""
            SELECT
                cliente_id,
                nombre,
                apellidos,
                razon_social,
                ruc,
                telefono,
                email
            FROM cliente
            WHERE cliente_id = ?
        """, (id,)).fetchone()

        if cliente is None:
            return jsonify({
                "error": "Cliente no encontrado"
            }), 404

        cliente_eliminado = dict(cliente)

        conexion.execute("""
            DELETE FROM cliente
            WHERE cliente_id = ?
        """, (id,))

        conexion.commit()

        return jsonify({
            "mensaje": "Cliente eliminado correctamente",
            "cliente": cliente_eliminado
        }), 200

    except sqlite3.IntegrityError:
        conexion.rollback()

        return jsonify({
            "error": "No se puede eliminar el cliente porque tiene registros relacionados"
        }), 409

    except sqlite3.Error as error:
        conexion.rollback()

        return jsonify({
            "error": "No se pudo eliminar el cliente",
            "detalle": str(error)
        }), 500

    finally:
        conexion.close()



# EJECUTAR LA APLICACIÓN
# =========================
if __name__ == "__main__":
    app.run(debug=True)
