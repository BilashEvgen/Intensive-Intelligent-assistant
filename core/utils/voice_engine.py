import asyncio
import os
import threading
import time
import edge_tts
import pygame

# вмикає звукову систему
pygame.mixer.init()

def speak_task(text: str):
    # створює унікальне ім'я голосового файлу
    file_name = f"voice_{int(time.time())}.mp3"
    try:
        # налаштування голосу 
        # uk: мова озвучування
        # UA: регіон
        # Polinal: ім'я голосу
        # Neural: тип голосу
        VOICE = "uk-UA-PolinaNeural"
        async def generate():
            # створюємо об'єкт генерації голосу
            communicate = edge_tts.Communicate(text, VOICE)
            await communicate.save(file_name)
            
        # створюємо новий цикл подій
        loop = asyncio.new_event_loop()
        
        # встановлюємо цикл як основний
        asyncio.set_event_loop(loop)
        
        # запускаємо асинхронну функцію
        loop.run_until_complete(generate())
        
        # закриваємо цикл
        loop.close()
        
        if os.path.exists(file_name):
            # завантажуємо створений файл голосу у mixer пайгейму
            pygame.mixer.music.load(file_name)
            pygame.mixer.music.play()
            
            # запускаємо цикл який буде працювати поки файл озвучується
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
    # створюємо новий потік
    # target: функція яка запускаєтся
    # args: текст який озвучується
    thread = threading.Thread(target = speak_task, args = (text,))
    # запуск потоку
    thread.start()
    # чекає доки поток виконається
    thread.join()
    

# print('test')
# speak_task('Привіт, це тест')
# print('test2')
# speak_async('Привіт, це другий тест')
# print('stop')