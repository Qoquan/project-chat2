import json

def make_message(action, **kwargs):
    """Crée un message JSON pour envoyer au serveur"""
    return json.dumps({
        "action": action,
        **kwargs
    })

def parse_message(raw):
    """Parse un message JSON reçu du serveur"""
    return json.loads(raw)
