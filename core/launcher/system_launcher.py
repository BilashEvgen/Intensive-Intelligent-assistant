import os
import platform

from core.catalog.system_apps import app_match_score

SYSTEM_MATCH_STRICT = 0.85
SYSTEM_MATCH_LOOSE = 0.7

# Вбудовані застосунки та розділи Windows: (назва, запуск, варіанти назв українською/російською/англійською)
SYSTEM_TARGETS = (
    {"title": "Параметри", "target": "ms-settings:",
    "names": ["параметри", "параметри windows", "параметри віндовс", "налаштування", "налаштування windows",
            "налаштування віндовс", "settings", "настройки", "параметры"]},
    {"title": "Програми Windows", "target": "ms-settings:appsfeatures",
    "names": ["програми windows", "програми віндовс", "додатки windows", "додатки віндовс",
            "застосунки windows", "застосунки віндовс", "встановлені програми", "встановлені додатки",
            "програми та функції", "всі програми", "приложения windows", "приложения виндовс",
            "установленные приложения", "apps windows"]},
    {"title": "Програми за замовчуванням", "target": "ms-settings:defaultapps",
    "names": ["програми за замовчуванням", "типові програми", "приложения по умолчанию"]},
    {"title": "Оновлення Windows", "target": "ms-settings:windowsupdate",
    "names": ["оновлення windows", "оновлення віндовс", "центр оновлення", "windows update", "обновление windows"]},
    {"title": "Параметри екрана", "target": "ms-settings:display",
    "names": ["параметри екрана", "налаштування екрана", "настройки экрана"]},
    {"title": "Параметри мережі", "target": "ms-settings:network",
    "names": ["параметри мережі", "налаштування мережі", "мережа", "wifi", "wi-fi", "вайфай"]},
    {"title": "Bluetooth", "target": "ms-settings:bluetooth", "names": ["bluetooth", "блютуз"]},
    {"title": "Параметри звуку", "target": "ms-settings:sound",
    "names": ["параметри звуку", "налаштування звуку", "звук"]},
    {"title": "Персоналізація", "target": "ms-settings:personalization",
    "names": ["персоналізація", "оформлення", "персонализация"]},
    {"title": "Калькулятор", "target": "calc.exe",
    "names": ["калькулятор", "калькулятор windows", "калькулятор віндовс", "calculator"]},
    {"title": "Фотографії", "target": "ms-photos:",
    "names": ["фотографії", "фото", "фотки", "галерея", "photos", "фотографии"]},
    {"title": "Годинник", "target": "ms-clock:",
    "names": ["годинник", "будильник", "таймер", "clock", "часы"]},
    {"title": "Камера", "target": "microsoft.windows.camera:", "names": ["камера", "camera"]},
    {"title": "Погода", "target": "msnweather:", "names": ["погода", "weather"]},
    {"title": "Карти", "target": "bingmaps:", "names": ["карти", "maps"]},
    {"title": "Microsoft Store", "target": "ms-windows-store:",
    "names": ["магазин", "microsoft store", "мікрософт стор", "магазин застосунків"]},
    {"title": "Безпека Windows", "target": "windowsdefender:",
    "names": ["безпека windows", "безпека віндовс", "захисник windows", "windows defender", "антивірус",
            "безопасность windows"]},
    {"title": "Блокнот", "target": "notepad.exe", "names": ["блокнот", "notepad", "нотпад"]},
    {"title": "Paint", "target": "mspaint.exe", "names": ["paint", "пейнт", "малювання"]},
    {"title": "Ножиці", "target": "ms-screenclip:",
    "names": ["ножиці", "знімок екрана", "скриншот", "snipping tool", "ножницы"]},
    {"title": "Командний рядок", "target": "cmd.exe",
    "names": ["командний рядок", "cmd", "консоль", "командная строка"]},
    {"title": "PowerShell", "target": "powershell.exe", "names": ["powershell", "павершел"]},
    {"title": "Диспетчер завдань", "target": "taskmgr.exe",
    "names": ["диспетчер завдань", "task manager", "диспетчер задач"]},
    {"title": "Провідник", "target": "explorer.exe",
    "names": ["провідник", "explorer", "проводник", "файловий менеджер"]},
    {"title": "Панель керування", "target": "control.exe",
    "names": ["панель керування", "control panel", "панель управления"]},
    {"title": "Диспетчер пристроїв", "target": "devmgmt.msc",
    "names": ["диспетчер пристроїв", "device manager", "диспетчер устройств"]},
)


def find_system_target(candidates: list, min_score: float = SYSTEM_MATCH_STRICT):
    """Шукає вбудований застосунок або розділ Windows за почутою назвою."""
    best = None
    best_key = (0.0, 0)

    for candidate in candidates:
        candidate = (candidate or "").lower().strip()
        if not candidate:
            continue

        for entry in SYSTEM_TARGETS:
            for name in entry["names"]:
                score = app_match_score(candidate, name)
                key = (score, len(name.split()))
                if score >= min_score and key > best_key:
                    best_key = key
                    best = entry

    return best


def launch_system_target(entry: dict):
    """Запускає вбудований застосунок або розділ Параметрів Windows."""
    if platform.system() != "Windows":
        raise OSError("Системні застосунки Windows доступні лише на Windows")

    os.startfile(entry["target"])


# Процеси вбудованих застосунків (запасне закриття, якщо вікна не знайдено)
SYSTEM_PROCESSES = {
    "Параметри": ("SystemSettings.exe",),
    "Калькулятор": ("CalculatorApp.exe", "Calculator.exe"),
    "Фотографії": ("Microsoft.Photos.exe",),
    "Камера": ("WindowsCamera.exe",),
    "Безпека Windows": ("SecHealthUI.exe",),
    "Microsoft Store": ("WinStore.App.exe",),
    "Блокнот": ("notepad.exe",),
    "Paint": ("mspaint.exe",),
}
