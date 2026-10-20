import os
import platform
import subprocess
import threading
import time

from core.utils.app_usage import record_app_launch
from core.utils.running_apps import snapshot_windows

POLL_INTERVAL = 2.0
LAUNCH_COOLDOWN = 5.0
PENDING_TTL = 12.0

running = threading.Event()
lock = threading.Lock()
recent = {}
pending = []


def is_watcher_running() -> bool:
    """Чи працює стеження за запусками."""
    return running.is_set()


def resolve_shortcut_target(path: str) -> str:
    """Для ярлика .lnk повертає шлях до exe, на який він вказує."""
    if not path.lower().endswith(".lnk") or platform.system() != "Windows":
        return path

    script = (
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        "(New-Object -ComObject WScript.Shell).CreateShortcut('{}').TargetPath"
    ).format(path.replace("'", "''"))

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10,
        )
        return result.stdout.strip() or path
    except Exception:
        return path


def count_launch(name: str, path: str, now: float) -> bool:
    """Рахує запуск, ігноруючи дублі того ж exe протягом LAUNCH_COOLDOWN секунд."""
    base = os.path.basename(path).lower()

    with lock:
        if base and base in recent and now - recent[base] < LAUNCH_COOLDOWN:
            return False
        if base:
            recent[base] = now

    return bool(record_app_launch(name, path))


def register_assistant_launch(name: str, path: str):
    """Викликається, коли застосунок запустив сам асистент."""
    if not is_watcher_running():
        count_launch(name, resolve_shortcut_target(path), time.monotonic())
        return

    with lock:
        pending.append({"name": name, "path": path, "time": time.monotonic()})


def flush_pending(now: float, stdout=None):
    """Рахує запуски асистента, для яких так і не з'явилось нове вікно."""
    with lock:
        expired = [item for item in pending if now - item["time"] >= PENDING_TTL]
        for item in expired:
            pending.remove(item)

    for item in expired:
        target = resolve_shortcut_target(item["path"])
        if count_launch(item["name"], target, now, window=PENDING_TTL + 2 * POLL_INTERVAL) and stdout:
            stdout.write(f"Запам'ятала запуск: {item['name']}")


def watch_launches(stdout=None, snapshot=snapshot_windows, sleep=time.sleep, clock=time.monotonic, iterations=None):
    """Стежить за появою нових вікон застосунків і записує запуски в БД."""
    from django.db import connection

    try:
        previous = set(snapshot())
    except Exception as err:
        if stdout:
            stdout.write(f"Стеження за запусками недоступне: {err}")
        return

    running.set()
    step = 0

    if stdout:
        stdout.write("Стеження за запуском застосунків увімкнено")

    try:
        while iterations is None or step < iterations:
            step += 1
            sleep(POLL_INTERVAL)

            try:
                now = clock()
                current = snapshot()
                fresh = {info for hwnd, info in current.items() if hwnd not in previous}

                for exe, name in sorted(fresh):
                    if count_launch(name, exe, now) and stdout:
                        stdout.write(f"Запам'ятала запуск: {name}")

                previous = set(current)
                flush_pending(now, stdout)
            except Exception as err:
                if stdout:
                    stdout.write(f"Помилка стеження: {err}")
    finally:
        running.clear()
        connection.close()


def start_process_watcher_async(stdout=None):
    """Запускає стеження у фоновому потоці (лише Windows)."""
    if platform.system() != "Windows":
        if stdout:
            stdout.write("Стеження за запусками поки підтримується лише на Windows, пропускаємо")
        return None

    thread = threading.Thread(target=watch_launches, args=(stdout,), daemon=True)
    thread.start()
    return thread
