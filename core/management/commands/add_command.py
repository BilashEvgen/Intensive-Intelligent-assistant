from core.models import App_command
from core.utils.voice_engine import speak_async, speak_task
from core.utils.voice_input import get_voice_input


def add_new_app_command_voice(source, recognizer):
    speak_task('Щоб додати команду, скажіть ключове слово')
    keyword  = get_voice_input(source, recognizer)

    if not keyword:
        speak_task('Я не почула слово, спробуйте ще раз')
        return
    speak_task(f'Ваше слово: {keyword}, підтвердити?')
    
    confirm = get_voice_input(source, recognizer)

    print(f'Асистент почув {confirm}')
    if 'підтвердити' not in str(confirm):
        speak_task('Дія скасована')
        return
    
    speak_task("Щоб додати застосунок скажіть його назву")
    app_name = get_voice_input(source, recognizer)
    if not app_name:
        speak_task('Назву не розпізнано')
        return
    app_name = app_name.replace('крапка', '.').replace('', '')
    speak_task(f'Назва додатку {app_name}, підтвердити?')
    
    confirm_app = get_voice_input(source, recognizer)
    print(f"Асисент почув {confirm_app}")
    if "підтвердити" not in str(confirm_app) :
        speak_task("Додавання скасовано")
        return
    
    App_command.objects.create(
        key_word = keyword,
        app_name = app_name
    )
    speak_async(f"Ваша команда : {keyword} успішно додана")
    print(f"Збережено {keyword } -> {app_name}")