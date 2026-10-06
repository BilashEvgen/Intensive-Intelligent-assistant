from core.models import App_command
from core.utils.voice_engine import speak_async, speak_task
from core.utils.voice_input import get_voice_input
from core.utils.answer_classify import is_cancel, is_confirm, classify_answer

STEP_ATTEMPTS = 4


def ask_confirmation(prompt_text: str, source, recognizer, commands: dict, stdout=None):
    """Запитує підтвердження голосом. Повертає True/False/None (скасовано)."""
    for attempt in range(STEP_ATTEMPTS):
        speak_task(prompt_text if attempt == 0 else '"Так" або "стоп"?')

        answer = get_voice_input(source, recognizer, stdout=stdout)

        if answer is None:
            continue

        if is_cancel(answer, commands):
            return None

        if is_confirm(answer, commands):
            return True

        learned = classify_answer(answer, commands, source, recognizer, stdout)

        if learned in ("deny", "cancel"):
            return None

        if learned == "confirm":
            return True

    return False


def add_new_app_command_voice(source, recognizer, commands: dict, stdout=None):
    """Додає нову команду голосом після підтвердження."""
    speak_task('Щоб додати команду, скажіть ключове слово')
    keyword = get_voice_input(source, recognizer, stdout=stdout)

    if not keyword:
        speak_task('Я не почула слово, спробуйте ще раз')
        return

    confirmed = ask_confirmation(f'Ваше слово: {keyword}, підтвердити?', source, recognizer, commands, stdout)

    if confirmed is None:
        speak_task('Дія скасована')
        return
    if not confirmed:
        speak_task('Не вдалося підтвердити слово, спробуйте пізніше')
        return

    speak_task("Щоб додати застосунок скажіть його назву")
    app_name = get_voice_input(source, recognizer, stdout=stdout)

    if not app_name:
        speak_task('Назву не розпізнано')
        return

    app_name = app_name.replace('крапка', '.').replace('', '')

    confirmed_app = ask_confirmation(f'Назва додатку {app_name}, підтвердити?', source, recognizer, commands, stdout)

    if confirmed_app is None:
        speak_task("Додавання скасовано")
        return
    if not confirmed_app:
        speak_task('Не вдалося підтвердити назву, спробуйте пізніше')
        return

    App_command.objects.create(
        key_word=keyword,
        app_name=app_name,
    )
    speak_async(f"Ваша команда : {keyword} успішно додана")
    if stdout:
        stdout.write(f"Збережено {keyword} -> {app_name}")
