import json
import os
import platform
import subprocess

from core.utils.fuzzy_match import similarity
MIN_MATCH_SCORE = 0.45


def scan_shortcuts_windows() -> dict:
    """Звичайні .lnk-ярлики з меню Пуск / робочого столу."""
    apps = {}
    shortcut_dirs = [
        os.path.expanduser("~\\Desktop"),
        "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs",
        "C:\\Users\\Public\\Desktop",
        os.path.join(os.environ.get("APPDATA", ""), "Microsoft\\Windows\\Start Menu\\Programs"),
    ]

    for shortcut_dir in shortcut_dirs:
        if not shortcut_dir or not os.path.exists(shortcut_dir):
            continue
        for root, _, files in os.walk(shortcut_dir):
            for file in files:
                if file.lower().endswith(".lnk"):
                    name = file[:-4]
                    apps.setdefault(name.lower(), {"name": name, "path": os.path.join(root, file)})

    return apps


def scan_start_apps_windows() -> dict:
    """Повертає застосунки меню Пуск Windows."""
    apps = {}
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-StartApps | ConvertTo-Json -Compress"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return apps

        data = json.loads(result.stdout)
        if isinstance(data, dict):
            data = [data]

        for item in data:
            name = (item.get("Name") or "").strip()
            app_id = (item.get("AppID") or "").strip()

            if not name or not app_id:
                continue

            if "!" in app_id or app_id.startswith("{"):
                path = "shell:AppsFolder\\" + app_id
            else:
                path = app_id

            apps.setdefault(name.lower(), {"name": name, "path": path})

    except Exception:
        pass

    return apps


def scan_apps_mac_linux() -> dict:
    apps = {}
    search_dirs = ["/Applications", os.path.expanduser("~/Applications"), "/usr/share/applications"]

    for search_dir in search_dirs:
        if not os.path.exists(search_dir):
            continue
        for entry in os.listdir(search_dir):
            path = os.path.join(search_dir, entry)
            if entry.lower().endswith(".app"):
                name = entry[:-4]
                apps.setdefault(name.lower(), {"name": name, "path": path})
            elif entry.lower().endswith(".desktop"):
                name = entry[:-8]
                apps.setdefault(name.lower(), {"name": name, "path": path})

    return apps


def list_installed_apps() -> list:
    """Повертає список встановлених застосунків: [{"name": ..., "path": ...}, ...]."""
    system = platform.system()
    apps = {}

    if system == "Windows":
        apps.update(scan_start_apps_windows())
        for key, value in scan_shortcuts_windows().items():
            apps.setdefault(key, value)
    else:
        apps.update(scan_apps_mac_linux())

    return list(apps.values())


def app_match_score(candidate: str, app_name: str) -> float:
    """Обчислює схожість слова й назви застосунку."""
    candidate = candidate.lower().strip()
    app_name = app_name.lower().strip()

    return similarity(candidate, app_name)


def find_matching_apps(candidate: str, min_score: float = MIN_MATCH_SCORE, limit: int = 15) -> list:
    """Знаходить застосунки зі схожою назвою."""
    candidate = (candidate or "").strip()
    if not candidate:
        return []

    scored = []
    for app in list_installed_apps():
        score = app_match_score(candidate, app["name"])
        if score >= min_score:
            scored.append((score, app))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [app for _, app in scored[:limit]]