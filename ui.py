import ttkbootstrap as ttk
from ttkbootstrap.constants import *

class ChatUI:
    def __init__(self):
        self.root = ttk.Window(themename="cyborg")
        self.root.title("Chat Client - Login")

        frame = ttk.Frame(self.root, padding=30)
        frame.pack(expand=True)

        self.entry_ip = ttk.Entry(frame, width=30)
        self.entry_ip.insert(0, "localhost")
        self.entry_ip.pack(pady=5)

        self.entry_port = ttk.Entry(frame, width=30)
        self.entry_port.insert(0, "8765")
        self.entry_port.pack(pady=5)

        self.entry_username = ttk.Entry(frame, width=30)
        self.entry_username.insert(0, "User")
        self.entry_username.pack(pady=5)

        self.btn_connect = ttk.Button(frame, text="Connect", bootstyle=SUCCESS)
        self.btn_connect.pack(pady=10)

    def run(self):
        self.root.mainloop()

    def build_chat_screen(self):
        self.root.title("Chat Client")

        # Efface écran login
        for w in self.root.winfo_children():
            w.destroy()

        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=BOTH, expand=True)

        # Liste salons
        room_frame = ttk.Labelframe(main, text="Rooms")
        room_frame.pack(side=LEFT, fill=Y, padx=5)

        self.list_rooms = ttk.Listbox(room_frame)
        self.list_rooms.pack(fill=BOTH, expand=True, padx=5, pady=5)

        # Zone messages
        msg_frame = ttk.Labelframe(main, text="Messages")
        msg_frame.pack(side=RIGHT, fill=BOTH, expand=True)

        from ttkbootstrap.scrolled import ScrolledText
        self.text_area = ScrolledText(msg_frame, height=20)
        self.text_area.pack(fill=BOTH, expand=True, padx=5, pady=5)

        # Champ message
        bottom = ttk.Frame(main)
        bottom.pack(fill=X, pady=5)

        self.entry_message = ttk.Entry(bottom)
        self.entry_message.pack(side=LEFT, fill=X, expand=True, padx=5)

        self.btn_send = ttk.Button(bottom, text="Send", bootstyle=PRIMARY)
        self.btn_send.pack(side=RIGHT, padx=5)
