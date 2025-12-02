import asyncio
import websockets
import json
from collections import defaultdict

# ===========================
# Structures de données
# ===========================
rooms = defaultdict(set)      # salon -> set de websockets
clients = dict()              # websocket -> username
rooms["general"] = set()      # salon par défaut

# ===========================
# Fonctions utilitaires
# ===========================
async def broadcast(room, message):
    """Envoyer message à tous les clients d'un salon"""
    if room not in rooms:
        return
    for ws in rooms[room]:
        try:
            await ws.send(json.dumps(message))
        except:
            pass  # ignorer les erreurs

# ===========================
# Handler principal
# ===========================
async def handler(ws):
    try:
        # --- login initial ---
        data = await ws.recv()
        msg = json.loads(data)
        user = msg.get("user", "Unknown")
        room = msg.get("room", "general")

        clients[ws] = user
        rooms[room].add(ws)
        print(f"[SERVER] {user} rejoint {room}")

        await broadcast(room, {"action": "system", "content": f"{user} a rejoint {room}"})

        # --- boucle réception messages ---
        async for message in ws:
            msg = json.loads(message)
            action = msg.get("action")

            if action == "send_message":
                content = msg.get("content")
                room = msg.get("room", "general")
                await broadcast(room, {
                    "action": "receive_message",
                    "user": clients[ws],
                    "content": content
                })

            elif action == "join_room":
                old_room = None
                for r, ws_set in rooms.items():
                    if ws in ws_set:
                        old_room = r
                        ws_set.remove(ws)
                        await broadcast(r, {"action": "system", "content": f"{clients[ws]} a quitté {r}"})
                        break
                new_room = msg.get("room", "general")
                rooms[new_room].add(ws)
                await broadcast(new_room, {"action": "system", "content": f"{clients[ws]} a rejoint {new_room}"})

            elif action == "list_rooms":
                room_list = list(rooms.keys())
                await ws.send(json.dumps({"action": "list_rooms", "rooms": room_list}))

    except websockets.exceptions.ConnectionClosed:
        print(f"[SERVER] {clients.get(ws, 'Unknown')} déconnecté")
    finally:
        # nettoyage
        for r in rooms.values():
            r.discard(ws)
        if ws in clients:
            del clients[ws]

# ===========================
# Lancement serveur
# ===========================
async def main():
    print("[SERVER] Démarrage serveur Chat sur ws://localhost:8765")
    async with websockets.serve(handler, "localhost", 8765):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
