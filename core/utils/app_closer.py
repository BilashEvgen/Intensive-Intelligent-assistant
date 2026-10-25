import os
import platform
import subprocess
import time

from core.models import App_command
from core.utils.process_watcher import resolve_shortcut_target
from core.utils.running_apps import snapshot_window_details, send_close
from core.utils.system_apps import app_match_score
from core.utils.system_launcher import find_system_target, SYSTEM_MATCH_LOOSE, SYSTEM_PROCESSES

CLOSE_THRESHOLD = 0.8
COMMAND_MATCH_THRESHOLD = 0.8
CLOSE_WAIT_SECONDS = 2.5

# У браузерів заголовок вікна - це вкладка, тому за заголовком їх не закриваємо
BROWSER_EXES = {"chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "brave.exe", "vivaldi.exe"}
SHELL_TITLES = {"program manager"}


def command_exes(candidates: list) -> set:
    """Повертає імена exe команд із бази, назва яких збігається з почутою."""
    exes = set()

    for app in App_command.objects.all():
        names = [name for name in (app.app_name, app.key_word) if name]
        matched = any(
            app_match_score(candidate, name) >= COMMAND_MATCH_THRESHOLD
            for candidate in candidates for name in names
        )
        if not matched:
            continue

        path = app.path or ""
        if path.lower().endswith(".lnk"):
            path = resolve_shortcut_target(path)
        if path.lower().endswith(".exe"):
            exes.add(os.path.basename(path).lower())

    return exes


def window_score(window: dict, names: list, exes: set) -> float:
    """Оцінює, наскільки вікно підходить під почуту назву."""
    exe_base = os.path.basename(window["exe"]).lower()

    if exe_base in exes:
        return 1.0

    title = window["title"].lower().strip()
    use_title = exe_base not in BROWSER_EXES and title not in SHELL_TITLES
    best = 0.0

    for name in names:
        best = max(best, app_match_score(name, window["name"]))
        if use_title and title:
            best = max(best, app_match_score(name, title))

    return best


def find_windows_to_close(names: list, exes: set, windows: list) -> list:
    """Повертає вікна однієї програми, яка найкраще підходить під назву."""
    best = None
    best_score = 0.0

    for window in windows:
        score = window_score(window, names, exes)
        if score >= CLOSE_THRESHOLD and score > best_score:
            best, best_score = window, score

    if best is None:
        return []

    if best["host"]:
        return [w for w in windows if w["hwnd"] == best["hwnd"] or (w["host"] and w["title"] == best["title"])]

    return [w for w in windows if w["exe"] == best["exe"]]


def close_by_voice(candidates: list):
    """Закриває програму за почутою назвою.

    Повертає (статус, назва): "closed" - закрилась, "pending" - вікно ще відкрите
    (ймовірно, питає про збереження), "killed" - завершено процес без вікон,
    "not_found" - не знайдено, "unsupported" - не Windows.
    """
    if platform.system() != "Windows":
        return "unsupported", ""

    entry = find_system_target(candidates, SYSTEM_MATCH_LOOSE)
    label = entry["title"] if entry else candidates[0]
    names = [candidate.lower() for candidate in candidates]

    if entry:
        names += [name.lower() for name in entry["names"]] + [entry["title"].lower()]

    exes = command_exes(candidates)
    group = find_windows_to_close(names, exes, snapshot_window_details())

    if group:
        for window in group:
            send_close(window["hwnd"])

        time.sleep(CLOSE_WAIT_SECONDS)
        still_open = {window["hwnd"] for window in snapshot_window_details()}
        pending = [window for window in group if window["hwnd"] in still_open]
        return ("pending" if pending else "closed"), label

    # Вікон немає - завершуємо фонові процеси, якщо знаємо їхні імена
    processes = set(exes)
    if entry:
        processes.update(SYSTEM_PROCESSES.get(entry["title"], ()))

    killed = False
    for process in processes:
        result = subprocess.run(["taskkill", "/IM", process, "/F"], capture_output=True)
        killed = killed or result.returncode == 0

    return ("killed" if killed else "not_found"), label
