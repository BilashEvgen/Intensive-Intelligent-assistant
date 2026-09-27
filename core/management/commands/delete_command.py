from core.models import App_command
from core.utils.voice_engine import speak_async, speak_task
from core.utils.voice_input import get_voice_input
from core.utils.fuzzy_match import similarity
from core.utils.answer_classify import is_cancel, is_confirm, classify_answer

_STEP_ATTEMPTS = 4

_MIN_MATCH_SCORE = 0.5


def _find_command_by_spoken_keyword(spoken_text: str):
    """Знаходить команду за схожим ключовим словом."""
    best_app = None
    best_score = 0.0

    spoken_text = spoken_text.lower().strip()

    for app in App_command.objects.all():
        if not app.key_word:
            continue

        key_word = app.key_word.lower()
        score = similarity(key_word, spoken_text)

        if key_word in spoken_text or spoken_text in key_word:
            score = max(score, 0.9)

        if score > best_score:
            best_score = score
            best_app = app

    return best_app, best_score


def delete_app_command_voice(source, recognizer, commands: dict, stdout=None):
    """Видаляє збережену команду голосом після підтвердження."""
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

        learned = classify_answer(answer, commands, source, recognizer, stdout)

        if learned in ("deny", "cancel"):
            speak_async("Гаразд, скасовую видалення")
            return

        if learned == "confirm":
            app_name = found_app.app_name
            found_app.delete()
            speak_async(f'Команду для "{app_name}" видалено')
            if stdout:
                stdout.write(f'Видалено команду "{app_name}" з БД')
            return

    speak_async("Не вдалося підтвердити видалення, команду залишено без змін")
