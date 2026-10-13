import ctypes
import os
import platform
import sys
from ctypes import wintypes

import psutil

# Службові процеси та термінали, які не є застосунками користувача
IGNORED_PROCESSES = {
    "explorer", "applicationframehost", "searchhost", "searchapp", "startmenuexperiencehost",
    "shellexperiencehost", "textinputhost", "systemsettings", "lockapp", "dwm", "csrss",
    "winlogon", "taskhostw", "sihost", "ctfmon", "runtimebroker", "widgets", "conhost",
    "msedgewebview2", "windowsterminal", "cmd", "powershell", "pwsh",
    "python", "pythonw", "py",
}

GW_OWNER = 4
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
DWMWA_CLOAKED = 14


def _load_winapi():
    """Налаштовує функції WinAPI з коректними типами (важливо для 64-бітних дескрипторів)."""
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    dwmapi = ctypes.WinDLL("dwmapi")

    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = ctypes.c_long
    user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    dwmapi.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
    dwmapi.DwmGetWindowAttribute.restype = ctypes.c_long

    return user32, dwmapi


def taskbar_windows() -> dict:
    """Повертає {hwnd: pid} для вікон, які показуються на панелі завдань (правило Alt+Tab)."""
    user32, dwmapi = _load_winapi()
    enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [enum_proc, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    windows = {}

    def callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd) or user32.GetWindowTextLengthW(hwnd) == 0:
            return True

        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if ex_style & WS_EX_TOOLWINDOW:
            return True

        # Вікна з власником (діалоги) пропускаємо, якщо вони не позначені як окремі
        if user32.GetWindow(hwnd, GW_OWNER) and not (ex_style & WS_EX_APPWINDOW):
            return True

        cloaked = wintypes.DWORD(0)
        dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
        if cloaked.value:
            return True

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        windows[hwnd or 0] = pid.value
        return True

    user32.EnumWindows(enum_proc(callback), 0)
    return windows


def snapshot_windows() -> dict:
    """Повертає {hwnd: (шлях до exe, назва)} для всіх вікон застосунків користувача."""
    if platform.system() != "Windows":
        return {}

    own_pid = os.getpid()
    own_exe = os.path.normcase(sys.executable)
    cache = {}
    result = {}

    for hwnd, pid in taskbar_windows().items():
        if pid == own_pid:
            continue

        if pid not in cache:
            info = None
            try:
                exe = psutil.Process(pid).exe()
                name = os.path.splitext(os.path.basename(exe))[0]
                if exe and os.path.normcase(exe) != own_exe and name.lower() not in IGNORED_PROCESSES:
                    info = (exe, name)
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                pass
            cache[pid] = info

        if cache[pid]:
            result[hwnd] = cache[pid]

    return result


def snapshot_running_apps() -> dict:
    """Повертає {шлях до exe: назва} для запущених застосунків."""
    return {exe: name for exe, name in snapshot_windows().values()}
