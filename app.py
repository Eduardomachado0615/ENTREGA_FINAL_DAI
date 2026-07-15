from flask import Flask, jsonify, request

app = Flask(__name__)

clientes = {
    1: {
        "cliente_id": 1,
        "nombre": "Juan",
        "apellidos": "Pérez",
        "razon_social": "JP Eventos",
        "ruc": "06141234567890",
        "telefono": "7777-8888",
        "email": "juan@gmail.com"
    },
    2: {
        "cliente_id": 2,
        "nombre": "María",
        "apellidos": "López",
        "razon_social": "Eventos López",
        "ruc": "06149876543210",
        "telefono": "7123-4567",
        "email": "maria@gmail.com"
    }
}


@app.route("/")
def inicio():
    return jsonify({
        "mensaje": "API REST - Sistema de Eventos",
        "version": "1.0",
        "endpoints": [
            "GET /clientes",
            "GET /clientes/<id>",
            "POST /clientes",
            "PUT /clientes/<id>",
            "DELETE /clientes/<id>"
        ]
    })


# CONSULTAR TODOS LOS CLIENTES
@app.get("/clientes")
def consultar_clientes():
    return jsonify(list(clientes.values()))


# CONSULTAR UN CLIENTE
@app.get("/clientes/<int:id>")
def consultar_cliente(id):

    cliente = clientes.get(id)

    if cliente:
        return jsonify(cliente)

    return jsonify({"error": "Cliente no encontrado"}), 404


# AGREGAR CLIENTE
@app.post("/clientes")
def agregar_cliente():

    nuevo_cliente = request.get_json()

    if not nuevo_cliente:
        return jsonify({"error": "Debe enviar información"}), 400

    campos = [
        "nombre",
        "apellidos",
        "razon_social",
        "ruc",
        "telefono",
        "email"
    ]

    for campo in campos:
        if campo not in nuevo_cliente:
            return jsonify({"error": f"Falta el campo {campo}"}), 400

    nuevo_id = max(clientes.keys()) + 1

    clientes[nuevo_id] = {
        "cliente_id": nuevo_id,
        "nombre": nuevo_cliente["nombre"],
        "apellidos": nuevo_cliente["apellidos"],
        "razon_social": nuevo_cliente["razon_social"],
        "ruc": nuevo_cliente["ruc"],
        "telefono": nuevo_cliente["telefono"],
        "email": nuevo_cliente["email"]
    }

    return jsonify(clientes[nuevo_id]), 201


# MODIFICAR CLIENTE
@app.put("/clientes/<int:id>")
def actualizar_cliente(id):

    if id not in clientes:
        return jsonify({"error": "Cliente no encontrado"}), 404

    datos = request.get_json()

    clientes[id]["nombre"] = datos.get("nombre", clientes[id]["nombre"])
    clientes[id]["apellidos"] = datos.get("apellidos", clientes[id]["apellidos"])
    clientes[id]["razon_social"] = datos.get("razon_social", clientes[id]["razon_social"])
    clientes[id]["ruc"] = datos.get("ruc", clientes[id]["ruc"])
    clientes[id]["telefono"] = datos.get("telefono", clientes[id]["telefono"])
    clientes[id]["email"] = datos.get("email", clientes[id]["email"])

    return jsonify(clientes[id])


# ELIMINAR CLIENTE
@app.delete("/clientes/<int:id>")
def eliminar_cliente(id):

    if id not in clientes:
        return jsonify({"error": "Cliente no encontrado"}), 404

    eliminado = clientes.pop(id)

    return jsonify({
        "mensaje": "Cliente eliminado correctamente",
        "cliente": eliminado
    })


if __name__ == "__main__":
    app.run(debug=True)