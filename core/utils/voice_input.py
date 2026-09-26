import time


def get_voice_input(
    source,
    recognizer,
    phrase_time_limit: int = 6,
    pre_delay: float = 0.8,
    stdout=None,
    recalibrate: bool = False,
):
    """Слухає один голосовий запит і повертає текст або None."""
    try:
        time.sleep(pre_delay)

        if recalibrate:
            try:
                pass
            except Exception:
                pass

        recognizer.dynamic_energy_threshold = False
        recognizer.energy_threshold = 200

        recognizer.pause_threshold = 0.6
        recognizer.phrase_threshold = 0.2
        recognizer.non_speaking_duration = 0.3

        if stdout:
            stdout.write(f"Слухаю відповідь ...")

        audio = recognizer.listen(source, timeout=None, phrase_time_limit=phrase_time_limit)
        text = recognizer.recognize_google(audio, language="uk-UA").lower()
        return text

    except Exception as err:
        if stdout:
            stdout.write(f"Не вдалося розпізнати відповідь: {err}")
        return None
