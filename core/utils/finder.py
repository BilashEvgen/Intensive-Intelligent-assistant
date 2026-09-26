import os
import platform
import subprocess

def find_app_path(app_name: str):
    system = platform.system()
    
    if app_name.lower().endswith(".exe"):
        app_name = app_name[:-4]
    elif app_name.lower().endswith(".app"):
        app_name = app_name[:-4]
        
    try:
        if system == "Windows":
            command = ["where", app_name]
        else:
            command = ["which", app_name]
            
        result = subprocess.run(
            command,
            capture_output = True,
            text = True
        )
        if result.returncode == 0 and result.stdout.strip():
            path = result.stdout.strip().split("\n")[0].strip()
            if os.path.exists(path):
                return path
    except:
        pass
    
    if system == "Windows":
        shortcut_dirs = [
            os.path.expanduser("~\\Desktop"),
            "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs",
            "C:\\Users\\Public\\Desktop",
            os.path.join(os.environ.get("APPDATA",""),
                "Microsoft\\Windows\\Start Menu\\Programs"
                ),
            
        ]
    
        for dir in shortcut_dirs:
            if not os.path.exists(dir):
                continue
            for root, dirs, files in os.walk(dir):
                for file in files:
                    if file.lower().endswith(".lnk") and app_name.lower() in file.lower():
                        return os.path.join(root, file)
        search_dirs =  [
            os.environ.get("ProgramFiles", "C:\\Program Files"),
            os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
            os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32"),
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local")),
            os.path.expanduser("~\\AppData\\Roaming")
        ]
        extensions = [".exe"]
    else:
        search_dirs = [
            "/usr/bin",
            "/usr/local/bin",
            "/Applications",
            os.path.expanduser("~/Applications")
        ]
        extensions = ["", ".app"]
    
    for root_dir in search_dirs:

        if not os.path.exists(root_dir):
            continue
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                for ext in extensions:
                    if file.lower() == app_name.lower() + ext:
                        return os.path.join(root, file)
            if root.count(os.sep) - root_dir.count(os.sep) > 3:
                dirs[:] = []

    return None
