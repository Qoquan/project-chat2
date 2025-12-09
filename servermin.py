import asyncio
import websockets
import json
from collections import defaultdict
import websockets.server

# ===========================
# Structures de données
# ===========================
# rooms: salon -> set de websockets des clients dans le salon
rooms = defaultdict(set)
# clients: websocket -> {username: str, room: str}
clients = dict()
# Créer le salon par défaut
rooms["general"] = set()

# ===========================
# Fonctions utilitaires pour la réponse
# ===========================
def create_success_response(message):
    return json.dumps({"action": "success", "data": {"message": message}})

def create_error_response(error_message):
    return json.dumps({"action": "error", "data": {"error": error_message}})

def create_system_message(content):
    return {"action": "system", "data": {"message": content}}

def create_received_message(username, room_name, message):
    return {"action": "receive_message", "data": {"username": username, "message": message, "room_name": room_name}}

def create_room_list_message(room_dict):
    return json.dumps({"action": "list_rooms", "data": {"rooms": room_dict}})

# ===========================
# Fonctions de diffusion
# ===========================
async def broadcast(room_name, message):
    """Envoyer un message à tous les clients d'un salon."""
    if room_name in rooms:
        # Copier les websockets pour éviter les problèmes de modification pendant l'itération
        for ws in list(rooms[room_name]):
            try:
                await ws.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                # Le client s'est déconnecté, on le nettoiera dans le handler principal
                pass
            except Exception as e:
                print(f"Erreur lors du broadcast: {e}")

# ===========================
# Logique de gestion des actions
# ===========================
async def handle_join_room(ws, new_room_name):
    """Gère la logique pour un client qui rejoint un salon."""
    if ws not in clients:
        return

    client_info = clients[ws]
    old_room_name = client_info.get("room")

    if old_room_name == new_room_name:
        return # Déjà dans le salon

    # Quitter l'ancien salon
    if old_room_name and old_room_name in rooms:
        rooms[old_room_name].remove(ws)
        await broadcast(old_room_name, create_system_message(f"{client_info['username']} a quitté le salon."))

    # Rejoindre le nouveau salon
    if new_room_name not in rooms:
        # Optionnel: créer le salon s'il n'existe pas
        rooms[new_room_name] = set()
        
    rooms[new_room_name].add(ws)
    client_info["room"] = new_room_name
    
    await ws.send(create_success_response(f"Vous avez rejoint le salon '{new_room_name}'."))
    await broadcast(new_room_name, create_system_message(f"{client_info['username']} a rejoint le salon."))


# ===========================
# Handler principal
# ===========================
async def handler(ws: websockets.server.WebSocketServerProtocol):
    """Gère une connexion client unique."""
    try:
        # --- Enregistrement initial ---
        registration_data = await ws.recv()
        registration_msg = json.loads(registration_data)
        username = registration_msg.get("username")

        if not username:
            await ws.send(create_error_response("Nom d'utilisateur requis."))
            await ws.close()
            return
        
        # Stocker les informations du client
        initial_room = "general"
        clients[ws] = {"username": username, "room": initial_room}
        rooms[initial_room].add(ws)
        
        print(f"[SERVER] {username} s'est connecté et a rejoint {initial_room}")
        
        # Confirmer la connexion au client
        await ws.send(create_success_response(f"Connecté en tant que {username}."))
        
        # Annoncer l'arrivée du nouveau client dans le salon
        await broadcast(initial_room, create_system_message(f"{username} a rejoint le salon."))

        # --- Boucle de réception des messages ---
        async for message in ws:
            try:
                msg = json.loads(message)
                action = msg.get("action")
                data = msg.get("data", {})
                client_info = clients[ws]

                if action == "send_message":
                    content = data.get("message")
                    current_room = client_info["room"]
                    await broadcast(current_room, create_received_message(client_info["username"], current_room, content))

                elif action == "join_room":
                    new_room_name = data.get("room_name")
                    if new_room_name:
                        await handle_join_room(ws, new_room_name)
                    else:
                        await ws.send(create_error_response("Nom de salon manquant."))

                elif action == "leave_room":
                    # Revenir au salon "general"
                    await handle_join_room(ws, "general")

                elif action == "create_room":
                    room_name = data.get("room_name")
                    if room_name:
                        if room_name in rooms:
                            await ws.send(create_error_response(f"Le salon '{room_name}' existe déjà."))
                        else:
                            rooms[room_name] = set()
                            await ws.send(create_success_response(f"Le salon '{room_name}' a été créé."))
                            # Informer tout le monde (ou juste le créateur) de la nouvelle liste de salons
                            await list_rooms(ws) # Send to current client
                    else:
                        await ws.send(create_error_response("Nom de salon manquant."))

                elif action == "list_rooms":
                    await list_rooms(ws)

            except json.JSONDecodeError:
                print(f"Message non JSON reçu de {clients.get(ws, {}).get('username', 'inconnu')}")
            except Exception as e:
                print(f"Erreur lors du traitement du message: {e}")
                await ws.send(create_error_response("Erreur interne du serveur."))


    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Connexion fermée avec le code {e.code}: {e.reason}")
    except Exception as e:
        print(f"Erreur inattendue dans le handler: {e}")
    finally:
        # --- Nettoyage ---
        if ws in clients:
            client_info = clients[ws]
            username = client_info["username"]
            room = client_info["room"]
            
            print(f"[SERVER] {username} déconnecté.")
            
            # Retirer le client du salon et de la liste des clients
            if room in rooms:
                rooms[room].discard(ws)
            del clients[ws]
            
            # Annoncer la déconnexion au salon
            await broadcast(room, create_system_message(f"{username} a quitté le chat."))

async def list_rooms(ws):
    """Envoie la liste des salons au client spécifié."""
    # Le client s'attend à un dictionnaire pour les salons
    room_dict = {name: len(clients_in_room) for name, clients_in_room in rooms.items() if clients_in_room}
    # Filtrer les salons vides, sauf "general"
    if "general" not in room_dict:
        room_dict["general"] = 0
        
    await ws.send(create_room_list_message(room_dict))

# ===========================
# Lancement du serveur
# ===========================
async def main():
    print("[SERVER] Démarrage du serveur Chat sur ws://localhost:8765")
    async with websockets.serve(handler, "localhost", 8765):
        await asyncio.Future()  # Exécuter indéfiniment

if __name__ == "__main__":
    asyncio.run(main())
