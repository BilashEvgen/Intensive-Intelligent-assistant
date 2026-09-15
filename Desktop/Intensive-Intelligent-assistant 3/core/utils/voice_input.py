import time


def get_voice_input(
    source,
    recognizer,
    phrase_time_limit: int = 6,
    pre_delay: float = 0.8,
    stdout=None,
    recalibrate: bool = False,
):
    """
    Слухає користувача через мікрофон один раз і повертає розпізнаний текст
    (у нижньому регістрі) або None, якщо нічого не розпізнано / сталась помилка.

    pre_delay - пауза перед стартом прослуховування. Потрібна, бо одразу після
    відтворення TTS через колонки аудіопристрій деяких систем не встигає
    "перемкнутися" назад у режим запису, і recognizer.listen() миттєво падає
    з помилкою.

    recalibrate - за замовчуванням ВИМКНЕНО. Раніше тут була автоматична
    переналаштування порогу гучності (adjust_for_ambient_noise) прямо перед
    кожним прослуховуванням - але це відбувається одразу після TTS, і навіть
    із затримкою (pre_delay) залишковий звук/відлуння від колонок потрапляє
    в цю коротку калібровку і ЗАВИЩУЄ поріг чутливості. Через це короткі тихі
    слова на кшталт "так"/"ні"/"стоп" переставали розпізнаватись як мова
    взагалі (recognizer просто "не чув", що хтось почав говорити). Тому
    перекалібровка більше не робиться автоматично на кожен виклик - поріг
    чутливості встановлюється один раз на старті (run_assiestent.py) і далі
    сам плавно підлаштовується під час прослуховування завдяки
    dynamic_energy_threshold.

    pause_threshold/phrase_threshold/non_speaking_duration занижені відносно
    дефолтних значень бібліотеки SpeechRecognition (розрахованих на довші
    фрази), щоб короткі односкладові слова не ігнорувались як "занадто короткі".
    """
    try:
        time.sleep(pre_delay)

        # Вимикаємо авто-калібровку шуму перед кожним слуханням.
        # Вона зашкалює поріг чутливості і працює як “шумодав” на рівні
        # SpeechRecognition, через що короткі / тихі слова часто не ловляться.
        if recalibrate:
            try:
                # recognizer.adjust_for_ambient_noise(source, duration=0.3)
                pass
            except Exception:
                pass

        # Вимикаємо автоматичне адаптивне підлаштування порогу. Це дозволяє
        # працювати без шумоподавлення і краще ловити сирий звук з мікрофона.
        recognizer.dynamic_energy_threshold = False
        recognizer.energy_threshold = 200

        recognizer.pause_threshold = 0.6
        recognizer.phrase_threshold = 0.2
        recognizer.non_speaking_duration = 0.3

        if stdout:
            stdout.write(f"Слухаю відповідь ... (поріг чутливості: {recognizer.energy_threshold:.0f})")

        audio = recognizer.listen(source, timeout=None, phrase_time_limit=phrase_time_limit)
        text = recognizer.recognize_google(audio, language="uk-UA").lower()
        return text

    except Exception as err:
        # раніше помилка "проковтувалась" мовчки, через що складно було
        # зрозуміти, чому асистент "не чує" - тепер виводимо її для діагностики
        if stdout:
            stdout.write(f"Не вдалося розпізнати відповідь: {err}")
        return None
