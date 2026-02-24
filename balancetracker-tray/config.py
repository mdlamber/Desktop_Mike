import json
import os

CONFIG_PATH = os.path.expanduser('~/.config/balancetracker-tray/config.json')

DEFAULTS = {
    'client_id': '',
    'client_secret': '',
    'refresh_token': '',
    'backend_url': 'http://localhost:3000',
}

def load_config(path: str = CONFIG_PATH) -> dict:
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        return {**DEFAULTS, **data}
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(DEFAULTS)

def save_config(data: dict, path: str = CONFIG_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
