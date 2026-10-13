from django.utils import timezone

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

class App_usage(models.Model):
    name = models.CharField(max_length = 200, verbose_name = "Назва застосунку")
    path = models.CharField(max_length = 500, unique = True, verbose_name = "Шлях")
    launch_count = models.PositiveIntegerField(default = 0, verbose_name = "Кількість запусків")
    last_used_at = models.DateTimeField(default = timezone.now, verbose_name = "Останній запуск")

    def __str__(self):
        return f"{self.name} ({self.launch_count})"

class Discovered_app(models.Model):
    name = models.CharField(max_length = 200, verbose_name = "Назва застосунку")
    path = models.CharField(max_length = 500, verbose_name = "Шлях")
    added_at = models.DateTimeField(auto_now_add = True, verbose_name = "Поле знайдено")
    

    class Meta:
        unique_together = ("name", "path")
        
        def __str__(self):
            return self.name