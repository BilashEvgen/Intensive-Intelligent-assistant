from core.models import App_command
from core.utils.voice_engine import speak_async, speak_task
from core.utils.voice_input import get_voice_input
from core.utils.fuzzy_match import similarity
from core.utils.answer_classify import is_cancel, is_confirm

# скільки разів перепитувати ОДИН І ТОЙ САМ крок (ключове слово / підтвердження),
# перш ніж здатись
_STEP_ATTEMPTS = 4

# мінімальна схожість, щоб вважати, що ми знайшли саме ту команду, яку назвав користувач
_MIN_MATCH_SCORE = 0.5


def _find_command_by_spoken_keyword(spoken_text: str):
    """Шукає в БД команду (App_command), чиє ключове слово найбільше схоже на сказане."""
    best_app = None
    best_score = 0.0

    spoken_text = spoken_text.lower().strip()

    for app in App_command.objects.all():
        if not app.key_word:
            continue

        key_word = app.key_word.lower()
        score = similarity(key_word, spoken_text)

        # якщо одне повністю входить в інше - вважаємо це майже точним збігом
        if key_word in spoken_text or spoken_text in key_word:
            score = max(score, 0.9)

        if score > best_score:
            best_score = score
            best_app = app

    return best_app, best_score


def delete_app_command_voice(source, recognizer, commands: dict, stdout=None):
    """
    Голосове видалення збереженої команди з БД:
    1. питає ключове слово команди, яку треба видалити,
    2. шукає найбільш схожу команду серед збережених,
    3. просить підтвердження і видаляє.
    Розуміє "стоп" на будь-якому кроці - одразу скасовує видалення.
    """
    keyword_text = None

    for attempt in range(_STEP_ATTEMPTS):
        if attempt == 0:
            speak_task('Яку команду видалити? Назвіть її ключове слово. Або скажіть стоп')
        else:
            speak_task('Назвіть ключове слово команди для видалення. Повторіть, будь ласка')

        answer = get_voice_input(source, recognizer, stdout=stdout)

        if answer is None:
            continue

        if is_cancel(answer, commands):
            speak_async("Гаразд, скасовую видалення")
            return

        keyword_text = answer
        break

    if not keyword_text:
        speak_async("Не вдалося розпізнати команду, спробуйте пізніше")
        return

    found_app, score = _find_command_by_spoken_keyword(keyword_text)

    if not found_app or score < _MIN_MATCH_SCORE:
        speak_async(f'Я не знайшла збереженої команди схожої на "{keyword_text}"')
        return

    for attempt in range(_STEP_ATTEMPTS):
        if attempt == 0:
            speak_task(
                f'Знайшла команду "{found_app.key_word}" для застосунку "{found_app.app_name}". '
                f'Видалити її? Скажіть "так", або "стоп", щоб скасувати'
            )
        else:
            speak_task('Скажіть "так", щоб видалити, або "стоп", щоб скасувати')

        answer = get_voice_input(source, recognizer, stdout=stdout)

        if answer is None:
            continue

        if is_cancel(answer, commands):
            speak_async("Гаразд, скасовую видалення")
            return

        if is_confirm(answer, commands):
            app_name = found_app.app_name
            found_app.delete()
            speak_async(f'Команду для "{app_name}" видалено')
            if stdout:
                stdout.write(f'Видалено команду "{app_name}" з БД')
            return

    speak_async("Не вдалося підтвердити видалення, команду залишено без змін")
