
import random

from core.utils.answer_classify import is_cancel, normalize_words
from core.utils.fuzzy_match import extract_app_name

MAX_ATTEMPTS = 2
LISTEN_SECONDS = 4
PRE_DELAY = 0.1

# Кілька варіантів кожного питання, щоб асистент не повторювався і говорив коротко
QUESTIONS = {
    "open": [
        "Що відкрити?",
        "Яку програму відкрити?",
        "Що саме відкрити?",
        "Назвіть програму.",
        "Яку саме програму?",
    ],
    "close": [
        "Що закрити?",
        "Яку програму закрити?",
        "Що саме закрити?",
        "Назвіть програму.",
        "Яку саме закрити?",
    ],
}

# Питання, якщо відповіді не було або назву не вдалося виділити
RETRY_QUESTIONS = [
    "Не почула. Яку програму?",
    "Повторіть назву.",
    "Ще раз, яку програму?",
    "Не розібрала. Назву ще раз?",
]

CANCEL_REPLIES = ["Гаразд.", "Добре, скасувала.", "Окей, не буду."]
GIVE_UP_REPLIES = ["Не почула назву. Скажіть команду ще раз.", "Не вийшло. Спробуйте ще раз."]

# Слова, які користувач може додати до назви ("відкрий мені програму хром, будь ласка")
FILLER_WORDS = {"будь", "ласка", "мені", "ну", "програму", "застосунок", "додаток", "її", "його", "це", "оцю"}
# Відповіді, якими користувач відмовляється від команди
REFUSAL_WORDS = {"ні", "нє", "не", "нічого", "неважливо", "no"}

ALL_PHRASES = (
    [text for group in QUESTIONS.values() for text in group]
    + RETRY_QUESTIONS + CANCEL_REPLIES + GIVE_UP_REPLIES
)

last_said = {}


def pick_phrase(options: list, group: str = "") -> str:
    """Випадкова фраза, яка не збігається з попередньою з цієї групи."""
    last = last_said.get(group)
    pool = [text for text in options if text != last] or options
    choice = random.choice(pool)
    last_said[group] = choice
    return choice


def is_refusal(text: str, commands: dict) -> bool:
    """Перевіряє відмову, не плутаючи її з назвою програми."""
    if is_cancel(text, commands):
        return True
    words = [w for w in normalize_words(text) if w]
    return bool(words) and all(word in REFUSAL_WORDS for word in words)


def clean_names(variants: list, action: str, commands: dict) -> list:
    """Видаляє службові слова, залишаючи назви програм."""
    names = []

    for text in variants:
        name = extract_app_name(text.lower().strip(), commands[action])
        words = [w for w in name.split() if w.strip(",.!?") not in FILLER_WORDS]
        name = "".join(words).strip(" ,.!?")

        if name and name not in names:
            names.append(name)

    return names


def ask_app_name(action: str, commands: dict, listen, say, stdout=None, max_attempts: int = MAX_ATTEMPTS):
    """Уточнює назву програми та повертає варіанти або None."""
    question = pick_phrase(QUESTIONS[action], f"q_{action}")

    for attempt in range(max_attempts):
        say(question)
        variants = listen()

        if not variants:
            question = pick_phrase(RETRY_QUESTIONS, "retry")
            continue

        if stdout:
            stdout.write(f"Відповідь на уточнення: {variants[0]}")

        if is_refusal(variants[0], commands):
            say(pick_phrase(CANCEL_REPLIES, "cancel"))
            return None

        names = clean_names(variants, action, commands)

        if names:
            return names

        question = pick_phrase(RETRY_QUESTIONS, "retry")

    say(pick_phrase(GIVE_UP_REPLIES, "give_up"))
    return None
