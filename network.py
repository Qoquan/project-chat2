import websockets
import json
from datetime import datetime, timezone

class ChatNetwork:
    def __init__(self):
        self.ws = None
        self.username = None

    async def connect(self, uri, username):
        self.username = username
        self.ws = await websockets.connect(uri)

        # ÉTAPE 1 : Envoyer le username pour s'enregistrer (protocole du serveur)
        registration_msg = json.dumps({"username": username})
        await self.ws.send(registration_msg)
        
        response = await self.ws.recv()
        response_data = json.loads(response)
        
        if response_data.get("action") == "error":
            raise Exception(f"Erreur de connexion: {response_data['data']['error']}")
        
        print(f"✓ Connecté: {response_data['data']['message']}")
        

    async def send_message(self, user, content):
        message = {
            "action": "send_message",
            "data": {
                "username": user,
                "message": content
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.ws.send(json.dumps(message))

    async def join_room(self, room_name):
        """Rejoindre un salon (adapté au protocole du serveur)"""
        message = {
            "action": "join_room",
            "data": {
                "room_name": room_name
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.ws.send(json.dumps(message))

    async def leave_room(self):
        """Quitter le salon actuel (adapté au protocole du serveur)"""
        message = {
            "action": "leave_room",
            "data": {
                "username": self.username
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.ws.send(json.dumps(message))

    async def create_room(self, room_name):
        """Créer un nouveau salon (adapté au protocole du serveur)"""
        message = {
            "action": "create_room",
            "data": {
                "room_name": room_name
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.ws.send(json.dumps(message))

    async def list_rooms(self):
        """Lister tous les salons disponibles"""
        message = {
            "action": "list_rooms",
            "data": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.ws.send(json.dumps(message))

    async def receive_loop(self, callback):
        """Boucle infinie pour recevoir les messages (adapte les réponses du serveur)"""
        while True:
            try:
                raw_msg = await self.ws.recv()
                server_msg = json.loads(raw_msg)
                
                # Adapter le format du serveur au format attendu par l'UI
                adapted_msg = self._adapt_server_message(server_msg)
                callback(adapted_msg)
                
            except websockets.exceptions.ConnectionClosed:
                print("✗ Connexion fermée par le serveur")
                break
            except Exception as e:
                print(f"Erreur lors de la réception: {e}")

    @staticmethod
    def _adapt_server_message(server_msg):
        """Convertit le format du serveur au format attendu par l'UI du client"""
        action = server_msg.get("action")
        data = server_msg.get("data", {})
        
        # Message de chat reçu
        if action == "receive_message":
            return {
                "action": "receive_message",
                "user": data.get("username", "?"),
                "content": data.get("message", ""),
                "room": data.get("room_name", "default")
            }
        
        # Message de succès (affiché comme message système)
        elif action == "success":
            return {
                "action": "system",
                "content": data.get("message", "Opération réussie")
            }
        
        # Message d'erreur (affiché comme message système)
        elif action == "error":
            return {
                "action": "system",
                "content": f"❌ {data.get('error', 'Erreur inconnue')}"
            }
        
        # Liste des salons
        elif action == "list_rooms":
            rooms_dict = data.get("rooms", {})
            return {
                "action": "list_rooms",
                "rooms": list(rooms_dict.keys())
            }
        
        # Message non reconnu - retourner tel quel
        else:
            return server_msg