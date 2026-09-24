"""
FreeDiscord - Discord Client & Web Launcher Module
Автоматически обнаруживает установленные версии Discord и запускает их.
"""

import os
import glob
import subprocess
import webbrowser

def find_discord_installations() -> list[dict]:
    """
    Ищет все установленные версии Discord в системе пользователя:
    - Discord Stable
    - Discord Canary
    - Discord PTB
    - Discord Development
    """
    found = []
    local_app = os.environ.get('LOCALAPPDATA', '')
    prog_files = os.environ.get('ProgramFiles', '')
    prog_files_x86 = os.environ.get('ProgramFiles(x86)', '')

    search_targets = [
        ("Discord Stable", os.path.join(local_app, "Discord")),
        ("Discord Canary", os.path.join(local_app, "DiscordCanary")),
        ("Discord PTB", os.path.join(local_app, "DiscordPTB")),
        ("Discord Development", os.path.join(local_app, "DiscordDevelopment")),
    ]

    for name, base_path in search_targets:
        if not os.path.isdir(base_path):
            continue
            
        update_exe = os.path.join(base_path, "Update.exe")
        direct_exes = glob.glob(os.path.join(base_path, "app-*", "Discord*.exe"))
        
        target_name = name.split()[1] + ".exe" if " " in name else "Discord.exe"
        if name == "Discord Stable":
            target_name = "Discord.exe"
            
        if os.path.isfile(update_exe):
            found.append({
                "name": name,
                "type": "launcher",
                "path": update_exe,
                "args": ["--processStart", target_name],
                "base_path": base_path
            })
        elif direct_exes:
            # Сортируем по версии и берем самый свежий
            direct_exes.sort(reverse=True)
            found.append({
                "name": name,
                "type": "direct",
                "path": direct_exes[0],
                "args": [],
                "base_path": base_path
            })

    return found

def launch_discord_app(proxy_url: str = None) -> tuple[bool, str]:
    """
    Запускает найденное приложение Discord.
    При необходимости может передать флаг прокси (--proxy-server).
    """
    installs = find_discord_installations()
    if not installs:
        return False, "Установленный Discord не найден. Вы можете открыть Discord в браузере."

    target = installs[0]
    cmd = [target["path"]] + target["args"]
    if proxy_url:
        cmd.append(f"--proxy-server={proxy_url}")

    try:
        subprocess.Popen(
            cmd,
            cwd=target["base_path"],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS if os.name == 'nt' else 0,
            close_fds=True
        )
        return True, f"Запущено приложение: {target['name']}"
    except Exception as e:
        return False, f"Ошибка при запуске Discord: {e}"

def open_discord_web() -> tuple[bool, str]:
    """Открывает веб-версию Discord в браузере по умолчанию"""
    url = "https://discord.com/app"
    try:
        webbrowser.open(url)
        return True, "Веб-версия Discord открыта в браузере по умолчанию."
    except Exception as e:
        return False, f"Не удалось открыть браузер: {e}"
