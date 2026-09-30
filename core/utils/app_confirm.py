from core.utils.voice_engine import speak_async, speak_task
from core.utils.voice_input import get_voice_input
from core.utils.spelling import parse_number
from core.utils.answer_classify import is_cancel, is_confirm, is_deny, is_keep, classify_answer
from core.utils.dictionary_api import get_suggestions_for_word, get_next_suggestions
from core.utils.system_apps import find_matching_apps

SUGGESTIONS_PAGE_SIZE = 3

def display_name(item) -> str:
    """Повертає назву варіанта для показу."""
    return item["name"] if isinstance(item, dict) else item

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

    system_matches = find_matching_apps(heard_word)

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

    first_batch = current_batch

    need_full_prompt = True
    no_response_streak = 0

    for _ in range(max_attempts):
        if need_full_prompt:
            options_text = ", ".join(f"{i + 1} - {display_name(word)}" for i, word in enumerate(current_batch))

            if stdout:
                stdout.write(f'Варіанти для "{heard_word}" ({source_label}): {options_text}')

            speak_task(
                f'Я почула щось схоже на слово {heard_word}. Можливо, ви мали на увазі: {options_text}. '
                f'Назвіть номер потрібного варіанта, скажіть "не підходить" щоб почути інші варіанти, '
                f'"залиш" щоб залишити слово {heard_word} як є, або "стоп", щоб скасувати'
            )
            need_full_prompt = False
        else:
            speak_task('Назвіть номер потрібного варіанта, скажіть "не підходить", "залиш", або "стоп"')

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