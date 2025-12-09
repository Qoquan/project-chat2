from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
import json
from datetime import datetime

class ActionType(Enum):
    create_room = "create_room"
    join_room = "join_room"
    leave_room = "leave_room" 
    send_message = "send_message"
    receive_message = "receive_message"
    error = "error"
    success = "success"
    list_rooms = "list_rooms"
    list_users = "list_users"
    
@dataclass
class ProtocolMessage:
    """structure d'un message du protocole"""
    action: str
    data: Dict[str, Any]
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()

    def to_json(self) -> str:
        """Convertir en JSON"""
        return json.dumps(asdict(self), ensure_ascii=False)
    
    
@staticmethod
def from_json(json_str: str) -> 'ProtocolMessage':
    """Convertit une chaîne JSON en un objet ProtocolMessage."""
    data = json.loads(json_str)
    return ProtocolMessage(**data)

@staticmethod
def create_error_message(error_msg: str) -> 'ProtocolMessage':
    """Créer un message d'erreur."""
    return ProtocolMessage(
        action=ActionType.erreur.value,
        data={"message": error_msg}
    )

@staticmethod
def create_success_message(info_msg: str) -> 'ProtocolMessage':
    """Créer un message de succès."""
    return ProtocolMessage(
        action=ActionType.success.value,
        data={"message": info_msg}
    )
