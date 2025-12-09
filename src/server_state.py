from typing import Dict, Set, Optional
import asyncio
from dataclasses import dataclass, field

@dataclass
class Client:
    websocket: any
    username: str
    current_room: str = "default"

@dataclass
class Room:
    """Représente un salon de discussion."""
    name: str
    clients: Set[str] = field(default_factory=set)

    def __repr__(self):
        return f"Room(name={self.name}, clients={list(self.clients)})"

class ServerState:
    """État du serveur de discussion."""
    def __init__(self):
        self.rooms: Dict[str, Room] = {
            "default": Room(name="default")
        }
        self.clients: Dict[str, Client] = {}  # username -> Client
        self.websocket_to_username: Dict[any, str] = {}  # websocket -> username
        self.lock = asyncio.Lock()

    async def add_client(self, websocket, username: str) -> bool:
        """Ajouter un nouveau client à l'état du serveur."""
        async with self.lock:
            if username in self.clients:
                return False  # Nom d'utilisateur déjà pris

            client = Client(websocket=websocket, username=username)
            self.clients[username] = client
            self.websocket_to_username[websocket] = username
            self.rooms["default"].clients.add(username)
            return True

    async def remove_client(self, websocket) -> Optional[str]:
        """Retirer un client de l'état du serveur."""
        async with self.lock:
            username = self.websocket_to_username.get(websocket)
            if not username:
                return None  # Client non trouvé

            client = self.clients.get(username)
            if client:
                room = self.rooms.get(client.current_room)
                if room:
                    room.clients.discard(username)
            
            if username in self.clients:
                del self.clients[username]
            if websocket in self.websocket_to_username:
                del self.websocket_to_username[websocket]
            return username

    async def create_room(self, room_name: str) -> bool:
        """Créer un nouveau salon de discussion."""
        async with self.lock:
            if room_name in self.rooms:
                return False  # Le salon existe déjà
            self.rooms[room_name] = Room(name=room_name)
            return True

    async def join_room(self, username: str, room_name: str) -> bool:
        """Rejoindre un salon de discussion existant."""
        async with self.lock:
            client = self.clients.get(username)
            if not client or room_name not in self.rooms:
                return False  # Client ou salon non trouvé

            # Quitter le salon actuel
            old_room = self.rooms.get(client.current_room)
            if old_room:
                old_room.clients.discard(username)

            # Rejoindre le nouveau salon
            client.current_room = room_name
            self.rooms[room_name].clients.add(username)
            return True

    async def leave_room(self, username: str) -> Optional[str]:
        """Quitter le salon actuel et retourner au salon par défaut."""
        async with self.lock:
            client = self.clients.get(username)
            if not client:
                return None  # Client non trouvé

            old_room_name = client.current_room
            if old_room_name == "default":
                return None  # Déjà dans le salon par défaut

            old_room = self.rooms.get(old_room_name)
            if old_room:
                old_room.clients.discard(username)

            client.current_room = "default"
            self.rooms["default"].clients.add(username)
            return old_room_name

    async def get_room_clients(self, room_name: str) -> Set[str]:
        """Obtenir la liste des clients dans un salon spécifique."""
        async with self.lock:
            room = self.rooms.get(room_name)
            return room.clients.copy() if room else set()

    async def get_client_room(self, username: str) -> Optional[str]:
        """Obtenir le salon actuel d'un client spécifique."""
        client = self.clients.get(username)
        return client.current_room if client else None

    async def get_client_websocket(self, username: str):
        """Obtenir le websocket d'un client spécifique."""
        client = self.clients.get(username)
        return client.websocket if client else None

    async def list_rooms(self) -> Dict[str, int]:
        """Lister tous les salons de discussion disponibles."""
        async with self.lock:
            return {name: len(room.clients) for name, room in self.rooms.items()}

    async def get_username_from_websocket(self, websocket) -> Optional[str]:
        """Obtenir le nom d'utilisateur associé à un websocket."""
        return self.websocket_to_username.get(websocket)

    def __repr__(self):
        return f"ServerState(rooms={self.rooms}, clients={list(self.clients.keys())})"
