import asyncio
import os
import threading
import time
import edge_tts
import numpy as np
import pygame
from scipy.io import wavfile
from scipy.signal import butter, lfilter

# вмикає звукову систему
pygame.mixer.init(frequency = 24000, size = -16, channels = 1, buffer = 2048)

def butter_lowpass_filter(audio_data, cutoff_frequency , sample_rate, filter_order = 4):

    # Обчислення частоти Найквіста (максимальна фізично можливої частоти звуку) 
    max_possible_frequency = 0.5 * sample_rate
    # Нормалізація частоти зрізу у проміжку від 0 до 1
    normalized_cutoff = cutoff_frequency / max_possible_frequency

    # 3. Створюємо формулу для нашого цифрового еквалайзера.
    # btype='low' — вмикає режим Low-pass: залишає низькі частоти голосу (бас), а високі — глушить.
    # analog=False — каже програмі, що ми обробляємо цифровий файл на ПК, а не реальну залізну радіодеталь.
    filter_numerator, filter_denominator = butter(
        filter_order, normalized_cutoff, btype='low', analog=False
    )

    # 4. Пропускаємо аудіомасив через створену формулу та згладжуємо різкі цифрові сплески
    clean_audio_data = lfilter(filter_numerator, filter_denominator, audio_data)
    return clean_audio_data

def speak_task(text: str):
    # створює унікальне ім'я голосового файлу
    timestamp = int(time.time())
    temp_mp3 = f"temp_{timestamp}.mp3"
    final_wav = f"voice_{timestamp}.wav"

    try:
        # налаштування голосу 
        # uk: мова озвучування
        # UA: регіон
        # Polinal: ім'я голосу
        # Neural: тип голосу
        VOICE = "uk-UA-PolinaNeural"
        async def generate():
            # створюємо об'єкт генерації голосу
            communicate = edge_tts.Communicate(text, VOICE, rate="+9%")
            with open(temp_mp3, "wb") as fp:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        fp.write(chunk["data"])
            
        # створюємо новий цикл подій
        loop = asyncio.new_event_loop()
        
        # встановлюємо цикл як основний
        asyncio.set_event_loop(loop)
        
        # запускаємо асинхронну функцію
        loop.run_until_complete(generate())
        
        # закриваємо цикл
        loop.close()
        
        if os.path.exists(temp_mp3):

            sound = pygame.mixer.Sound(temp_mp3)
            raw_samples = pygame.sndarray.array(sound)
            
            # 1. Фільтруємо звук (зрізаємо свист вище 4800 Гц). Голос стане м'яким і студійним.
            filtered_samples = butter_lowpass_filter(
                audio_data = raw_samples, 
                cutoff_frequency = 5600, 
                sample_rate = 24000, 
                filter_order = 4
            )
            
            # 2. Нормалізуємо амплітуду (робимо звук щільним і гучним БЕЗ хрипу)
            max_val = np.max(np.abs(filtered_samples))
            if max_val > 0:
                filtered_samples = (filtered_samples / max_val) * 32767
            
            # Конвертуємо в аудіоформат 16-біт
            final_audio_mono = filtered_samples.astype(np.int16)
            
            # 3. Готуємо дані для збереження у чистий WAV-файл
            # Склеюємо моно-доріжку в однакове стерео для лівого та правого вуха
            final_audio = np.column_stack((final_audio_mono, final_audio_mono))
            
            # Зберігаємо у фінальний WAV-файл (тепер він запишеться як стерео)
            wavfile.write(final_wav, 24000, final_audio)
            
            os.remove(temp_mp3)
        
        if os.path.exists(final_wav):

            pygame.mixer.init(frequency=24000, size=-16, channels=2, buffer=4096)
            
            pygame.mixer.music.load(final_wav)
            
            pygame.mixer.music.set_volume(0.85) 
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                time.sleep(0.2)
                
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            
            time.sleep(0.2)
            os.remove(final_wav)
            print(f"file {final_wav} deleted")

    except Exception as error:
        print(f'Помилка звуку: {error}')
        for file in (temp_mp3, final_wav):
            if os.path.exists(file):
                try:
                    os.remove(file)
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