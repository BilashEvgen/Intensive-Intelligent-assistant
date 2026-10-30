import math
import os

from django.db import IntegrityError
from django.db.models import F
from django.utils import timezone

from core.models import App_usage, Discovered_app
from core.catalog.app_classify import filter_primary_apps, is_secondary_app
from core.processes.running_apps import snapshot_running_apps
from core.catalog.system_apps import app_match_score, list_installed_apps, normalize_app_path

TOP_USED_LIMIT = 30
USAGE_MIN_SCORE = 0.6
USAGE_BONUS_MAX = 0.3
USAGE_BONUS_CAP = 20


def is_launchable_path(path: str) -> bool:
    """Перевіряє доступність шляху для запуску."""
    path = normalize_app_path(path)
    if not path:
        return False
    if path.lower().startswith("shell:"):
        return True
    return os.path.exists(path)


def record_app_launch(name: str, path: str):
    """Збільшує лічильник запусків застосунку в БД."""
    name = (name or "").strip()
    path = (path or "").strip()

    if not name or not path:
        return None

    if is_secondary_app(name, path):
        return None

    norm = os.path.normcase(path)
    usage = next((row for row in App_usage.objects.all() if os.path.normcase(row.path) == norm), None)

    if usage is None:
        try:
            return App_usage.objects.create(name=name, path=path, launch_count=1)
        except IntegrityError:
            usage = App_usage.objects.get(path=path)

    App_usage.objects.filter(pk=usage.pk).update(
        launch_count=F("launch_count") + 1,
        last_used_at=timezone.now(),
    )
    return usage


def get_top_used_apps(limit: int = TOP_USED_LIMIT) -> list:
    """Повертає найчастіше запускані застосунки."""
    return list(App_usage.objects.order_by("-launch_count", "-last_used_at")[:limit])


def get_running_apps() -> list:
    """Повертає застосунки, які зараз запущені (з вікнами)."""
    try:
        return [{"name": name, "path": exe} for exe, name in snapshot_running_apps().items()]
    except Exception:
        return []


def get_primary_catalog() -> list:
    """Збирає запущені застосунки та всі застосунки з БД, відсіює вторинні.
    Запущені йдуть першими. Якщо БД порожня - додатково скануємо систему.
    """
    apps = []
    seen_names = set()
    seen_paths = set()

    def add(app):
        name_key = app["name"].lower()
        path_key = os.path.normcase(app["path"] or "")
        if name_key in seen_names or (path_key and path_key in seen_paths):
            return
        seen_names.add(name_key)
        if path_key:
            seen_paths.add(path_key)
        apps.append({"name": app["name"], "path": app["path"]})

    for app in get_running_apps():
        add(app)

    db_rows = list(Discovered_app.objects.order_by("id").values("name", "path"))
    for row in db_rows:
        add(row)

    if not db_rows:
        for app in list_installed_apps():
            add(app)

    return filter_primary_apps(apps)


def usage_bonus(launch_count: int) -> float:
    """Бонус до оцінки за частоту запусків (з обмеженням)."""
    capped = min(max(launch_count, 0), USAGE_BONUS_CAP)
    return USAGE_BONUS_MAX * math.log1p(capped) / math.log1p(USAGE_BONUS_CAP)


def pick_top_suggestion(candidate: str, primary_matches: list):
    """Обирає застосунок, який запропонувати відкрити одразу."""
    best_app = None
    best_key = 0.0

    for row in get_top_used_apps():
        if is_secondary_app(row.name, row.path) or not is_launchable_path(row.path):
            continue

        score = app_match_score(candidate, row.name)
        if score < USAGE_MIN_SCORE:
            continue

        key = score + usage_bonus(row.launch_count)
        if key > best_key:
            best_key = key
            best_app = {"name": row.name, "path": row.path}

    if best_app:
        return best_app, "usage"

    if primary_matches:
        return primary_matches[0], "list"

    return None, None
