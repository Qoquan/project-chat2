import asyncio
import websockets
from protocol import make_message, parse_message

class ChatNetwork:
    def __init__(self):
        self.ws = None

    async def connect(self, uri, username):
        self.ws = await websockets.connect(uri)

        # Envoi du login
        await self.ws.send(make_message(
            "join_room",
            user=username,
            room="general"
        ))

    async def receive_loop(self, callback):
        while True:
            msg = await self.ws.recv()
            callback(parse_message(msg))

    async def send_message(self, room, user, content):
        await self.ws.send(make_message(
            "send_message",
            room=room,
            user=user,
            content=content
        ))
