import asyncio
import websockets
import json
from typing import Optional
from src.server_state import ServerState
from src.protocol import ProtocolMessage
from src.handlers import MessageHandler
from src.logger import log_info, log_warning, log_error, log_critical

class ChatServer:
    """Serveur de chat asynchrone avec WebSockets"""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.state = ServerState()
        self.handler = MessageHandler(self.state)
    
    async def register_client(self, websocket) -> Optional[str]:
        """Enregistrer un nouveau client"""
        try:
            # Attendre le premier message avec le username
            message_json = await websocket.recv()
            data = json.loads(message_json)
            
            username = data.get("username")
            if not username:
                await websocket.send(
                    ProtocolMessage.create_error("Username manquant").to_json()
                )
                return None
            
            # Ajouter le client
            success = await self.state.add_client(websocket, username)
            
            if not success:
                await websocket.send(
                    ProtocolMessage.create_error(f"Username '{username}' déjà utilisé").to_json()
                )
                return None
            
            # Confirmer l'enregistrement
            await websocket.send(
                ProtocolMessage.create_success(
                    f"Bienvenue {username}! Vous êtes dans le salon 'default'",
                    {"username": username, "room": "default"}
                ).to_json()
            )
            
            log_info(f"✓ Nouveau client connecté: {username}")
            return username
        
        except Exception as e:
            log_error(f"Erreur lors de l'enregistrement du client: {e}")
            return None
    
    async def handle_client(self, websocket):
        """Gérer la connexion d'un client"""
        username = None
        
        try:
            # Enregistrer le client
            username = await self.register_client(websocket)
            if not username:
                return
            
            # Boucle de réception des messages
            async for message_json in websocket:
                try:
                    # Parser le message
                    message = ProtocolMessage.from_json(message_json)
                    
                    # Traiter le message
                    response = await self.handler.handle_message(websocket, message)
                    
                    # Envoyer la réponse
                    await websocket.send(response.to_json())
                
                except json.JSONDecodeError:
                    log_warning(f"Message JSON invalide reçu de {username}")
                    await websocket.send(
                        ProtocolMessage.create_error("Format JSON invalide").to_json()
                    )
                except Exception as e:
                    log_error(f"Erreur lors du traitement du message de {username}: {e}", exc_info=True)
                    await websocket.send(
                        ProtocolMessage.create_error(f"Erreur serveur: {str(e)}").to_json()
                    )
        
        except websockets.exceptions.ConnectionClosed:
            log_info(f"✗ Connexion fermée: {username or 'inconnu'}")
        
        except Exception as e:
            log_error(f"Erreur inattendue avec le client {username or 'inconnu'}: {e}", exc_info=True)
        
        finally:
            # Nettoyer le client
            if username:
                removed = await self.state.remove_client(websocket)
                if removed:
                    log_info(f"✗ Client déconnecté: {removed}")
    
    async def start(self):
        """Démarrer le serveur"""
        log_info("=" * 60)
        log_info("🚀 SERVEUR DE CHAT")
        log_info("=" * 60)
        log_info(f"Host: {self.host}")
        log_info(f"Port: {self.port}")
        log_info(f"Salon par défaut: default")
        log_info("=" * 60)
        log_info("Le serveur est prêt à accepter des connexions...")
        log_info("")
        
        try:
            async with websockets.serve(self.handle_client, self.host, self.port):
                # Garder le serveur actif indéfiniment
                await asyncio.Future()
        
        except KeyboardInterrupt:
            log_info("\n\n⚠️  Arrêt du serveur demandé...")
        
        except Exception as e:
            log_critical(f"Erreur fatale du serveur: {e}", exc_info=True)
        
        finally:
            log_info("✓ Serveur arrêté")

async def main():
    """Point d'entrée principal"""
    server = ChatServer(host="localhost", port=8765)
    await server.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass