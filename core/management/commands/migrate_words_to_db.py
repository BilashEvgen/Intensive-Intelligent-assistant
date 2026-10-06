import json
from django.core.management.base import BaseCommand
from core.utils.phrase_db import add_phrase, init_db
from core.utils.default_commands import DEFAULT_COMMANDS_PATH

class Command(BaseCommand):
    def handle(self, *args, **options):
        init_db()
        try:
            with open(DEFAULT_COMMANDS_PATH, mode="r", encoding="utf-8") as file:
                data = json.load(file)
        except Exception as err:
            self.stdout.write(self.style.ERROR(f"Не вдалося прочитати {DEFAULT_COMMANDS_PATH}: {err}"))
            return 
        added = 0
        skipped = 0
        for category, phrases in data.items():
            for phrase in phrases:
                if add_phrase(category, phrase):
                    added += 1
                else:
                    skipped += 1
        self.stdout.write(self.style.SUCCESS(f"Готово: додано {added}, вже було: {skipped}"))
        