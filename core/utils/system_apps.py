import json
import os
import platform
import subprocess

from core.utils.fuzzy_match import similarity
MIN_MATCH_SCORE = 0.55


def scan_shortcuts_windows() -> dict:
    """Збирає ярлики застосунків Windows."""
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


_NOISE_EXE_PATTERNS = (
    "unins", "uninstall", "setup", "install", "update", "updater",
    "helper", "crashpad", "crashhandler", "vcredist", "vc_redist",
    "redist", "report", "diagnostic", "repair",
)


def is_noise_exe(filename: str) -> bool:
    """Перевіряє, чи є exe службовим."""
    name = filename.lower()
    return any(pattern in name for pattern in _NOISE_EXE_PATTERNS)


def scan_program_files_windows(max_depth: int = 4) -> dict:
    """Шукає exe у каталогах Program Files."""
    apps = {}
    program_dirs = [
        os.environ.get("ProgramFiles", "C:\\Program Files"),
        os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
    ]
    skip_dirs = {"common files", "windowsapps"}

    for base_dir in program_dirs:
        if not base_dir or not os.path.exists(base_dir):
            continue

        base_depth = base_dir.rstrip("\\/").count(os.sep)

        for root, dirs, files in os.walk(base_dir):
            depth = root.rstrip("\\/").count(os.sep) - base_depth

            if depth == 0:
                dirs[:] = [d for d in dirs if d.lower() not in skip_dirs]

            if depth >= max_depth:
                dirs[:] = []
                continue

            for file in files:
                if file.lower().endswith(".exe") and not is_noise_exe(file):
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
            errors="replace",
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
    """Шукає застосунки у стандартних каталогах macOS і Linux."""
    apps = {}
    search_dirs = ["/Applications", os.path.expanduser("~/Applications"), "/usr/share/applications"]

    def _collect(directory):
        if not os.path.exists(directory):
            return
        for entry in os.listdir(directory):
            path = os.path.join(directory, entry)
            if entry.lower().endswith(".app"):
                name = entry[:-4]
                apps.setdefault(name.lower(), {"name": name, "path": path})
            elif entry.lower().endswith(".desktop"):
                name = entry[:-8]
                apps.setdefault(name.lower(), {"name": name, "path": path})

    for search_dir in search_dirs:
        if not os.path.exists(search_dir):
            continue

        _collect(search_dir)

        for entry in os.listdir(search_dir):
            subdir = os.path.join(search_dir, entry)
            if os.path.isdir(subdir) and not entry.lower().endswith((".app",)):
                _collect(subdir)

    return apps


def list_installed_apps() -> list:
    """Повертає список встановлених застосунків."""
    system = platform.system()
    apps = {}

    if system == "Windows":
        apps.update(scan_start_apps_windows())
        for key, value in scan_shortcuts_windows().items():
            apps.setdefault(key, value)
        for key, value in scan_program_files_windows().items():
            apps.setdefault(key, value)
    else:
        apps.update(scan_apps_mac_linux())

    return list(apps.values())


def word_level_score(candidate: str, app_name: str) -> float:
    """Оцінює схожість назв за окремими словами."""
    candidate_words = candidate.split()
    app_words = app_name.split()

    if not candidate_words or not app_words:
        return 0.0

    per_word_scores = [
        max(similarity(cw, aw) for aw in app_words)
        for cw in candidate_words
    ]

    return min(per_word_scores)


def app_match_score(candidate: str, app_name: str) -> float:
    """Обчислює оцінку схожості назв."""
    candidate = candidate.lower().strip()
    app_name = app_name.lower().strip()

    word_score = word_level_score(candidate, app_name)
    whole_score = similarity(candidate, app_name)

    return word_score * 0.75 + whole_score * 0.25


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