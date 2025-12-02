import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledText
from tkinter import BOTH, LEFT, RIGHT, Listbox


class ChatUI:
    def __init__(self, on_send_callback):
        self.root = ttk.Window(themename="cyborg")
        self.root.title("Chat Client")

        # --- Login Screen ---
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

        # Callback pour le bouton Envoyer
        self.on_send_callback = on_send_callback

        # Bouton de connexion
        self.btn_connect = ttk.Button(self.login_frame, text="Se connecter", bootstyle=SUCCESS)
        self.btn_connect.pack(pady=10)

        # Variables chat
        self.text_area = None
        self.list_rooms = None
        self.entry_message = None
        self.btn_send = None

    def build_chat_screen(self):
        """Créer l'interface principale chat après connexion"""
        self.login_frame.destroy()

        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=BOTH, expand=True)

        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=4)

        # Liste des salons
        room_frame = ttk.Labelframe(main_frame, text="Salons")
        room_frame.grid(row=0, column=0, sticky="nswe", padx=5, pady=5)

        # Utiliser la Listbox native Tkinter
        self.list_rooms = Listbox(room_frame)
        self.list_rooms.pack(fill=BOTH, expand=True, padx=5, pady=5)

        # Zone messages
        msg_frame = ttk.Labelframe(main_frame, text="Messages")
        msg_frame.grid(row=0, column=1, sticky="nswe", padx=5, pady=5)
        self.text_area = ScrolledText(msg_frame, height=20)
        self.text_area.pack(fill=BOTH, expand=True, padx=5, pady=5)
        self.text_area.configure(state="disabled")

        # Zone d’écriture
        entry_frame = ttk.Frame(main_frame)
        entry_frame.grid(row=1, column=1, sticky="we", pady=5)

        self.entry_message = ttk.Entry(entry_frame)
        self.entry_message.pack(side=LEFT, fill=BOTH, expand=True, padx=5)

        # Bouton Envoyer avec callback attaché
        self.btn_send = ttk.Button(entry_frame, text="Envoyer", bootstyle=PRIMARY, command=self.on_send_callback)
        self.btn_send.pack(side=RIGHT, padx=5)

    def append_message(self, text):
        """Ajouter un message dans la zone texte"""
        self.text_area.configure(state="normal")
        self.text_area.insert("end", text + "\n")
        self.text_area.configure(state="disabled")
        self.text_area.see("end")
