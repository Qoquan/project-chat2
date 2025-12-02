import json

def make_message(action, **kwargs):
    return json.dumps({
        "action": action,
        **kwargs
    })

def parse_message(raw):
    return json.loads(raw)
