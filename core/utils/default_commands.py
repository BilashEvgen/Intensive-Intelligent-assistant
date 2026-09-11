import json
import os

DEFAULT_COMMANDS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "default_commands.json",
)


def load_default_commands() -> dict:
    
    empty = {"open": [], "close": [], "add_command": []}
    try:
        with open(DEFAULT_COMMANDS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for category in empty:
            empty[category] = data.get(category, [])
        return empty
    except (FileNotFoundError, json.JSONDecodeError):
        return empty
