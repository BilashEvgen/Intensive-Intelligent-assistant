from core.utils.voice_engine import speak_async, speak_task
from core.utils.voice_input import get_voice_input
from core.utils.spelling import spell_word_numbered, parse_number
from core.utils.answer_classify import is_cancel, is_confirm, is_deny, matches_action
from core.utils.fuzzy_match import fuzzy_word_in_text
from core.utils.dictionary_api import get_suggestions_for_word, get_next_suggestions

_CANCEL = "__CANCEL__"

# скільки варіантів зі словника показувати за раз
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
    """
    Замість того щоб перепитувати слово по буквах, звертається до API
    словника і пропонує користувачу кілька (page_size) найбільш підходящих
    слів до того, що почув асистент.

    - користувач називає одне із запропонованих слів (або повторює саме
      почуте слово чи каже "так") -> воно підтверджується і повертається;
    - користувач каже "не підходить" -> показуємо НАСТУПНІ page_size
      варіантів зі словника, не повторюючи вже показані;
    - варіанти зі словника закінчились -> залишаємо початкове почуте слово;
    - "стоп" -> скасування (повертає None).

    Повертає підтверджене слово, або None, якщо скасовано / не вдалось підтвердити.
    """
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

    need_full_prompt = True
    no_response_streak = 0

    for _ in range(max_attempts):
        if need_full_prompt:
            options_text = ", ".join(f"{i + 1} - {word}" for i, word in enumerate(current_batch))

            if stdout:
                stdout.write(f'Варіанти зі словника для "{heard_word}": {options_text}')

            speak_task(
                f'Я почула щось схоже на слово {heard_word}. Можливо, ви мали на увазі: {options_text}. '
                f'Назвіть потрібне слово, скажіть "не підходить" щоб почути інші варіанти, '
                f'або "стоп", щоб скасувати'
            )
            need_full_prompt = False
        else:
            speak_task('Скажіть потрібне слово, "не підходить", або "стоп"')

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

        # користувач назвав один із запропонованих варіантів
        for word in current_batch:
            if fuzzy_word_in_text(word, answer):
                return word

        # користувач підтвердив саме початково почуте слово ("так" / повторив його)
        if is_confirm(answer, commands) or fuzzy_word_in_text(heard_word, answer):
            return heard_word

        if is_deny(answer, commands):
            current_batch, offset = get_next_suggestions(all_suggestions, offset, page_size)

            if not current_batch:
                if stdout:
                    stdout.write(f'Варіанти зі словника вичерпано, залишаю слово "{heard_word}" як є')
                speak_async(f'Більше варіантів немає, залишаю слово "{heard_word}" як є')
                return heard_word

            need_full_prompt = True
            continue

        # незрозуміла відповідь - короткий перепит без повторного переліку варіантів
        continue

    speak_async("Не вдалося підібрати слово, спробуйте ще раз пізніше")
    return None

# скільки разів перепитувати ОДИН І ТОЙ САМ підкрок (наприклад "яку літеру
# видалити"), перш ніж здатись і повернутись до головного меню дій.
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
    """
    Асистент один раз озвучує припущену назву застосунку по буквах (з номерами)
    і одразу пояснює, що можна зробити далі - все в ОДНІЙ репліці:
        "так" -> підтвердити,
        номер літери -> замінити її,
        "додати літеру" / "видалити літеру" -> відредагувати слово,
        "стоп" -> скасувати.

    Слово повторно озвучується по буквах ЛИШЕ якщо воно змінилось (після
    редагування). При тиші/незрозумілій відповіді - лише короткий перепит,
    без повторного читання слова.

    Якщо ж усередині підкроку (наприклад "яку літеру додати") відповідь не
    почута - асистент перепитує САМЕ ЦЕЙ підкрок ще кілька разів, а не
    повертається одразу до головного меню дій (щоб не змушувати користувача
    повторювати номер літери спочатку).

    Повертає підтверджене слово, або None, якщо скасовано / не вдалось підтвердити.
    """
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

        # незрозуміла відповідь (в тому числі просто "ні" без деталей) -
        # без повторного читання слова, лише короткий перепит на наступній ітерації
        continue

    speak_async("Не вдалося підтвердити слово, спробуйте ще раз пізніше")
    return None


def _ask_position(prompt_text, min_pos, max_pos, source, recognizer, commands, stdout=None):
    """
    Питає номер літери (позицію) і НЕ повертається до головного меню дій,
    поки не отримає коректну відповідь, користувач не скаже "стоп", або не
    вичерпаються спроби ЦЬОГО САМОГО підкроку.
    Повертає: число (позиція), _CANCEL, або None (спроби вичерпано).
    """
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
    """
    Питає нову літеру і НЕ повертається до головного меню дій, поки не
    отримає відповідь, користувач не скаже "стоп", або не вичерпаються
    спроби цього самого підкроку.
    Повертає: літеру (str), _CANCEL, або None (спроби вичерпано).
    """
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
    """Замінює літеру за вже відомим номером. Повертає нове слово / старе слово / None (стоп)."""
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
    """Додає нову літеру у слово. Повертає нове слово / старе слово / None (стоп)."""
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
    """Видаляє літеру за номером. Повертає нове слово / старе слово / None (стоп)."""
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
