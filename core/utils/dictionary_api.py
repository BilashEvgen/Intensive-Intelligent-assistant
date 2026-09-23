# Звернення до публічного API словника LanguageTool (https://languagetool.org),
# який серед іншого підтримує українську мову і для "підозрілого"/невідомого
# слова повертає список слів-замін, які він вважає найбільш ймовірними
# (по суті - орфографічний словник із перевіркою схожості).
#
# Використовуємо це, щоб коли розпізнане голосом слово не знайшлось як назва
# застосунку, не питати користувача "по буквах", а одразу підказати кілька
# найбільш підходящих варіантів зі словника.

import requests

from core.utils.local_dictionary import find_similar_words

LANGUAGETOOL_URL = "https://api.languagetool.org/v2/check"
LANGUAGETOOL_LANGUAGE = "uk-UA"
REQUEST_TIMEOUT = 5.0


def fetch_dictionary_suggestions(word: str, language: str = LANGUAGETOOL_LANGUAGE) -> list:
    """
    Відправляє слово в API словника і повертає ПОВНИЙ список слів-варіантів,
    відсортований API за ймовірністю (найбільш підходящі - на початку).

    Якщо слово вже коректне (словник не бачить помилки) або сталась мережева
    помилка - повертає порожній список.
    """
    word = (word or "").strip()
    if not word:
        return []

    try:
        response = requests.post(
            LANGUAGETOOL_URL,
            data={"text": word, "language": language},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        # мережа недоступна / API впало / таймаут - просто немає підказок
        return []

    suggestions = []
    seen = set()

    # "matches" - список знайдених "помилок" у тексті. Для одного слова
    # зазвичай буде щонайбільше один match (сама перевірка орфографії),
    # але на випадок кількох - перебираємо всі і збираємо їх заміни разом.
    for match in data.get("matches", []):
        for replacement in match.get("replacements", []):
            value = replacement.get("value", "").strip()
            key = value.lower()
            if value and key != word.lower() and key not in seen:
                seen.add(key)
                suggestions.append(value)

    return suggestions


def get_suggestions_for_word(word: str, language: str = LANGUAGETOOL_LANGUAGE, local_limit: int = 15) -> list:
    """
    Основне джерело варіантів для голосового підбору слова.

    1) Спочатку - локальний перебір словника (find_similar_words): знаходить
       слова, схожі за написанням/звучанням, НЕЗАЛЕЖНО від того, чи саме
       почуте слово існує в мові. Це головний сценарій ("рака" почулось
       замість "рука").
    2) Потім - API словника LanguageTool: якщо почуте слово - орфографічна
       помилка (не існує взагалі), додає його офіційні виправлення.

    Списки об'єднуються без дублікатів, локальні варіанти йдуть першими.
    """
    word = (word or "").strip()
    if not word:
        return []

    local_matches = find_similar_words(word, limit=local_limit)
    api_matches = fetch_dictionary_suggestions(word, language=language)

    merged = []
    seen = {word.lower()}
    for candidate in local_matches + api_matches:
        key = candidate.lower()
        if key not in seen:
            seen.add(key)
            merged.append(candidate)

    return merged


def get_next_suggestions(all_suggestions: list, offset: int, limit: int = 3) -> tuple:
    """
    Дістає з уже отриманого списку варіантів наступну "пачку" (сторінку) -
    це і є "перебір" словника: кожен виклик з новим offset повертає інші
    варіанти, не показані раніше.

    Повертає (batch, new_offset).
    """
    batch = all_suggestions[offset: offset + limit]
    return batch, offset + limit
