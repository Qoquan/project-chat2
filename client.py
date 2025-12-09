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
        self.current_room = "default"
        self.loop = None

        # Attacher la commande de connexion
        self.ui.btn_connect.configure(command=self.connect)

    # --- Connexion serveur ---
    def connect(self):
        ip = self.ui.entry_ip.get()
        port = self.ui.entry_port.get()
        self.username = self.ui.entry_username.get().strip()
        if not self.username:
            print("❌ Veuillez entrer un nom d'utilisateur")
            return

        uri = f"ws://{ip}:{port}"

        # Construire le chat screen avant le réseau
        self.ui.build_chat_screen()

        # Thread pour le réseau
        threading.Thread(target=self.run_async_client, args=(uri,), daemon=True).start()

    def run_async_client(self, uri):
        """Lance la boucle asyncio dans un thread séparé"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.websocket_handler(uri))
        except Exception as e:
            print(f"❌ Erreur de connexion: {e}")
            self.ui.append_message(f"❌ Impossible de se connecter: {e}")

    async def websocket_handler(self, uri):
        """Gère la connexion WebSocket"""
        try:
            await self.network.connect(uri, self.username)
            self.ui.append_message(f"✓ Connecté en tant que {self.username}")
            self.ui.append_message(f"✓ Vous êtes dans le salon '{self.current_room}'")
            
            # Charger la liste des salons
            await self.network.list_rooms()
            
            # Démarrer la boucle de réception
            await self.network.receive_loop(self.handle_message)
        except Exception as e:
            self.ui.append_message(f"❌ Erreur: {e}")
            raise

    # --- Envoi message ---
    def send_message(self):
        """Envoie un message ou traite une commande"""
        msg = self.ui.entry_message.get().strip()
        if not msg:
            return

        # Vérifier si c'est une commande
        if msg.startswith("/"):
            self.handle_command(msg)
        else:
            # Envoyer le message normal
            asyncio.run_coroutine_threadsafe(
                self.network.send_message(self.username, msg),
                self.loop
            )
        
        self.ui.entry_message.delete(0, "end")
    def handle_command(self, cmd):
        """Traite les commandes spéciales"""
        parts = cmd[1:].split()
        if not parts:
            return
        
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        if command == "join" and args:
            # Rejoindre un salon
            room_name = args[0]
            asyncio.run_coroutine_threadsafe(
                self.network.join_room(room_name),
                self.loop
            )
            self.current_room = room_name
            self.ui.append_message(f"📍 Tentative de rejoindre '{room_name}'...")
        
        elif command == "create" and args:
            # Créer un salon
            room_name = args[0]
            asyncio.run_coroutine_threadsafe(
                self.network.create_room(room_name),
                self.loop
            )
            self.ui.append_message(f"🏗️ Tentative de création du salon '{room_name}'...")
        
        elif command == "leave":
            # Quitter le salon actuel
            asyncio.run_coroutine_threadsafe(
                self.network.leave_room(),
                self.loop
            )
            self.current_room = "default"
            self.ui.append_message(f"🚪 Retour au salon par défaut...")
        
        elif command == "rooms":
            # Lister les salons
            asyncio.run_coroutine_threadsafe(
                self.network.list_rooms(),
                self.loop
            )
            self.ui.append_message("📋 Chargement de la liste des salons...")
        
        elif command == "help":
            # Afficher l'aide
            self.ui.append_message("=== COMMANDES DISPONIBLES ===")
            self.ui.append_message("/join <salon>  - Rejoindre un salon")
            self.ui.append_message("/create <salon> - Créer un nouveau salon")
            self.ui.append_message("/leave          - Quitter le salon actuel")
            self.ui.append_message("/rooms          - Lister tous les salons")
            self.ui.append_message("/help           - Afficher cette aide")
        
        else:
            self.ui.append_message(f"❌ Commande inconnue: /{command}")
            self.ui.append_message("Tapez /help pour voir les commandes disponibles")
    # --- Traitement message reçu ---
    def handle_message(self, msg):
        """Traite les messages reçus du serveur"""
        action = msg.get("action")
        
        if action == "receive_message":
            # Message de chat normal
            user = msg.get("user", "?")
            content = msg.get("content", "")
            room = msg.get("room", self.current_room)
            
            # Afficher seulement si c'est dans le salon actuel
            if room == self.current_room:
                self.ui.append_message(f"[{user}]: {content}")
        
        elif action == "system":
            # Message système
            content = msg.get("content", "")
            self.ui.append_message(f"* {content} *")
        
        elif action == "list_rooms":
            # Mise à jour de la liste des salons
            rooms = msg.get("rooms", [])
            self.ui.list_rooms.delete(0, "end")
            for room in rooms:
                self.ui.list_rooms.insert("end", room)
            self.ui.append_message(f"📋 {len(rooms)} salon(s) disponible(s)")

    def run(self):
        """Lance l'application"""
        self.ui.root.mainloop()


if __name__ == "__main__":
    app = ChatClientApp()
    app.run()
