from typing import Dict, Set, Optional
import asyncio
from dataclasses import dataclass, field

@dataclass
class Client:
    websocket: any  # Placeholder for the websocket connection
    username: str
    current_room: str = "default"
    
@dataclass
class Room:
    """ Représente un salon de discussion. """
    nom: str
    clients: Set[str] = field(default_factory=set)
    
    def __repr__(self):
        return f"salon(nom={self.name}, clients={list(self.clients)})"
    
class ServerState:
    """etat du serveur de discussion.  """
    def __init__(self):
        self.rooms: Dict[str, Room] = {
            "default": Room(name="default")
        }
    
        self.clients: Dict[str, Client] = {} # Mapping from username to Client
        self.websocket_to_username: Dict[any, str] = {}  # Mapping from websocket to username
        self.lock = asyncio.Lock()  # for thread-safe operations
    
    async def add_client(self, websocket , username: str)-> bool:
        """add à new client to the server state."""
        async with self.lock:
            if username in self.clients:
                return False  # Username already taken
            
            client = Client(websocket=websocket, username=username)
            self.clients[username] = client
            self.websocket_to_username[websocket] = username
            self.rooms["default"].clients.add(username)
            return True
        
    async def remove_client(self, websocket )-> Optional[str]:
        """remove a client from the server state."""
        async with self.lock:
            username = self.websocket_to_username.get(websocket)
            if not username:
                return None  # Client not found
            
            client = self.clients.pop(username)
            if client:
                # Remove from current room
                room = self.rooms.get(client.current_room)
                if room :
                    room.clients.discard(username)
            
            del self.clients[username]
            del self.websocket_to_username[websocket]
            return username
    
    async def create_room(self, room_name: str) -> bool:
        """create a new chat room."""
        async with self.lock:
            if room_name in self.rooms:
                return False  # Room already exists
            self.rooms[room_name] = Room(name=room_name)
            return True
    
    async def join_room(self, username: str, room_name: str) -> bool:
        """join an existing chat room."""
        async with self.lock:
            client = self.clients.get(username)
            if not client or room_name not in self.rooms:
                return False  # Client or room not found
            # Leave current room
            old_room = self.rooms.get(client.current_room)
            if old_room:
                old_room.clients.discard(username)
            # Join new room
            client_current_room  = room_name
            self.rooms[room_name].clients.add(username)
            return True
        
    async def leave_room(self, username: str) -> Optional[str]:
        """ leave the current chat room and return to default."""
        async with self.lock:
            client = self.clients.get(username)
            if not client:
                return None  # Client not found
            old_room_name = client.current_room
            
            if old_room_name == "default":
                return None  # Already in default room
            
            old_room = self.rooms.get(old_room_name)
            if old_room:
                old_room.clients.discard(username)
            
            client.current_room = "default"
            self.rooms["default"].clients.add(username)
            return old_room_name
        
    async def get_room_clients(self, room_name: str) -> Set[str]:
        """get the list of clients in a specific room."""
        async with self.lock:
            room = self.rooms.get(room_name)
            return room.clients.copy() if room else set()
    
    async def get_client_room(self, username: str) -> Optional[str]:
        """get the current room of a specific client."""
        client = self.clients.get(username)
        return client.current_room if client else None
    
    async def get_clent_websocket(self, username: str):
        """get the websocket of a specific client."""
        client = self.clients.get(username)
        return client.websocket if client else None
    
    async def list_rooms(self) -> Set[str]:
        """list all available chat rooms."""
        async with self.lock:
            return {name: len(room.clients) for name, room in self.rooms.items()}
        
    async def get_username(self, websocket ) -> Optional[str]:
        """get the username associated with a websocket."""
        return self.websocket_to_username.get(websocket)
    
    def __repr__(self):
        return f"ServerState(rooms={self.rooms}, clients={list(self.clients.keys())})"