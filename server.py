from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

clients = {}  # Diccionario para almacenar roles y números de clientes
server_id = None  # ID del servidor actual
client_counter = 1  # Contador para numerar clientes

@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("connect")
def handle_connect():
    global server_id, client_counter
    role = "cliente"
    client_number = client_counter

    if server_id is None:
        server_id = request.sid
        role = "servidor"
    else:
        client_counter += 1  # Aumenta el número de cliente

    clients[request.sid] = {"role": role, "number": client_number}
    
    print(f"Cliente {request.sid} conectado como {role.capitalize()} {client_number if role == 'cliente' else ''}")
    
    emit("role_changed", {"new_role": "Servidor" if role == "servidor" else f"Cliente {client_number}"}, room=request.sid)

@socketio.on("disconnect")
def handle_disconnect():
    global server_id
    if request.sid in clients:
        role = clients[request.sid]["role"]
        print(f"{role.capitalize()} {clients[request.sid]['number'] if role == 'cliente' else ''} ({request.sid}) desconectado.")

        if request.sid == server_id:
            server_id = None
            for client_id in clients:
                if client_id != request.sid:
                    server_id = client_id
                    clients[server_id]["role"] = "servidor"
                    emit("role_changed", {"new_role": "Servidor"}, room=server_id)
                    print(f"Nuevo servidor asignado: {server_id}")
                    break

        del clients[request.sid]

@socketio.on("message")
def handle_message(data):
    sender_id = request.sid
    sender_info = clients.get(sender_id, {"role": "cliente", "number": 0})

    sender_role = sender_info["role"]
    sender_number = sender_info["number"]

    if sender_role == "servidor":
        sender_display = "Servidor"
    else:
        sender_display = f"Cliente {sender_number}"

    print(f"Mensaje de {sender_display}: {data['msg']}")

    emit("message", {
        "msg": f"{sender_display}: {data['msg']}",
        "role": sender_role
    }, broadcast=True)

@socketio.on("change_role")
def handle_change_role():
    global server_id

    if request.sid not in clients:
        return  

    current_role = clients[request.sid]["role"]

    if current_role == "servidor":
        print(f"Servidor cambia a Cliente {clients[request.sid]['number']}")
        clients[request.sid]["role"] = "cliente"
        server_id = None  
    else:
        if server_id is None:
            print(f"Cliente {clients[request.sid]['number']} se convierte en Servidor")
            clients[request.sid]["role"] = "servidor"
            server_id = request.sid
        else:
            emit("error", {"msg": "Ya hay un servidor activo."}, room=request.sid)
            return  

    new_role_name = "Servidor" if clients[request.sid]["role"] == "servidor" else f"Cliente {clients[request.sid]['number']}"
    emit("role_changed", {"new_role": new_role_name}, room=request.sid)

if __name__ == "__main__":
    socketio.run(app, debug=True)
