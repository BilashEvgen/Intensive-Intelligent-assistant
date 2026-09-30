from django.core.management.base import BaseCommand
import speech_recognition as sr
from core.models import Voice_response, App_command
from core.utils.voice_engine import speak_async
import platform
import os
import subprocess

from core.utils.finder import find_app_path
from core.management.commands.add_command import add_new_app_command_voice
from core.management.commands.delete_command import delete_app_command_voice
from core.utils.default_commands import load_default_commands
from core.utils.fuzzy_match import fuzzy_word_in_text, find_best_keyword_match, similarity, extract_app_name
from core.utils.app_confirm import confirm_app_name_by_dictionary
from core.utils.answer_classify import matches_action

class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Асистен запущений ..."))

        self.default_commands = load_default_commands()
        
        recognizer = sr.Recognizer()
        mic = sr.Microphone()
        
        with mic as source:
            recognizer.dynamic_energy_threshold = False

            recognizer.energy_threshold = 200

            self.stdout.write(self.style.SUCCESS("Слухаю ..."))
            
            while True:
                try:
                    audio = recognizer.listen(source, timeout = None, phrase_time_limit = 5)

                    command_text = recognizer.recognize_google(audio, language = "uk-UA")
                    self.text_variants = recognizer.recognize_google(audio, language = "uk-UA", show_all = True)['alternative']
                    self.stdout.write(f"Ви сказали: {command_text}")
                    self.process_command(command_text, source, recognizer)
                    
                except sr.UnknownValueError:
                    continue
                
                except Exception as err:
                    self.stdout.write(self.style.WARNING(f"Помилка: {err}"))
                    continue
                
    def process_command(self, command_text: str, source, recognizer):
        command_text = command_text.lower().strip()

        is_add_command = matches_action(command_text, self.default_commands["add_command"])
        is_delete_command = matches_action(command_text, self.default_commands["delete_command"])
        is_close = find_best_keyword_match(
            self.default_commands["close"], command_text
        )
        is_open = find_best_keyword_match(
            self.default_commands["open"], command_text
        )

        if is_add_command:
            add_new_app_command_voice(source, recognizer)
            return

        if is_delete_command:
            delete_app_command_voice(source, recognizer, self.default_commands, self.stdout)
            return

        if is_close:
            found_app = self.find_app_by_keyword()
            if not found_app:
                speak_async("Я не знайшла такої команди")
                return
            speak_async(f"Закриваю {found_app.app_name}")
            self.close_app(found_app)
            return

        if not is_open:
            for resp in Voice_response.objects.all():
                if resp.key_word and fuzzy_word_in_text(resp.key_word, command_text):
                    speak_async(resp.response)
                    return
            return

        found_app = self.find_app_by_keyword()

        if not found_app:
            candidate = extract_app_name(command_text, self.default_commands["open"])

            if not candidate:
                speak_async("Я не знайшла такої команди")
                return

            speak_async(f'Я не знайшла команду "{candidate}" в базі. Підберу схожі слова зі словника')

            confirmed_word = confirm_app_name_by_dictionary(
                candidate, source, recognizer, self.default_commands, self.stdout
            )

            if not confirmed_word:
                speak_async("Додавання скасовано")
                return

            self.register_and_launch_new_app(confirmed_word)
            return

        if found_app.path and self.is_launchable_path(found_app.path):
            speak_async(f"Відкриваю {found_app.app_name}")
            self.launch_app(found_app.path)
            return

        speak_async(f"Шукаю {found_app.app_name}")
        found_path = find_app_path(found_app.app_name)

        if found_path:
            found_app.path = found_path
            found_app.save()
            speak_async(f"Відкриваю {found_app.app_name}")
            self.launch_app(found_path)
        else:
            speak_async(f"Я не змогла знайти цю програму на компе")

    def is_launchable_path(self, path):
        """Перевіряє доступність шляху для запуску."""
        if not path:
            return False
        if path.lower().startswith("shell:"):
            return True
        return os.path.exists(path)

    def register_and_launch_new_app(self, confirmed):
        if isinstance(confirmed, dict):
            word = confirmed.get("name")
            known_path = confirmed.get("path")
        else:
            word = confirmed
            known_path = None

        app_command = App_command.objects.create(app_name=word, key_word=word, path=known_path)

        if known_path:
            speak_async(f"Відкриваю {word}")
            self.launch_app(known_path)
            return

        speak_async(f"Слово {word} додано. Шукаю програму")
        found_path = find_app_path(word)

        if found_path:
            app_command.path = found_path
            app_command.save()
            speak_async(f"Відкриваю {word}")
            self.launch_app(found_path)
        else:
            speak_async(f"Команду {word} додано, але я не змогла знайти таку програму на компʼютері")

    def find_app_by_keyword(self):
        best_app = None
        best_score = 0
        best_len = 0

        for app in App_command.objects.all():
            if not app.key_word:
                continue

            key_word = app.key_word.lower()

            for element in self.text_variants:
                transcript = element['transcript'].lower()

                if not fuzzy_word_in_text(key_word, transcript):
                    continue

                if key_word in transcript:
                    score = 1.0
                else:
                    score = similarity(key_word, transcript)

                key_len = len(app.key_word)

                if score > best_score or (score == best_score and key_len > best_len):
                    best_score = score
                    best_len = key_len
                    best_app = app

        return best_app
            
    def launch_app(self, path):
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            else:
                subprocess.run(["open", "-a", path], check=True)
        except Exception as err:
            self.stdout.write(self.style.ERROR(f"Помилка запуску {err}"))

def close_app(self, app_command):
    if app_command.path and not app_command.path.lower().endswith(".lnk"):
        process_name = os.path.basename(app_command.path)
    else:
        process_name = app_command.app_name
    try:
        if platform.system() == "Windows":
            if not process_name.lower().endswith(".exe"):
                process_name += ".exe"
            result = subprocess.run(["taskkill", "/IM", process_name, "/F"], capture_output=True)
        else:

            if process_name.lower().endswith(".app"):
                process_name = process_name[:-4]
            result = subprocess.run(["pkill", "-f", process_name], capture_output=True)

        if result.returncode != 0:
            self.stdout.write(self.style.WARNING(f"Не вдалося знайти запущенний процес {process_name}"))

    except Exception as err:
        self.stdout.write(self.style.ERROR(f"Помилка закриття {err}"))
