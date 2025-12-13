import asyncio
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Set

import websockets
from websockets.exceptions import ConnectionClosed

# ======================================================================================
# Configuration du Logger
# ======================================================================================

def setup_logger(name: str = "ChatServer", level: int = logging.INFO) -> logging.Logger:
    """Configure et retourne un logger avec des couleurs pour la console."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.hasHandlers():
        logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    class ColoredFormatter(logging.Formatter):
        """Formatter personnalisé avec des couleurs ANSI pour une meilleure lisibilité."""
        COLORS = {'DEBUG': '\033[94m', 'INFO': '\033[92m', 'WARNING': '\033[93m', 'ERROR': '\033[91m', 'CRITICAL': '\033[95m'}
        RESET = '\033[0m'
        BOLD = '\033[1m'

        def format(self, record):
            color = self.COLORS.get(record.levelname, self.RESET)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_message = f"{self.BOLD}[{timestamp}]{self.RESET} {color}{record.levelname:8}{self.RESET} - {record.getMessage()}"
            if record.exc_info:
                log_message += f"\n{self.formatException(record.exc_info)}"
            return log_message

    formatter = ColoredFormatter()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger

# Instance globale du logger pour le serveur
server_logger = setup_logger("ChatServer", logging.INFO)

# ======================================================================================
# Définitions du Protocole de Communication
# ======================================================================================

class ProtocolError(Exception):
    """Exception levée pour les erreurs liées au protocole."""
    pass

class ActionType(Enum):
    """Énumère les actions possibles dans le protocole de communication."""
    # Actions client -> serveur
    CREATE_ROOM = "create_room"
    JOIN_ROOM = "join_room"
    LEAVE_ROOM = "leave_room"
    SEND_MESSAGE = "send_message"
    LIST_ROOMS = "list_rooms"
    
    # Actions serveur -> client
    RECEIVE_MESSAGE = "receive_message"
    ERROR = "error"
    SUCCESS = "success"
    SYSTEM = "system" # Pour les messages système génériques

@dataclass
class ProtocolMessage:
    """Structure standard d'un message échangé entre le client et le serveur."""
    action: str
    data: Dict[str, Any]
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_json(self) -> str:
        """Sérialise le message en une chaîne JSON."""
        return json.dumps(asdict(self), ensure_ascii=False)

    @staticmethod
    def from_json(json_str: str) -> 'ProtocolMessage':
        """Désérialise une chaîne JSON en un objet ProtocolMessage."""
        try:
            data = json.loads(json_str)
            if "action" not in data:
                raise ProtocolError("Le champ 'action' est manquant.")
            return ProtocolMessage(action=data["action"], data=data.get("data", {}))
        except (json.JSONDecodeError, TypeError) as e:
            raise ProtocolError(f"Format de message JSON invalide: {e}") from e

    # Méthodes utilitaires pour créer des réponses standards
    @staticmethod
    def create_error(error_msg: str) -> 'ProtocolMessage':
        return ProtocolMessage(action=ActionType.ERROR.value, data={"error": error_msg})

    @staticmethod
    def create_success(info_msg: str, extra_data: Optional[Dict[str, Any]] = None) -> 'ProtocolMessage':
        payload = {"message": info_msg}
        if extra_data:
            payload.update(extra_data)
        return ProtocolMessage(action=ActionType.SUCCESS.value, data=payload)
        
    @staticmethod
    def create_system_message(message: str) -> 'ProtocolMessage':
        return ProtocolMessage(action=ActionType.SYSTEM.value, data={"message": message})

# ======================================================================================
# Gestion de l'État du Serveur
# ======================================================================================

@dataclass
class Client:
    """Représente un client connecté."""
    websocket: Any
    username: str
    current_room: str = "general" # Le salon par défaut

@dataclass
class Room:
    """Représente un salon de discussion."""
    name: str
    clients: Set[Any] = field(default_factory=set)  # Stocke les objets websocket directement

class ServerState:
    """Classe centralisée pour gérer l'état global du serveur (clients, salons)."""
    def __init__(self):
        self.clients: Dict[Any, Client] = {}  # websocket -> Client
        self.rooms: Dict[str, Room] = {"general": Room(name="general")}
        self.lock = asyncio.Lock()

    async def register_client(self, websocket: Any, username: str) -> bool:
        """Enregistre un nouveau client et l'ajoute au salon 'general'."""
        async with self.lock:
            if any(c.username == username for c in self.clients.values()):
                return False
            
            new_client = Client(websocket=websocket, username=username)
            self.clients[websocket] = new_client
            self.rooms["general"].clients.add(websocket)
            return True

    async def unregister_client(self, websocket: Any) -> Optional[Client]:
        """Supprime un client et le retire de son salon."""
        async with self.lock:
            client = self.clients.pop(websocket, None)
            if client:
                room = self.rooms.get(client.current_room)
                if room:
                    room.clients.discard(websocket)
            return client

    async def create_room(self, room_name: str) -> bool:
        """Crée un nouveau salon."""
        async with self.lock:
            if room_name in self.rooms:
                return False
            self.rooms[room_name] = Room(name=room_name)
            return True

    async def join_room(self, websocket: Any, new_room_name: str) -> Optional[str]:
        """Fait rejoindre un salon à un client. Retourne l'ancien salon."""
        async with self.lock:
            client = self.clients.get(websocket)
            if not client or new_room_name not in self.rooms:
                return None

            old_room_name = client.current_room
            if old_room_name != new_room_name:
                if old_room_name in self.rooms:
                    self.rooms[old_room_name].clients.discard(websocket)
                
                self.rooms[new_room_name].clients.add(websocket)
                client.current_room = new_room_name
            
            return old_room_name
            
    async def get_all_rooms(self) -> Dict[str, int]:
        """Retourne un dictionnaire des salons et du nombre de leurs membres."""
        async with self.lock:
            return {name: len(room.clients) for name, room in self.rooms.items()}

# ======================================================================================
# Gestionnaire des Actions (Logique Métier)
# ======================================================================================

class MessageHandler:
    """Traite les messages entrants et exécute la logique métier correspondante."""
    def __init__(self, state: ServerState):
        self.state = state

    async def handle_message(self, websocket: Any, message: ProtocolMessage):
        """Aiguille un message vers la bonne méthode de traitement."""
        client = self.state.clients.get(websocket)
        if not client:
            await websocket.send(ProtocolMessage.create_error("Client non enregistré.").to_json())
            return

        handler_method = getattr(self, f"handle_{message.action}", self.handle_unknown)
        await handler_method(websocket, client, message.data)

    async def handle_unknown(self, websocket: Any, client: Client, data: Dict):
        """Gère les actions non reconnues."""
        server_logger.warning(f"Action inconnue de {client.username}: {data}")
        await websocket.send(ProtocolMessage.create_error("Action inconnue.").to_json())

    async def handle_send_message(self, websocket: Any, client: Client, data: Dict):
        """Gère l'envoi d'un message par un client."""
        content = data.get("message")
        if not content:
            await websocket.send(ProtocolMessage.create_error("Le message ne peut pas être vide.").to_json())
            return

        room_name = client.current_room
        server_logger.info(f"💬 [{room_name}] {client.username}: {content}")
        
        response = ProtocolMessage(
            action=ActionType.RECEIVE_MESSAGE.value,
            data={"username": client.username, "message": content, "room_name": room_name}
        )
        await self.broadcast(room_name, response, exclude_ws=websocket)

    async def handle_create_room(self, websocket: Any, client: Client, data: Dict):
        """Gère la création d'un salon."""
        room_name = data.get("room_name")
        if not room_name:
            await websocket.send(ProtocolMessage.create_error("Nom de salon manquant.").to_json())
            return

        if await self.state.create_room(room_name):
            server_logger.info(f"🏠 Salon '{room_name}' créé par {client.username}")
            await websocket.send(ProtocolMessage.create_success(f"Salon '{room_name}' créé.").to_json())
            await self.broadcast_room_list()
        else:
            await websocket.send(ProtocolMessage.create_error(f"Le salon '{room_name}' existe déjà.").to_json())

    async def handle_join_room(self, websocket: Any, client: Client, data: Dict):
        """Gère la demande de rejoindre un salon."""
        room_name = data.get("room_name")
        if not room_name:
            await websocket.send(ProtocolMessage.create_error("Nom de salon manquant.").to_json())
            return

        old_room_name = await self.state.join_room(websocket, room_name)
        if old_room_name is not None:
            server_logger.info(f"🚪 {client.username} a rejoint {room_name} (venant de {old_room_name})")
            
            await self.broadcast(old_room_name, ProtocolMessage.create_system_message(f"{client.username} a quitté le salon."))
            await self.broadcast(room_name, ProtocolMessage.create_system_message(f"{client.username} a rejoint le salon."))
            
            await websocket.send(ProtocolMessage.create_success(f"Vous avez rejoint le salon '{room_name}'.").to_json())
        else:
            await websocket.send(ProtocolMessage.create_error(f"Le salon '{room_name}' n'existe pas.").to_json())

    async def handle_leave_room(self, websocket: Any, client: Client, data: Dict):
        """Gère la demande de quitter un salon pour retourner à 'general'."""
        if client.current_room == "general":
            await websocket.send(ProtocolMessage.create_error("Vous êtes déjà dans le salon principal.").to_json())
            return
        
        await self.handle_join_room(websocket, client, {"room_name": "general"})

    async def handle_list_rooms(self, websocket: Any, client: Client, data: Dict):
        """Envoie la liste des salons au client qui la demande."""
        rooms = await self.state.get_all_rooms()
        response = ProtocolMessage(action=ActionType.LIST_ROOMS.value, data={"rooms": rooms})
        await websocket.send(response.to_json())

    async def broadcast(self, room_name: str, message: ProtocolMessage, exclude_ws: Optional[Any] = None):
        """Diffuse un message à tous les clients d'un salon de manière robuste."""
        room = self.state.rooms.get(room_name)
        if not room:
            server_logger.warning(f"Tentative de diffusion dans un salon inexistant: {room_name}")
            return

        message_json = message.to_json()
        
        # On utilise une copie de la liste des clients pour itérer
        clients_to_iterate = list(room.clients)
        dead_clients = []
        tasks = []

        for ws in clients_to_iterate:
            if ws == exclude_ws:
                continue
            
            try:
                # On vérifie si la connexion est ouverte avant d'envoyer
                if ws.open:
                    tasks.append(ws.send(message_json))
                else:
                    dead_clients.append(ws)
            except Exception:  # Attrape AttributeError si 'open' n'existe pas ou autres erreurs
                server_logger.warning(f"Client invalide ou déconnecté trouvé dans le salon '{room_name}'.")
                dead_clients.append(ws)

        # Envoi des messages en parallèle
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Nettoyage des clients morts ou invalides
        if dead_clients:
            server_logger.info(f"Nettoyage de {len(dead_clients)} client(s) mort(s) du salon '{room_name}'.")
            async with self.state.lock:
                for ws in dead_clients:
                    room.clients.discard(ws)
                    # On supprime aussi de la liste globale des clients
                    self.state.clients.pop(ws, None)


    async def broadcast_room_list(self):
        """Diffuse la liste mise à jour des salons à tous les clients connectés."""
        rooms = await self.state.get_all_rooms()
        response = ProtocolMessage(action=ActionType.LIST_ROOMS.value, data={"rooms": rooms})
        
        all_clients = [client.websocket for client in self.state.clients.values()]
        tasks = [ws.send(response.to_json()) for ws in all_clients if ws.open]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

# ======================================================================================
# Classe Principale du Serveur
# ======================================================================================

class ChatServer:
    """Le serveur de chat principal."""
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.state = ServerState()
        self.handler = MessageHandler(self.state)
    
    async def handle_connection(self, websocket: Any):
        """Gère une connexion client de A à Z."""
        client = None
        try:
            # --- Étape 1: Enregistrement du client ---
            server_logger.info("New connection attempt...")
            message_json = await websocket.recv()
            data = json.loads(message_json)
            username = data.get("username")

            if not username:
                server_logger.warning("Connection rejected: no username provided.")
                await websocket.send(ProtocolMessage.create_error("Nom d'utilisateur manquant.").to_json())
                return

            if not await self.state.register_client(websocket, username):
                server_logger.warning(f"Connection rejected: username '{username}' is taken.")
                await websocket.send(ProtocolMessage.create_error(f"Le nom d'utilisateur '{username}' est déjà pris.").to_json())
                return

            client = self.state.clients[websocket]
            server_logger.info(f"✅ Client '{username}' registered. Sending welcome sequence...")
            await websocket.send(ProtocolMessage.create_success(f"Bienvenue {username} !").to_json())
            
            server_logger.info(f"Broadcasting join message for '{username}'...")
            await self.handler.broadcast("general", ProtocolMessage.create_system_message(f"{username} a rejoint le chat."))
            
            server_logger.info(f"Sending room list to '{username}'...")
            await self.handler.handle_list_rooms(websocket, client, {})

            server_logger.info(f"Broadcasting room list to all...")
            await self.handler.broadcast_room_list()
            server_logger.info(f"Welcome sequence for '{username}' complete. Awaiting messages.")

            # --- Étape 2: Boucle de réception des messages ---
            async for message_json in websocket:
                try:
                    message = ProtocolMessage.from_json(message_json)
                    await self.handler.handle_message(websocket, message)
                except ProtocolError as e:
                    server_logger.warning(f"Message invalide de {client.username}: {e}")
                    await websocket.send(ProtocolMessage.create_error(str(e)).to_json())

        except ConnectionClosed:
            server_logger.info(f"🔌 Connexion fermée pour {client.username if client else 'un client inconnu'}.")
        except Exception as e:
            server_logger.critical(f"💥 UNEXPECTED ERROR in handle_connection for {client.username if client else 'un client'}: {e}", exc_info=True)
        finally:
            # --- Étape 3: Nettoyage ---
            if client:
                server_logger.info(f"Cleaning up connection for '{client.username}'...")
                await self.state.unregister_client(websocket)
                server_logger.info(f"🗑️ Client '{client.username}' disconnected and cleaned up.")
                await self.handler.broadcast(client.current_room, ProtocolMessage.create_system_message(f"{client.username} a quitté le chat."))
                await self.handler.broadcast_room_list()
            else:
                server_logger.info("Cleaning up anonymous connection.")
    
    async def start(self):
        """Démarre le serveur WebSocket."""
        server_logger.info("=" * 60)
        server_logger.info(f"🚀 Démarrage du serveur de chat sur ws://{self.host}:{self.port}")
        server_logger.info("=" * 60)
        async with websockets.serve(self.handle_connection, self.host, self.port):
            await asyncio.Future()

# ======================================================================================
# Point d'Entrée
# ======================================================================================

async def main():
    server = ChatServer()
    try:
        await server.start()
    except KeyboardInterrupt:
        server_logger.info("🛑 Arrêt du serveur demandé.")
    except Exception as e:
        server_logger.critical(f"💥 Erreur fatale du serveur: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
