from core.utils.voice_engine import speak_async, speak_task
from core.utils.voice_input import get_voice_input
from core.utils.spelling import spell_word_numbered, parse_number
from core.utils.answer_classify import is_cancel, is_confirm, is_deny, is_keep, matches_action
from core.utils.dictionary_api import get_suggestions_for_word, get_next_suggestions

_CANCEL = "__CANCEL__"

_SUGGESTIONS_PAGE_SIZE = 3


def confirm_app_name_by_dictionary(
    app_name: str,
    source,
    recognizer,
    commands: dict,
    stdout=None,
    max_attempts: int = 8,
    max_no_response: int = 3,
    page_size: int = _SUGGESTIONS_PAGE_SIZE,
):
    """Підбирає та підтверджує назву застосунку зі словника."""
    heard_word = app_name.strip()

    if not heard_word:
        return None

    all_suggestions = get_suggestions_for_word(heard_word)
    offset = 0
    current_batch, offset = get_next_suggestions(all_suggestions, offset, page_size)

    if not current_batch:
        if stdout:
            stdout.write(f'Словник не дав варіантів до слова "{heard_word}", залишаю його як є')
        speak_async(f'Я не знайшла схожих слів у словнику, залишаю слово "{heard_word}" як є')
        return heard_word

    first_batch = current_batch

    need_full_prompt = True
    no_response_streak = 0

    for _ in range(max_attempts):
        if need_full_prompt:
            options_text = ", ".join(f"{i + 1} - {word}" for i, word in enumerate(current_batch))

            if stdout:
                stdout.write(f'Варіанти зі словника для "{heard_word}": {options_text}')

            speak_task(
                f'Я почула щось схоже на слово {heard_word}. Можливо, ви мали на увазі: {options_text}. '
                f'Назвіть номер потрібного слова, скажіть "не підходить" щоб почути інші варіанти, '
                f'"залиш" щоб залишити слово {heard_word} як є, або "стоп", щоб скасувати'
            )
            need_full_prompt = False
        else:
            speak_task('Назвіть номер потрібного слова, скажіть "не підходить", "залиш", або "стоп"')

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

        if is_keep(answer, commands) or is_confirm(answer, commands):
            return heard_word

        position = parse_number(answer)
        if position and 1 <= position <= len(current_batch):
            return current_batch[position - 1]

        if is_deny(answer, commands):
            current_batch, offset = get_next_suggestions(all_suggestions, offset, page_size)

            if not current_batch:
                if stdout:
                    stdout.write(
                        f'Додаткових варіантів для "{heard_word}" більше немає, '
                        f'ось попередні варіанти: '
                        + ", ".join(f"{i + 1} - {word}" for i, word in enumerate(first_batch))
                    )

                current_batch = first_batch
                options_text = ", ".join(f"{i + 1} - {word}" for i, word in enumerate(current_batch))
                need_full_prompt = False
                continue

            need_full_prompt = True
            continue

        continue

    speak_async("Не вдалося підібрати слово, спробуйте ще раз пізніше")
    return None

_SUBSTEP_ATTEMPTS = 4


def confirm_app_name_by_spelling(
    app_name: str,
    source,
    recognizer,
    commands: dict,
    stdout=None,
    max_attempts: int = 8,
    max_no_response: int = 3,
):
    """Підтверджує назву застосунку та дозволяє редагувати її по буквах."""
    current_word = app_name.strip()

    if not current_word:
        return None

    need_full_prompt = True
    no_response_streak = 0

    for _ in range(max_attempts):
        if need_full_prompt:
            numbered = spell_word_numbered(current_word)

            if stdout:
                stdout.write(f'Асистент промовляє слово "{current_word}" по буквах: {numbered}')

            speak_task(
                f'Я почула слово: {current_word}. По буквах: {numbered}. '
                f'Якщо вірно - скажіть "так". Якщо ні - назвіть номер літери для заміни, '
                f'скажіть "додати літеру", "видалити літеру", або "стоп", щоб скасувати'
            )
            need_full_prompt = False
        else:
            speak_task('Скажіть "так", номер літери, "додати літеру", "видалити літеру", або "стоп"')

        answer = get_voice_input(source, recognizer, stdout=stdout)

        if answer is None:
            no_response_streak += 1
            if no_response_streak >= max_no_response:
                speak_async("Я вас не чую, спробуйте додати команду пізніше")
                return None
            continue

        no_response_streak = 0

        if is_cancel(answer, commands):
            speak_async("Гаразд, зупиняю перевірку слова")
            return None

        if is_confirm(answer, commands):
            return current_word

        if matches_action(answer, commands.get("add_letter", [])):
            new_word = _add_letter(current_word, source, recognizer, commands, stdout)
            if new_word is None:
                speak_async("Гаразд, зупиняю перевірку слова")
                return None
            if new_word != current_word:
                current_word = new_word
                need_full_prompt = True
            continue

        if matches_action(answer, commands.get("remove_letter", [])):
            new_word = _remove_letter(current_word, source, recognizer, commands, stdout)
            if new_word is None:
                speak_async("Гаразд, зупиняю перевірку слова")
                return None
            if new_word != current_word:
                current_word = new_word
                need_full_prompt = True
            continue

        position = parse_number(answer)
        if position:
            new_word = _replace_letter(current_word, position, source, recognizer, commands, stdout)
            if new_word is None:
                speak_async("Гаразд, зупиняю перевірку слова")
                return None
            if new_word != current_word:
                current_word = new_word
                need_full_prompt = True
            continue

        continue

    speak_async("Не вдалося підтвердити слово, спробуйте ще раз пізніше")
    return None


def _ask_position(prompt_text, min_pos, max_pos, source, recognizer, commands, stdout=None):
    """Запитує позицію літери або повертає сигнал скасування."""
    for attempt in range(_SUBSTEP_ATTEMPTS):
        if attempt > 0:
            speak_task(prompt_text + ". Повторіть, будь ласка")
        else:
            speak_task(prompt_text)

        text = get_voice_input(source, recognizer, stdout=stdout)

        if text is None:
            continue

        if is_cancel(text, commands):
            return _CANCEL

        position = parse_number(text)
        if position and min_pos <= position <= max_pos:
            return position

    return None


def _ask_letter(prompt_text, source, recognizer, commands, stdout=None):
    """Запитує нову літеру або повертає сигнал скасування."""
    for attempt in range(_SUBSTEP_ATTEMPTS):
        if attempt > 0:
            speak_task(prompt_text + ". Повторіть, будь ласка")
        else:
            speak_task(prompt_text)

        text = get_voice_input(source, recognizer, stdout=stdout)

        if text is None:
            continue

        if is_cancel(text, commands):
            return _CANCEL

        if text.strip():
            return text.strip()[0]

    return None


def _replace_letter(word: str, position: int, source, recognizer, commands: dict, stdout=None):
    """Замінює літеру у слові."""
    if position < 1 or position > len(word):
        speak_task("Такого номера літери немає в слові, спробуємо ще раз")
        return word

    new_letter = _ask_letter("Яка літера повинна бути замість цієї? Або скажіть стоп", source, recognizer, commands, stdout)

    if new_letter == _CANCEL:
        return None

    if new_letter is None:
        speak_task("Не вдалося розпізнати літеру, залишаю слово без змін")
        return word

    new_word = word[: position - 1] + new_letter + word[position:]

    if stdout:
        stdout.write(f'Оновлене слово: "{new_word}"')

    return new_word


def _add_letter(word: str, source, recognizer, commands: dict, stdout=None):
    """Додає літеру до слова."""
    max_position = len(word) + 1

    position = _ask_position(
        'На яку позицію вставити нову літеру? Наприклад, скажіть "два", щоб вставити перед другою літерою. Або скажіть стоп',
        1, max_position, source, recognizer, commands, stdout,
    )

    if position == _CANCEL:
        return None

    if position is None:
        speak_task("Не вдалося розпізнати позицію, залишаю слово без змін")
        return word

    new_letter = _ask_letter("Яку літеру додати? Або скажіть стоп", source, recognizer, commands, stdout)

    if new_letter == _CANCEL:
        return None

    if new_letter is None:
        speak_task("Не вдалося розпізнати літеру, залишаю слово без змін")
        return word

    new_word = word[: position - 1] + new_letter + word[position - 1:]

    if stdout:
        stdout.write(f'Оновлене слово: "{new_word}"')

    return new_word


def _remove_letter(word: str, source, recognizer, commands: dict, stdout=None):
    """Видаляє літеру зі слова."""
    if len(word) <= 1:
        speak_task("У слові залишилась лише одна літера, її не можна видалити")
        return word

    position = _ask_position(
        "Яку літеру за номером видалити? Або скажіть стоп",
        1, len(word), source, recognizer, commands, stdout,
    )

    if position == _CANCEL:
        return None

    if position is None:
        speak_task("Не вдалося розпізнати номер, залишаю слово без змін")
        return word

    new_word = word[: position - 1] + word[position:]

    if not new_word:
        speak_task("Так не можна видалити всі літери, залишаю слово без змін")
        return word

    if stdout:
        stdout.write(f'Оновлене слово: "{new_word}"')

    return new_word
