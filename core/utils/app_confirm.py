from core.utils.voice_engine import speak_async, speak_task
from core.utils.voice_input import get_voice_input
from core.utils.spelling import parse_number
from core.utils.answer_classify import is_cancel, is_confirm, is_deny, is_keep, classify_answer
from core.utils.dictionary_api import get_suggestions_for_word, get_next_suggestions
from core.utils.system_apps import find_matching_apps
from core.utils.app_usage import get_primary_catalog, pick_top_suggestion

SUGGESTIONS_PAGE_SIZE = 3

def display_name(item) -> str:
    """Повертає назву варіанта для показу."""
    return item["name"] if isinstance(item, dict) else item

def offer_top_app(
    app: dict,
    reason: str,
    source,
    recognizer,
    commands: dict,
    stdout=None,
    max_attempts: int = 3,
    max_no_response: int = 3,
):
    """Пропонує відкрити одразу найкращий застосунок.

    Повертає: "accept" - відкрити, "deny" - показати список,
    "keep" - залишити слово як є, "cancel" - зупинити підбір.
    """
    name = display_name(app)

    if reason == "usage":
        prompt = f"Ви часто відкриваєте {name}. Відкрити його?"
    else:
        prompt = f"Відкрити {name}?"

    retry_prompt = f'Відкрити {name}? Скажіть "так" або "ні"'

    if stdout:
        stdout.write(f"Пропоную відкрити одразу: {name}")

    attempt = 0
    no_response_streak = 0

    while attempt < max_attempts:
        speak_task(prompt if attempt == 0 else retry_prompt)

        answer = get_voice_input(source, recognizer, stdout=stdout)

        if answer is None:
            no_response_streak += 1
            if no_response_streak >= max_no_response:
                speak_async("Я вас не чую, спробуйте пізніше")
                return "cancel"
            continue

        no_response_streak = 0
        attempt += 1

        # Номер стосується списку, який ще не озвучено - показуємо список
        if parse_number(answer) is not None:
            return "deny"

        # Знайоме слово класифікується, невідоме - запускається learn_new_word
        result = classify_answer(answer, commands, source, recognizer, stdout)

        if result == "confirm":
            return "accept"

        if result == "deny":
            return "deny"

        if result == "keep":
            return "keep"

        if result == "cancel":
            speak_async("Гаразд, зупиняю підбір слова")
            return "cancel"

    return "deny"


def confirm_app_name_by_dictionary(
    app_name: str,
    source,
    recognizer,
    commands: dict,
    stdout=None,
    max_attempts: int = 8,
    max_no_response: int = 3,
    page_size: int = SUGGESTIONS_PAGE_SIZE,
):
    """Підбирає та підтверджує назву застосунку зі словника."""
    heard_word = app_name.strip()

    if not heard_word:
        return None

    system_matches = find_matching_apps(heard_word, apps=get_primary_catalog())

    if system_matches:
        all_suggestions = [{"name": app["name"], "path": app["path"]} for app in system_matches]
        source_label = "серед встановлених застосунків"
    else:
        all_suggestions = get_suggestions_for_word(heard_word)
        source_label = "у словнику"

    offset = 0
    current_batch, offset = get_next_suggestions(all_suggestions, offset, page_size)

    if not current_batch:
        if stdout:
            stdout.write(f'Не знайдено варіантів для "{heard_word}", залишаю його як є')
        speak_async(f'Я не знайшла схожих варіантів, залишаю слово "{heard_word}" як є')
        return heard_word

    if system_matches:
        top_app, reason = pick_top_suggestion(heard_word, system_matches)

        if top_app:
            decision = offer_top_app(top_app, reason, source, recognizer, commands, stdout)

            if decision == "accept":
                return top_app

            if decision == "keep":
                return heard_word

            if decision == "cancel":
                return None

    first_batch = current_batch

    need_full_prompt = True
    no_response_streak = 0

    for _ in range(max_attempts):
        if need_full_prompt:
            options_text = ", ".join(f"{i + 1} - {display_name(word)}" for i, word in enumerate(current_batch))

            if stdout:
                stdout.write(f'Варіанти для "{heard_word}" ({source_label}): {options_text}')

            speak_task(f'Почула "{heard_word}". Варіанти: {options_text}. Назвіть номер для вибору, "не підходить" для інших варіантів, "залиш" або "стоп"')
            need_full_prompt = False
        else:
            speak_task('Номер, "не підходить", "залиш" або "стоп"')

        answer = get_voice_input(source, recognizer, stdout=stdout)

        if answer is None:
            no_response_streak += 1
            if no_response_streak >= max_no_response:
                speak_async("Я вас не чую, спробуйте додати команду пізніше")
                return None
            continue

        no_response_streak = 0

        if is_cancel(answer, commands):
            speak_async("Гаразд, зупиняю підбір слова")
            return None

        if is_keep(answer, commands):
            return heard_word

        if is_confirm(answer, commands):
            return current_batch[0]

        position = parse_number(answer)
        if position and 1 <= position <= len(current_batch):
            return current_batch[position - 1]

        answer_type = is_deny(answer, commands)
        if not answer_type:
            learned = classify_answer(answer, commands, source, recognizer, stdout)
            answer_type = learned == "deny"

            if learned == "cancel":
                speak_async("Гаразд, зупиняю підбір слова")
                return None

            if learned == "keep":
                return heard_word

            if learned == "confirm":
                return current_batch[0]

        if answer_type:
            current_batch, offset = get_next_suggestions(all_suggestions, offset, page_size)

            if not current_batch:
                if stdout:
                    stdout.write(
                        f'Додаткових варіантів для "{heard_word}" більше немає, '
                        f'ось попередні варіанти: '
                        + ", ".join(f"{i + 1} - {display_name(word)}" for i, word in enumerate(first_batch))
                    )

                current_batch = first_batch
                need_full_prompt = False
                continue

            need_full_prompt = True
            continue

        continue

    speak_async("Не вдалося підібрати слово, спробуйте ще раз пізніше")
    return None