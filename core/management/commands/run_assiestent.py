from django.core.management.base import BaseCommand
import speech_recognition as sr
from core.models import Voice_response, App_command
from core.utils.voice_engine import speak_async, speak_cached, prewarm_cache
import platform
import os
import subprocess

from core.utils.finder import find_app_path
from core.management.commands.add_command import add_new_app_command_voice
from core.management.commands.delete_command import delete_app_command_voice
from core.utils.default_commands import load_default_commands
from core.utils.fuzzy_match import fuzzy_word_in_text, find_best_keyword_match, similarity, extract_app_name
from core.utils.app_confirm import confirm_app_from_catalog
from core.utils.voice_input import configure_recognizer, recognize_variants, get_voice_variants
from core.management.commands.clarify import ask_app_name, ALL_PHRASES
from core.utils.app_closer import close_by_voice
from core.utils.system_launcher import (
    find_system_target, launch_system_target, SYSTEM_MATCH_STRICT, SYSTEM_MATCH_LOOSE,
)
from core.utils.answer_classify import matches_action
from core.utils.discovery_app import scan_and_store_apps_async
from core.utils.process_watcher import start_process_watcher_async, register_assistant_launch
from core.utils.system_apps import normalize_app_path


class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Асистен запущений ..."))

        self.default_commands = load_default_commands()
        prewarm_cache(ALL_PHRASES)
        
        scan_and_store_apps_async(self.stdout)
        start_process_watcher_async(stdout= self.stdout)
        
        recognizer = sr.Recognizer()
        configure_recognizer(recognizer)
        mic = sr.Microphone()
        
        with mic as source:
            self.stdout.write(self.style.SUCCESS("Слухаю ..."))
            
            while True:
                try:
                    audio = recognizer.listen(source, timeout = None, phrase_time_limit = 5)

                    variants = recognize_variants(recognizer, audio)

                    if not variants:
                        continue

                    command_text = variants[0]
                    self.text_variants = [{"transcript": text} for text in variants]
                    self.stdout.write(f"Ви сказали: {command_text}")
                    self.process_command(command_text, source, recognizer)
                    
                except sr.UnknownValueError:
                    continue
                
                except Exception as err:
                    self.stdout.write(self.style.WARNING(f"Помилка: {err}"))
                    continue
                
    def process_command(self, command_text: str, source, recognizer, clarified: bool = False):
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
            add_new_app_command_voice(source, recognizer, self.default_commands, self.stdout)
            return

        if is_delete_command:
            delete_app_command_voice(source, recognizer, self.default_commands, self.stdout)
            return

        if is_close:
            self.handle_close(command_text, source, recognizer, clarified)
            return

        if not is_open:
            for resp in Voice_response.objects.all():
                if resp.key_word and fuzzy_word_in_text(resp.key_word, command_text):
                    speak_async(resp.response)
                    return
            return

        candidates = self.open_candidates(command_text)

        system_entry = find_system_target(candidates, SYSTEM_MATCH_STRICT)
        if system_entry:
            self.open_system_target(system_entry)
            return

        found_app = self.find_app_by_keyword()

        if not found_app:
            system_entry = find_system_target(candidates, SYSTEM_MATCH_LOOSE)
            if system_entry:
                self.open_system_target(system_entry)
                return

            candidate = extract_app_name(command_text, self.default_commands["open"])

            if not candidate:
                # Дієслово почуто, а назви програми немає - одразу перепитуємо
                if clarified:
                    speak_async("Я не знайшла такої команди")
                else:
                    self.clarify_and_retry("open", source, recognizer)
                return

            speak_async(f'Я не знайшла команду "{candidate}" в базі. Шукаю схожі програми на компʼютері')

            confirmed_word = confirm_app_from_catalog(
                candidate, source, recognizer, self.default_commands, self.stdout
            )

            if not confirmed_word:
                return

            self.register_and_launch_new_app(confirmed_word)
            return

        if found_app.path and self.is_launchable_path(found_app.path):
            speak_async(f"Відкриваю {found_app.app_name}")
            self.launch_app(found_app.path, found_app.app_name)
            return

        speak_async(f"Шукаю {found_app.app_name}")
        found_path = find_app_path(found_app.app_name)

        if found_path:
            found_app.path = found_path
            found_app.save()
            speak_async(f"Відкриваю {found_app.app_name}")
            self.launch_app(found_path, found_app.app_name)
        else:
            speak_async(f"Я не змогла знайти цю програму на компе")

    def clarify_and_retry(self, action: str, source, recognizer):
        """Питає назву програми і повторно виконує команду вже з уточненою назвою."""
        names = ask_app_name(
            action,
            self.default_commands,
            listen=lambda: get_voice_variants(source, recognizer, stdout=self.stdout),
            say=speak_cached,
            stdout=self.stdout,
        )

        if not names:
            return

        verb = self.default_commands[action][0]
        self.text_variants = [{"transcript": f"{verb} {name}"} for name in names]
        self.stdout.write(f"Уточнено: {self.text_variants[0]['transcript']}")
        self.process_command(self.text_variants[0]["transcript"], source, recognizer, clarified=True)

    def handle_close(self, command_text: str, source=None, recognizer=None, clarified: bool = False):
        """Закриває запущену програму за назвою (команди, системні програми, будь-яке відкрите вікно)."""
        candidates = self.open_candidates(command_text, "close")

        if not candidates:
            if clarified or source is None:
                speak_async("Що саме закрити?")
            else:
                self.clarify_and_retry("close", source, recognizer)
            return

        status, label = close_by_voice(candidates)

        if status == "unsupported":
            found_app = self.find_app_by_keyword()
            if not found_app:
                speak_async("Я не знайшла такої команди")
                return
            speak_async(f"Закриваю {found_app.app_name}")
            self.close_app(found_app)
        elif status == "closed":
            speak_async(f"Закрила {label}")
        elif status == "killed":
            speak_async(f"Завершила {label}")
        elif status == "pending":
            speak_async(f"{label} ще відкрита, можливо, вона питає про збереження змін")
        else:
            speak_async(f"Я не бачу запущеної програми {label}")

    def open_candidates(self, command_text: str, action: str = "open") -> list:
        """Повертає назви застосунку з усіх варіантів розпізнавання."""
        texts = [command_text] + [item.get("transcript", "") for item in getattr(self, "text_variants", [])]
        candidates = []

        for text in texts:
            candidate = extract_app_name(text.lower().strip(), self.default_commands[action])
            if candidate and candidate not in candidates:
                candidates.append(candidate)

        return candidates

    def open_system_target(self, entry: dict):
        """Відкриває вбудований застосунок або розділ Параметрів Windows."""
        speak_async(f"Відкриваю {entry['title']}")
        try:
            launch_system_target(entry)
        except Exception as err:
            self.stdout.write(self.style.ERROR(f"Помилка запуску {entry['title']}: {err}"))
            speak_async("Не вдалося відкрити")

    def is_launchable_path(self, path):
        """Перевіряє доступність шляху для запуску."""
        path = normalize_app_path(path)
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
            self.launch_app(known_path, word)
            return

        speak_async(f"Слово {word} додано. Шукаю програму")
        found_path = find_app_path(word)

        if found_path:
            app_command.path = found_path
            app_command.save()
            speak_async(f"Відкриваю {word}")
            self.launch_app(found_path, word)
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
            
    def launch_app(self, path, name = None):
        path = normalize_app_path(path)
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            else:
                subprocess.run(["open", "-a", path], check=True)
        except Exception as err:
            self.stdout.write(self.style.ERROR(f"Помилка запуску {err}"))
            return
        
        try:
            register_assistant_launch(name or os.path.splitext(os.path.basename(path))[0], path)
        except Exception as error:
            self.stdout.write(self.style.WARNING(f"Не вдалося записати запуск {error}"))
            
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
