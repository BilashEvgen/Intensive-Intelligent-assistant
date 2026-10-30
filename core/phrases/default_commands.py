import os
from core.phrases.phrase_db import load_phrases
DEFAULT_COMMANDS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "default_commands.json",
)
def load_default_commands():
    return load_phrases()