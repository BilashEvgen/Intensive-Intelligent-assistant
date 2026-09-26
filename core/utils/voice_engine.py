import asyncio
import os
import threading
import time
import edge_tts
import pygame

pygame.mixer.init()

def speak_task(text: str):
    file_name = f"voice_{int(time.time())}.mp3"
    try:
        VOICE = "uk-UA-PolinaNeural"
        async def generate():
            communicate = edge_tts.Communicate(text, VOICE)
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
