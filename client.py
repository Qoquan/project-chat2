import threading
from ui import ChatUI
from network import ChatNetwork
import asyncio

class ChatClientApp:
    def __init__(self):
        self.ui = ChatUI()
        self.network = ChatNetwork()

        self.ui.btn_connect.configure(command=self.connect)

    def connect(self):
        ip = self.ui.entry_ip.get()
        port = self.ui.entry_port.get()
        username = self.ui.entry_username.get()

        uri = f"ws://{ip}:{port}"

        thread = threading.Thread(
            target=self.run_async,
            args=(uri, username),
            daemon=True
        )
        thread.start()

    def run_async(self, uri, username):
        asyncio.run(self.network.connect(uri, username))

    def run(self):
        self.ui.run()

if __name__ == "__main__":
    ChatClientApp().run()
