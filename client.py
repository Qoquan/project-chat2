import threading
import asyncio
from ui import ChatUI
from network import ChatNetwork  # ton module réseau

class ChatClientApp:
    def __init__(self):
        # UI avec callback
        self.ui = ChatUI(on_send_callback=self.send_message)
        self.network = ChatNetwork()
        self.username = None
        self.current_room = "general"

        # Attacher la commande de connexion
        self.ui.btn_connect.configure(command=self.connect)

    # --- Connexion serveur ---
    def connect(self):
        ip = self.ui.entry_ip.get()
        port = self.ui.entry_port.get()
        self.username = self.ui.entry_username.get().strip()
        if not self.username:
            return

        uri = f"ws://{ip}:{port}"

        # Construire le chat screen avant le réseau
        self.ui.build_chat_screen()

        # Thread pour le réseau
        threading.Thread(target=self.run_async_client, args=(uri,), daemon=True).start()

    def run_async_client(self, uri):
        asyncio.run(self.websocket_handler(uri))

    async def websocket_handler(self, uri):
        await self.network.connect(uri, self.username)
        await self.network.receive_loop(self.handle_message)

    # --- Envoi message ---
    def send_message(self):
        msg = self.ui.entry_message.get().strip()
        if not msg:
            return

        asyncio.run_coroutine_threadsafe(
            self.network.send_message(self.current_room, self.username, msg),
            asyncio.get_event_loop()
        )
        self.ui.entry_message.delete(0, "end")

    # --- Traitement message reçu ---
    def handle_message(self, msg):
        action = msg.get("action")
        if action == "receive_message":
            self.ui.append_message(f"[{msg['user']}] : {msg['content']}")
        elif action == "system":
            self.ui.append_message(f"* {msg['content']} *")
        elif action == "list_rooms":
            self.ui.list_rooms.delete(0, "end")
            for room in msg.get("rooms", []):
                self.ui.list_rooms.insert("end", room)

    def run(self):
        self.ui.root.mainloop()


if __name__ == "__main__":
    app = ChatClientApp()
    app.run()
