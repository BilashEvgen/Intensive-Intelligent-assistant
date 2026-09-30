import json
import os

from core.utils.voice_engine import speak_async, speak_task
from core.utils.voice_input import get_voice_input
from core.utils.fuzzy_match import similarity
from core.utils.answer_classify import is_confirm, is_deny
from core.utils.default_commands import DEFAULT_COMMANDS_PATH

NEGATION_PREFIXES = ("не", "ні", "ані")

TYPE_LABELS = {
    "confirm": "підтвердити",
    "deny": "скасувати",
}

LEARN_ATTEMPTS = 3


def looks_like_negation(word: str) -> bool:
    """Перевіряє заперечні префікси слова."""
    word = word.lower().strip()

    if word in ("не", "ні"):
        return True

    for prefix in NEGATION_PREFIXES:
        if word.startswith(prefix) and len(word) > len(prefix) + 1:
            return True

    return False


def guess_word_type(word: str, commands: dict) -> str:
    """Визначає тип нового слова: підтвердження або заперечення."""
    word = (word or "").lower().strip()

    if not word:
        return "confirm"

    if looks_like_negation(word):
        return "deny"

    best_confirm = max(
        (similarity(word, w) for w in commands.get("confirm", [])), default=0.0
    )
    best_deny = max(
        (similarity(word, w) for w in commands.get("deny", [])), default=0.0
    )

    return "deny" if best_deny > best_confirm else "confirm"


def sample_word(commands: dict, category: str) -> str:
    """Повертає зразок слова для категорії."""
    words = commands.get(category, [])
    if words:
        return words[0]
    return "так" if category == "confirm" else "ні"


def learn_new_word(word: str, commands: dict, source, recognizer, stdout=None, max_attempts: int = LEARN_ATTEMPTS):
    """Уточнює тип нового слова та додає його до словника команд."""
    word = (word or "").strip()

    if not word:
        return None

    guessed_type = guess_word_type(word, commands)
    action_label = TYPE_LABELS[guessed_type]

    confirm_sample = sample_word(commands, "confirm")
    deny_sample = sample_word(commands, "deny")

    prompt = (
        f'Я так зрозуміла, ви хочете {action_label} дію. '
        f'Скажіть "{confirm_sample}", якщо так, або "{deny_sample}", якщо ні'
    )

    if stdout:
        stdout.write(f'Невідоме слово "{word}", ймовірний тип: {guessed_type}')

    for attempt in range(max_attempts):
        if attempt == 0:
            speak_task(prompt)
        else:
            speak_task(f'Скажіть "{confirm_sample}", якщо так, або "{deny_sample}", якщо ні')

        answer = get_voice_input(source, recognizer, stdout=stdout)

        if answer is None:
            continue

        if is_confirm(answer, commands):
            save_new_word(commands, guessed_type, word, stdout)
            return guessed_type

        if is_deny(answer, commands):
            if stdout:
                stdout.write(f'Здогад щодо слова "{word}" відхилено, не додаю його до бази')
            speak_async(f'Гаразд, не буду додавати слово "{word}"')
            return None

    speak_async("Не вдалося зрозуміти, залишаю без змін")
    return None


def save_new_word(commands: dict, category: str, word: str, stdout=None):
    """Зберігає нове слово в пам'яті та файлі команд."""
    word = word.lower().strip()

    if not word:
        return

    if word in commands.get(category, []):
        return

    commands.setdefault(category, []).append(word)

    try:
        if os.path.exists(DEFAULT_COMMANDS_PATH):
            with open(DEFAULT_COMMANDS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}

        data.setdefault(category, [])
        if word not in data[category]:
            data[category].append(word)

        with open(DEFAULT_COMMANDS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        if stdout:
            stdout.write(f'Нове слово "{word}" додано в категорію "{category}"')

    except (OSError, json.JSONDecodeError) as err:
        if stdout:
            stdout.write(f'Не вдалося зберегти нове слово у файл: {err}')
