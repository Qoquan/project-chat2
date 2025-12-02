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
