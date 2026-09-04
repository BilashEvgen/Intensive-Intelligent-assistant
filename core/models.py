from django.db import models

# Create your models here.
# Створюємо нову модель за допомогою класів пайтону
# Обов'язково наслідуємо базову модель джанго models.Model
class Voice_response(models.Model):
    # CharField використавується для короткого тексту 
    # max_length задає максимальну довжину рядка
    # verbose_name задає назву відображення в адмін-панелі
    key_word = models.CharField(max_length = 100, verbose_name = "Ключове слово")
    # TextField використовується для довгого тексту
    response = models.TextField(verbose_name = "Що відповісти")
    # def __str__(self) - спеціальний метод який відповідає за відображення об'єкту в адмін-панелі
    def __str__(self):
        return f"Відповідь на {self.key_word}"

class App_command(models.Model):
    path = models.CharField(max_length = 250, blank = True, null = True, verbose_name = "Шлях")
    app_name = models.CharField(max_length = 100, verbose_name = "Назва файлу")
    key_word = models.CharField(max_length = 100, verbose_name = "Ключове слово")
    def __str__(self):
        return f"Запуск {self.app_name} за словом {self.key_word}"