"""
FreeDiscord - Dependency Auto-Installer
Автоматически проверяет наличие необходимых библиотек Python и устанавливает недостающие через pip.
"""

import sys
import subprocess
import importlib.util

REQUIRED_PACKAGES = {
    "pystyle": "pystyle>=2.9",
    "psutil": "psutil>=5.9.0",
    "requests": "requests>=2.31.0"
}

def is_installed(package_name: str) -> bool:
    """Проверяет установлен ли модуль в текущем окружении"""
    try:
        return importlib.util.find_spec(package_name) is not None
    except Exception:
        return False

def install_package(spec: str) -> bool:
    """Устанавливает пакет через python -m pip install"""
    try:
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", spec]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode == 0
    except Exception as e:
        print(f"[-] Ошибка при установке {spec}: {e}")
        return False

def ensure_dependencies(silent: bool = False) -> bool:
    """
    Проверяет все зависимости и автоматически доустанавливает недостающие.
    """
    missing = [pkg for pkg in REQUIRED_PACKAGES if not is_installed(pkg)]
    
    if not missing:
        if not silent:
            # Все зависимости уже установлены
            pass
        return True

    print("\n[!] Обнаружены отсутствующие зависимости: " + ", ".join(missing))
    print("[*] Автоматическая установка через pip...")

    all_ok = True
    for pkg in missing:
        spec = REQUIRED_PACKAGES[pkg]
        print(f"    -> Установка {spec}...")
        ok = install_package(spec)
        if ok:
            print(f"    [+] {pkg} успешно установлен.")
        else:
            print(f"    [-] Не удалось установить {pkg}.")
            all_ok = False

    if all_ok:
        print("[+] Все зависимости успешно установлены!\n")
    else:
        print("[!] Внимание: некоторые зависимости не удалось установить. Проверьте подключение к сети.\n")

    return all_ok

if __name__ == "__main__":
    ensure_dependencies(silent=False)
