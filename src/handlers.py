from typing import Dict, Any
from src.protocol import ProtocolMessage, ActionType
from src.server_state import ServerState
from src.logger import log_info, log_warning, log_error
import asyncio

class MessageHandler:
    """Gestionnaire des messages selon le protocole."""

    def __init__(self, state: ServerState):
        self.state = state

    async def handle_message(self, websocket, message: ProtocolMessage) -> ProtocolMessage:
        """Traiter un message selon son action."""
        action = message.action
        data = message.data

        try:
            if action == ActionType.CREATE_ROOM.value:
                return await self.handle_create_room(data)
            elif action == ActionType.JOIN_ROOM.value:
                return await self.handle_join_room(websocket, data)
            elif action == ActionType.LEAVE_ROOM.value:
                return await self.handle_leave_room(websocket)
            elif action == ActionType.SEND_MESSAGE.value:
                return await self.handle_send_message(websocket, data)
            elif action == ActionType.LIST_ROOMS.value:
                return await self.handle_list_rooms()
            elif action == ActionType.LIST_USERS.value:
                return await self.handle_list_users(data)
            else:
                log_warning(f"Action inconnue: {action}")
                return ProtocolMessage.create_error(f"Action inconnue: {action}")
        except Exception as e:
            log_error(f"Erreur lors du traitement du message: {e}")
            return ProtocolMessage.create_error(f"Erreur interne: {str(e)}")

    async def handle_create_room(self, data: Dict[str, Any]) -> ProtocolMessage:
        """Créer un nouveau salon."""
        room_name = data.get("room_name")
        if not room_name:
            return ProtocolMessage.create_error("Nom de salon manquant")

        success = await self.state.create_room(room_name)
        if success:
            log_info(f"✓ Salon créé: {room_name}")
            return ProtocolMessage.create_success(
                f"Salon '{room_name}' créé avec succès",
                {"room_name": room_name}
            )
        else:
            log_warning(f"✗ Tentative de création d'un salon existant: {room_name}")
            return ProtocolMessage.create_error(f"Le salon '{room_name}' existe déjà")

    async def handle_join_room(self, websocket, data: Dict[str, Any]) -> ProtocolMessage:
        """Rejoindre un salon."""
        room_name = data.get("room_name")
        username = await self.state.get_username_from_websocket(websocket)

        if not room_name:
            return ProtocolMessage.create_error("Nom de salon manquant")
        if not username:
            return ProtocolMessage.create_error("Utilisateur non connecté")

        success = await self.state.join_room(username, room_name)
        if success:
            log_info(f"✓ {username} a rejoint le salon: {room_name}")
            await self.broadcast_to_room(
                room_name,
                ProtocolMessage(
                    action=ActionType.RECEIVE_MESSAGE.value,
                    data={
                        "room_name": room_name,
                        "username": "SYSTÈME",
                        "message": f"{username} a rejoint le salon"
                    }
                ),
                exclude_username=username
            )
            return ProtocolMessage.create_success(
                f"Vous avez rejoint le salon '{room_name}'",
                {"room_name": room_name}
            )
        else:
            log_warning(f"✗ {username} n'a pas pu rejoindre: {room_name}")
            return ProtocolMessage.create_error(f"Impossible de rejoindre '{room_name}'")

    async def handle_leave_room(self, websocket) -> ProtocolMessage:
        """Quitter le salon actuel."""
        username = await self.state.get_username_from_websocket(websocket)
        if not username:
            return ProtocolMessage.create_error("Utilisateur non connecté")

        old_room = await self.state.leave_room(username)
        if old_room:
            log_info(f"✓ {username} a quitté le salon: {old_room}")
            await self.broadcast_to_room(
                old_room,
                ProtocolMessage(
                    action=ActionType.RECEIVE_MESSAGE.value,
                    data={
                        "room_name": old_room,
                        "username": "SYSTÈME",
                        "message": f"{username} a quitté le salon"
                    }
                )
            )
            return ProtocolMessage.create_success(
                f"Vous avez quitté '{old_room}' et êtes retourné au salon par défaut",
                {"old_room": old_room, "new_room": "default"}
            )
        else:
            return ProtocolMessage.create_error("Vous êtes déjà dans le salon par défaut")

    async def handle_send_message(self, websocket, data: Dict[str, Any]) -> ProtocolMessage:
        """Envoyer un message dans le salon actuel."""
        username = await self.state.get_username_from_websocket(websocket)
        message_text = data.get("message")

        if not username:
            return ProtocolMessage.create_error("Utilisateur non connecté")
        if not message_text:
            return ProtocolMessage.create_error("Message vide")

        room_name = await self.state.get_client_room(username)
        if not room_name:
            return ProtocolMessage.create_error("Vous n'êtes dans aucun salon")

        log_info(f"💬 [{room_name}] {username}: {message_text}")
        broadcast_message = ProtocolMessage(
            action=ActionType.RECEIVE_MESSAGE.value,
            data={
                "room_name": room_name,
                "username": username,
                "message": message_text
            }
        )
        await self.broadcast_to_room(room_name, broadcast_message)
        return ProtocolMessage.create_success("Message envoyé")

    async def handle_list_rooms(self) -> ProtocolMessage:
        """Lister tous les salons disponibles."""
        rooms = await self.state.list_rooms()
        log_info(f"📋 Liste des salons demandée: {len(rooms)} salons")
        return ProtocolMessage.create_success(
            "Liste des salons",
            {"rooms": rooms}
        )

    async def handle_list_users(self, data: Dict[str, Any]) -> ProtocolMessage:
        """Lister les utilisateurs d'un salon."""
        room_name = data.get("room_name", "default")
        users = await self.state.get_room_clients(room_name)
        log_info(f"👥 Liste des utilisateurs du salon '{room_name}': {len(users)} utilisateurs")
        return ProtocolMessage.create_success(
            f"Utilisateurs dans '{room_name}'",
            {"room_name": room_name, "users": list(users)}
        )

    async def broadcast_to_room(self, room_name: str, message: ProtocolMessage, exclude_username: str = None):
        """Diffuser un message à tous les membres d'un salon."""
        clients = await self.state.get_room_clients(room_name)
        send_tasks = []
        for username in clients:
            if username == exclude_username:
                continue
            ws = await self.state.get_client_websocket(username)
            if ws:
                send_tasks.append(self.send_message(ws, message))
        if send_tasks:
            await asyncio.gather(*send_tasks, return_exceptions=True)

    @staticmethod
    async def send_message(websocket, message: ProtocolMessage):
        """Envoyer un message à un websocket."""
        try:
            await websocket.send(message.to_json())
        except Exception as e:
            log_error(f"Erreur lors de l'envoi du message: {e}")
