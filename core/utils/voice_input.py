import time

ENERGY_THRESHOLD = 200
PAUSE_THREASHOLD = 0.6
PHRASE_THRESHOLD = 0.1
NON_SPEAKING_DURATION = 0.3
LANGUAGE = "uk-UA"


def configure_recognizer(recognizer):
    recognizer.dynamic_energy_threshold = False
    recognizer.energy_threshold = ENERGY_THRESHOLD
    recognizer.pause_threshold = PAUSE_THREASHOLD
    recognizer.phrase_threshold = PHRASE_THRESHOLD
    recognizer.non_speaking_duration = NON_SPEAKING_DURATION\

def recognize_variants(recognizer, audio, language: str = LANGUAGE):
    result = recognizer.recognize_google(audio, language = language, show_all = True)
    alternatives = result.get("alternative", []) if isinstance(result, dict) else []
    variants = []
    for alternative in alternatives:
        text = (alternative.get("transcript") or "").lower().strip() 
        if text and text not in variants:
            variants.append(text)
        return variants

def get_voice_input(
    source,
    recognizer,
    phrase_time_limit: int = 6,
    pre_delay: float = 0.4,
    stdout=None,
    recalibrate: bool = False,
):
    """Слухає один голосовий запит і повертає текст або None."""
    try:
        time.sleep(pre_delay)
        configure_recognizer(recognizer)
        if stdout:
            stdout.write(f"Слухаю відповідь")
        audio = recognizer.listen(source, timeout = None, phrase_time_limit = phrase_time_limit)
        variants = recognize_variants(recognizer, audio)
        if not variants:
            if stdout:
                stdout.write("Не вдалося розпізнати відповідь")
            return None

        return variants[0]

    except Exception as err:
        if stdout:
            stdout.write(f"Не вдалося розпізнати відповідь: {err}")
        return None
