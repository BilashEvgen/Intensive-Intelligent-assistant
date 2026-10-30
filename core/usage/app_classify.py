import re


SECONDARY_THRESHOLD = 1.0

SECONDARY_MATRIX = (
    # Назва застосунку
    ("name", r"\bun-?instal\w*|\bunins\w*|\bвидал\w*|\bудал\w*|\bдеінсталя\w*|\bдеинсталл\w*", 2.0),
    ("name", r"\bsetup\b|\binstall(er|ation)?\b|\bінсталя\w*|\bвстановл\w*|\bустановк\w*|\bустановщик\w*", 1.5),
    ("name", r"\bupdat(e|er|es)\b|\bupgrade\b|\bоновл\w*|\bобновл\w*", 1.2),
    ("name", r"\brepair\b|\bвідновл\w*", 1.2),
    ("name", r"\bredist\w*|\bvc_?redist\w*", 2.0),
    ("name", r"\bcrash\w*|\bbug-?report\w*|\breporter\b", 1.0),
    ("name", r"\bdiagnostic\w*|\btelemetry\b", 1.0),
    ("name", r"\breadme\b|\brelease notes\b|\blicen[sc]e\b|\beula\b", 1.2),
    ("name", r"\bhelper\b", 1.0),
    ("name", r"\bhelp\b|\bmanual\b|\bdocumentation\b|\bдовідк\w*|\bпосібник\w*", 0.7),
    ("name", r"\bwebsite\b|\bweb site\b|\bсайт\w*", 1.0),
    ("name", r"\bvisit\b", 0.7),
    ("name", r"\bservice\b|\bagent\b|\bdaemon\b", 0.6),
    # Шлях до файлу
    ("path", r"[\\/](temp|tmp|cache|installer|setup|updates?|crashpad|redist)[\\/]", 1.0),
    ("path", r"[\\/]windows[\\/](installer|softwaredistribution|winsxs)[\\/]", 2.0),
    ("path", r"\$patchcache\$", 2.0),
    ("path", r"\.(msi|msp|bat|cmd|ps1|reg)$", 1.5),
)


COMPILED = tuple(
    (target, re.compile(pattern, re.IGNORECASE), weight)
    for target, pattern, weight in SECONDARY_MATRIX
)


def secondary_score(name: str, path: str = "") -> float:
    """Повертає суму ваг ознак вторинного застосунку."""
    fields = {"name": (name or "").strip(), "path": (path or "").strip()}
    return sum(
        weight
        for target, pattern, weight in COMPILED
        if pattern.search(fields[target])
    )


def is_secondary_app(name: str, path: str = "") -> bool:
    """Перевіряє, чи є застосунок вторинним (інсталятор, апдейтер тощо)."""
    return secondary_score(name, path) >= SECONDARY_THRESHOLD


def filter_primary_apps(apps: list) -> list:
    """Залишає лише первинні застосунки."""
    return [app for app in apps if not is_secondary_app(app.get("name", ""), app.get("path", ""))]
































