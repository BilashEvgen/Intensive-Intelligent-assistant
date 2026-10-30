import asyncio
import hashlib
import os
import threading
import time
import edge_tts
import pygame

pygame.mixer.init()

VOICE = "uk-UA-PolinaNeural"
RATE = "+20%"

# Кеш озвучених фраз: короткі типові фрази (уточнювальні питання) звучать без затримки на мережу
CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tts_cache"
)

def speak_task(text: str):
    file_name = f"voice_{int(time.time())}.mp3"
    try:
        async def generate():
            communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
            await communicate.save(file_name)
            
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(generate())
        loop.close()
        
        if os.path.exists(file_name):
            pygame.mixer.music.load(file_name)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                time.sleep(0.2)
                
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            time.sleep(0.2)
            os.remove(file_name)
            print(f"file {file_name} deleted")
    except Exception as error:
        print(f'Помилка звуку: {error}')
        if os.path.exists(file_name):
            try:
                os.remove(file_name)
            except:
                pass
            
def speak_async(text: str):
    thread = threading.Thread(target = speak_task, args = (text,))
    thread.start()
    thread.join()



def cache_path(text: str) -> str:
    key = hashlib.md5(f"{VOICE}|{RATE}|{text}".encode("utf-8")).hexdigest()
    return os.path.join(CACHE_DIR, f"{key}.mp3")


def synthesize(text: str, file_name: str):
    async def generate():
        communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
        await communicate.save(file_name)

    asyncio.run(generate())


def prewarm_cache(phrases):
    """У фоні озвучує фрази заздалегідь, щоб потім відтворювати їх миттєво."""
    def worker():
        os.makedirs(CACHE_DIR, exist_ok=True)
        for text in phrases:
            path = cache_path(text)
            if os.path.exists(path):
                continue
            tmp = path + ".tmp"
            try:
                synthesize(text, tmp)
                os.replace(tmp, path)
            except Exception:
                if os.path.exists(tmp):
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass

    threading.Thread(target=worker, daemon=True).start()


def speak_cached(text: str):
    """Відтворює фразу з кешу; якщо її там немає - озвучує звичайним способом і кешує."""
    path = cache_path(text)

    if not os.path.exists(path):
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            tmp = path + ".tmp"
            synthesize(text, tmp)
            os.replace(tmp, path)
        except Exception as error:
            print(f"Помилка кешу звуку: {error}")
            speak_task(text)
            return

    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
        pygame.mixer.music.unload()
    except Exception as error:
        print(f"Помилка звуку: {error}")
