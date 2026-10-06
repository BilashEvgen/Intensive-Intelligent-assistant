import platform
import threading
from core.models import Discovered_app
from core.utils.system_apps import list_installed_apps


def scan_and_store_apps(stdout = None):
    if platform.system() != "Windows":
        if stdout:
            stdout.write("Сканування застосунків поки підтримується лише на Windows, пропускаємо")
            return True
    if stdout:
        stdout.write("Сканує застосунки на комп'ютері")

    apps = list_installed_apps()
    exciting_pairs = set(Discovered_app.objects.values_list("name", "path",))

    added_count = 0
    for app in apps:
        name = app.get("name")
        path = app.get("path")
        if not name or not path:
            continue
        if (name, path) in exciting_pairs:
            continue
        Discovered_app.objects.create(name = name, path = path)
        exciting_pairs.add((name, path))
        added_count += 1
        message = f"Знайдено новий застосунок: {name}"
        if stdout:
            stdout.write(message)

    summary = f"Сканування завершено: знайдено {len(apps)} застосунків, додано нових {added_count}"
    if stdout:
        stdout.write(summary)
    
def scan_and_store_apps_async(stdout = None):
    thread = threading.Thread(target = scan_and_store_apps, args = (stdout,), daemon = True)
    thread.start()
    return thread