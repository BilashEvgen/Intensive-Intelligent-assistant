from django.db import models

class Voice_response(models.Model):
    key_word = models.CharField(max_length = 100, verbose_name = "Ключове слово")
    response = models.TextField(verbose_name = "Що відповісти")
    def __str__(self):
        return f"Відповідь на {self.key_word}"

class App_command(models.Model):
    path = models.CharField(max_length = 250, blank = True, null = True, verbose_name = "Шлях")
    app_name = models.CharField(max_length = 100, verbose_name = "Назва файлу")
    key_word = models.CharField(max_length = 100, verbose_name = "Ключове слово")
    def __str__(self):
        return f"Запуск {self.app_name} за словом {self.key_word}"