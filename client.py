import asyncio
import json
import threading
from tkinter import Listbox, BOTH, END
from tkinter.scrolledtext import ScrolledText

import ttkbootstrap as ttk
import websockets
from ttkbootstrap.constants import *

# ======================================================================================
# Classe pour l'Interface Utilisateur (UI)
# ======================================================================================

class ChatUI:
    """Gère tous les éléments de l'interface graphique avec ttkbootstrap."""
    def __init__(self, on_send_callback, on_connect_callback):
        self.root = ttk.Window(themename="cyborg")
        self.root.title("Chat Client")

        # --- Écran de Connexion ---
        self.login_frame = ttk.Frame(self.root, padding=30)
        self.login_frame.pack(expand=True)

        ttk.Label(self.login_frame, text="Connexion au serveur", font=("Segoe UI", 16, "bold")).pack(pady=10)

        self.entry_ip = ttk.Entry(self.login_frame, width=30)
        self.entry_ip.insert(0, "localhost")
        self.entry_ip.pack(pady=5)

        self.entry_port = ttk.Entry(self.login_frame, width=30)
        self.entry_port.insert(0, "8765")
        self.entry_port.pack(pady=5)

        self.entry_username = ttk.Entry(self.login_frame, width=30)
        self.entry_username.insert(0, "User")
        self.entry_username.pack(pady=5)
        self.entry_username.bind("<Return>", lambda event: on_connect_callback())

        self.on_send_callback = on_send_callback
        self.btn_connect = ttk.Button(self.login_frame, text="Se connecter", bootstyle=SUCCESS, command=on_connect_callback)
        self.btn_connect.pack(pady=10)

        # --- Variables pour l'écran de Chat ---
        self.text_area = None
        self.list_rooms = None
        self.entry_message = None
        self.btn_send = None

    def build_chat_screen(self):
        """Construit l'interface principale du chat après une connexion réussie."""
        self.login_frame.destroy()
        self.root.geometry("800x600")

        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=BOTH, expand=True)

        main_frame.columnconfigure(1, weight=3)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)

        room_frame = ttk.Labelframe(main_frame, text="Salons", padding=5)
        room_frame.grid(row=0, column=0, sticky="nswe", padx=(0, 5))
        room_frame.rowconfigure(0, weight=1)
        room_frame.columnconfigure(0, weight=1)

        self.list_rooms = Listbox(room_frame, bg="#2b2b2b", fg="white", selectbackground="#007bff", borderwidth=0, highlightthickness=0)
        self.list_rooms.grid(row=0, column=0, sticky="nswe")

        chat_frame = ttk.Frame(main_frame)
        chat_frame.grid(row=0, column=1, sticky="nswe", padx=(5, 0))
        chat_frame.rowconfigure(0, weight=1)
        chat_frame.columnconfigure(0, weight=1)

        self.text_area = ScrolledText(chat_frame, height=20, bg="#2b2b2b", fg="white", wrap="word", borderwidth=0, highlightthickness=0)
        self.text_area.grid(row=0, column=0, sticky="nswe")
        self.text_area.configure(state="disabled")

        entry_frame = ttk.Frame(main_frame, padding=(0, 10))
        entry_frame.grid(row=1, column=0, columnspan=2, sticky="we")
        entry_frame.columnconfigure(0, weight=1)

        self.entry_message = ttk.Entry(entry_frame)
        self.entry_message.grid(row=0, column=0, sticky="we", ipady=5)
        self.entry_message.bind("<Return>", lambda event: self.on_send_callback())

        self.btn_send = ttk.Button(entry_frame, text="Envoyer", bootstyle=PRIMARY, command=self.on_send_callback)
        self.btn_send.grid(row=0, column=1, padx=(10, 0))

    def append_message(self, text, tag=None):
        """Ajoute un message à la zone de texte, avec un style optionnel."""
        if not self.text_area: return
        
        self.text_area.configure(state="normal")
        self.text_area.insert(END, text + "\n", tag)
        self.text_area.configure(state="disabled")
        self.text_area.see(END)

    def display_message(self, username, message, is_self=False):
        """Affiche un message formaté dans la zone de texte."""
        if not self.text_area: return

        user_tag = 'self_username' if is_self else 'username'
        msg_tag = 'self_msg' if is_self else 'user_msg'
        display_username = "Vous" if is_self else username

        self.text_area.configure(state="normal")
        self.text_area.insert(END, f'[{display_username}]: ', user_tag)
        self.text_area.insert(END, f'{message}\n', msg_tag)
        self.text_area.configure(state="disabled")
        self.text_area.see(END)

    def configure_styles(self):
        """Définit les styles (couleurs, polices) pour les différents types de messages."""
        if not self.text_area: return
        self.text_area.tag_config('system', foreground="#00bfff", font=('Segoe UI', 9, 'italic'))
        self.text_area.tag_config('error', foreground="#ff4d4d", font=('Segoe UI', 9, 'bold'))
        self.text_area.tag_config('user_msg', foreground="#cccccc")
        self.text_area.tag_config('username', foreground="#007bff", font=('Segoe UI', 9, 'bold'))
        self.text_area.tag_config('self_msg', foreground="white", font=('Segoe UI', 9, 'italic'))
        self.text_area.tag_config('self_username', foreground="#17a2b8", font=('Segoe UI', 9, 'bold'))

# ======================================================================================
# Classe pour la Gestion du Réseau
# ======================================================================================

class ChatNetwork:
    """Gère la connexion WebSocket, l'envoi et la réception de messages."""
    def __init__(self):
        self.ws = None

    async def connect(self, uri, username):
        """Établit la connexion WebSocket et envoie le message d'enregistrement."""
        self.ws = await websockets.connect(uri)
        await self.ws.send(json.dumps({"username": username}))
        
        response_json = await self.ws.recv()
        response = json.loads(response_json)
        
        if response.get("action") == "error":
            raise ConnectionRefusedError(response['data']['error'])

    async def send_json(self, message: dict):
        """Envoie un message au format JSON au serveur."""
        if self.ws and self.ws.open:
            await self.ws.send(json.dumps(message))
            
    async def close(self):
        """Ferme la connexion WebSocket."""
        if self.ws:
            await self.ws.close()
            self.ws = None

    async def receive_loop(self, on_message_callback):
        """Boucle infinie pour écouter les messages du serveur."""
        try:
            while True:
                raw_msg = await self.ws.recv()
                server_msg = json.loads(raw_msg)
                on_message_callback(server_msg)
        except websockets.exceptions.ConnectionClosed:
            on_message_callback({"action": "system", "data": {"message": "Connexion perdue avec le serveur."}})
        except Exception as e:
            on_message_callback({"action": "error", "data": {"error": f"Erreur réseau: {e}"}})

# ======================================================================================
# Classe Principale de l'Application Client
# ======================================================================================

class ChatClientApp:
    """Orchestre l'UI, le réseau et la logique de l'application."""
    def __init__(self):
        self.ui = ChatUI(on_send_callback=self.schedule_send_message, on_connect_callback=self.connect)
        self.network = ChatNetwork()
        self.username = None
        self.current_room = "general"
        self.loop = None
        self.main_task = None
        self.is_running = True
        self.ui.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        """Gère la fermeture propre de l'application."""
        self.is_running = False
        if self.loop and self.loop.is_running() and self.main_task:
            try:
                self.loop.call_soon_threadsafe(self.main_task.cancel)
            except RuntimeError:
                pass
        self.ui.root.destroy()

    def connect(self):
        """Lance le processus de connexion au serveur."""
        ip, port = self.ui.entry_ip.get(), self.ui.entry_port.get()
        self.username = self.ui.entry_username.get().strip()
        if not self.username:
            self.ui.append_message("❌ Veuillez entrer un nom d'utilisateur", 'error')
            return
        
        self.ui.build_chat_screen()
        self.ui.configure_styles()
        
        threading.Thread(target=self.run_async_client, args=(f"ws://{ip}:{port}",), daemon=True).start()

    def run_async_client(self, uri):
        """Point d'entrée pour le thread réseau asyncio."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        self.main_task = self.loop.create_task(self.websocket_handler(uri))
        
        try:
            self.loop.run_until_complete(self.main_task)
        except asyncio.CancelledError:
            pass
        finally:
            tasks = [t for t in asyncio.all_tasks(self.loop) if t is not self.main_task]
            if tasks:
                for task in tasks: task.cancel()
                self.loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            self.loop.close()

    async def websocket_handler(self, uri):
        """Gère le cycle de vie de la connexion WebSocket."""
        try:
            await self.network.connect(uri, self.username)
            self.ui.root.after(0, lambda: self.ui.append_message(f"Connecté en tant que {self.username}.", 'system'))
            await self.network.receive_loop(self.handle_message_from_network)
        except (ConnectionRefusedError, OSError, websockets.exceptions.InvalidURI) as e:
            if self.is_running:
                self.ui.root.after(0, lambda: self.ui.append_message(f"Impossible de se connecter: {e}", 'error'))
        except asyncio.CancelledError:
            raise
        finally:
            await self.network.close()

    def schedule_send_message(self):
        """Planifie l'envoi d'un message depuis le thread de l'UI vers le thread réseau."""
        if self.loop and self.is_running and self.loop.is_running():
            msg = self.ui.entry_message.get().strip()
            if msg:
                self.ui.entry_message.delete(0, END)
                # Affiche le message localement avant de l'envoyer
                self.ui.display_message(self.username, msg, is_self=True)
                try:
                    self.loop.call_soon_threadsafe(self.process_message_for_sending, msg)
                except RuntimeError:
                    pass

    def process_message_for_sending(self, msg: str):
        """Traite le message (commande ou texte) et l'envoie via le réseau."""
        if not self.is_running: return

        coro = self.handle_command(msg) if msg.startswith("/") else self.network.send_json({"action": "send_message", "data": {"message": msg}})

        if coro:
            asyncio.create_task(coro)

    def handle_command(self, cmd: str):
        """Interprète les commandes utilisateur (ex: /join, /create)."""
        parts = cmd[1:].split()
        if not parts: return None
        
        command, args = parts[0].lower(), parts[1:]
        action, data = None, {}
        
        if command == "join" and args:
            self.current_room = args[0]
            action, data = "join_room", {"room_name": self.current_room}
        elif command == "create" and args:
            action, data = "create_room", {"room_name": args[0]}
        elif command == "leave":
            self.current_room = "general"
            action = "leave_room"
        elif command == "rooms":
            action = "list_rooms"
        elif command == "help":
            self.ui.root.after(0, self.show_help)
        else:
            self.ui.root.after(0, lambda: self.ui.append_message(f"Commande inconnue: {cmd}", 'error'))
        
        if action:
            return self.network.send_json({"action": action, "data": data})
        return None

    def show_help(self):
        """Affiche les commandes disponibles dans l'UI."""
        self.ui.append_message("--- Aide ---", 'system')
        self.ui.append_message("/join <salon>  - Rejoindre un salon", 'system')
        self.ui.append_message("/create <salon> - Créer un salon", 'system')
        self.ui.append_message("/leave          - Quitter (retourne au salon 'general')", 'system')
        self.ui.append_message("/rooms          - Lister les salons", 'system')
        self.ui.append_message("--- Fin ---", 'system')

    def handle_message_from_network(self, msg: dict):
        """Callback pour traiter les messages reçus du serveur."""
        if self.is_running:
            self.ui.root.after(0, self.process_ui_update, msg)

    def process_ui_update(self, msg: dict):
        """Met à jour l'interface graphique en fonction du message reçu."""
        if not self.ui.text_area or not self.is_running: return
        
        action = msg.get("action")
        data = msg.get("data", {})

        if action == "receive_message":
            # Ne pas afficher les messages que l'on a soi-même envoyés (car déjà affichés localement)
            if data.get("username") == self.username:
                return  # On ignore notre propre message
            
            if data.get("room_name") == self.current_room:
                self.ui.display_message(data.get("username"), data.get("message"))
        elif action == "list_rooms":
            rooms_data = data.get("rooms", {})
            if self.ui.list_rooms:
                self.ui.list_rooms.delete(0, END)
                for room_name in sorted(rooms_data.keys()):
                    self.ui.list_rooms.insert(END, f" {room_name} ({rooms_data[room_name]})")
        elif action in ("system", "success", "error"):
            tag = 'system'
            content = data.get("message", data.get("error", "Message système non spécifié."))
            if action == "error": tag = 'error'
            self.ui.append_message(content, tag)

    def run(self):
        """Lance la boucle principale de l'interface graphique."""
        self.ui.root.mainloop()


if __name__ == "__main__":
    app = ChatClientApp()
    app.run()
