from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
import json
from datetime import datetime, timezone

class ActionType(Enum):
    CREATE_ROOM = "create_room"
    JOIN_ROOM = "join_room"
    LEAVE_ROOM = "leave_room"
    SEND_MESSAGE = "send_message"
    RECEIVE_MESSAGE = "receive_message"
    ERROR = "error"
    SUCCESS = "success"
    LIST_ROOMS = "list_rooms"
    LIST_USERS = "list_users"

@dataclass
class ProtocolMessage:
    """Structure d'un message du protocole."""
    action: str
    data: Dict[str, Any]
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_json(self) -> str:
        """Convertir en JSON."""
        return json.dumps(asdict(self), ensure_ascii=False)

    @staticmethod
    def from_json(json_str: str) -> 'ProtocolMessage':
        """Convertit une chaîne JSON en un objet ProtocolMessage."""
        try:
            data = json.loads(json_str)
            return ProtocolMessage(**data)
        except (json.JSONDecodeError, TypeError) as e:
            # Retourner un message d'erreur si le JSON est invalide
            return ProtocolMessage.create_error(f"Format JSON invalide: {e}")

    @staticmethod
    def create_error(error_msg: str, data: Optional[Dict[str, Any]] = None) -> 'ProtocolMessage':
        """Créer un message d'erreur."""
        payload = {"error": error_msg}
        if data:
            payload.update(data)
        return ProtocolMessage(
            action=ActionType.ERROR.value,
            data=payload
        )

    @staticmethod
    def create_success(info_msg: str, data: Optional[Dict[str, Any]] = None) -> 'ProtocolMessage':
        """Créer un message de succès."""
        payload = {"message": info_msg}
        if data:
            payload.update(data)
        return ProtocolMessage(
            action=ActionType.SUCCESS.value,
            data=payload
        )
