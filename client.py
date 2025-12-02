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

    def send(self):
        msg = self.ui.entry_message.get()
        username = self.ui.entry_username.get()

        asyncio.run_coroutine_threadsafe(
            self.network.send_message("general", username, msg),
            asyncio.get_event_loop()
        )
        self.ui.entry_message.delete(0, "end")


if __name__ == "__main__":
    ChatClientApp().run()
