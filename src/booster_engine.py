"""
FreeDiscord - Booster Core Engine
Управляет процессами обхода блокировок:
1. Системный WinWS Booster (Zapret-движок для трафика, медиа и голосовых каналов Discord UDP)
2. Глубокая кастомизация (настройка параметров Fake-TLS, Fake-QUIC, десинхронизации и UDP)
3. Локальный Python Desync Proxy (без прав администратора)
4. Управление системной службой Windows
"""

import os
import sys
import json
import time
import ctypes
import winreg
import socket
import select
import threading
import subprocess
import psutil

# Пути к компонентам
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CORE_DIR = os.path.join(BASE_DIR, "core")
BIN_DIR = os.path.join(CORE_DIR, "bin")
LISTS_DIR = os.path.join(CORE_DIR, "lists")
WINWS_EXE = os.path.join(BIN_DIR, "winws.exe")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

# Пресеты готовых стратегий
STRATEGIES = {
    "ALT": {
        "title": "General ALT (Рекомендуемая 2024-2026)",
        "file": "general (ALT).bat",
        "description": "Fake TLS + Fake QUIC + Active UDP Discord (работает сайт, чаты, медиа и голос)",
        "provider": "Универсально: Ростелеком, МТС, Дом.ру, Билайн, Т2, Мегафон"
    },
    "FAKE_TLS_AUTO_ALT": {
        "title": "Fake TLS Auto Alt",
        "file": "general (FAKE TLS AUTO ALT).bat",
        "description": "Автоматическая подстройка под сигнатуры DPI с фейковыми TLS заголовками",
        "provider": "Ростелеком, Дом.ру, региональные провайдеры"
    },
    "FAKE_TLS_AUTO_ALT2": {
        "title": "Fake TLS Auto Alt 2",
        "file": "general (FAKE TLS AUTO ALT2).bat",
        "description": "Вторая вариация авто-фейков для сложных узлов ТСПУ",
        "provider": "МТС, МГТС, Ситилинк"
    },
    "FAKE_TLS_AUTO_ALT3": {
        "title": "Fake TLS Auto Alt 3 (Новейший)",
        "file": "general (FAKE TLS AUTO ALT3).bat",
        "description": "Специфический тайминг-сплит под обновленные фильтры 2026 года",
        "provider": "Провайдеры с глубоким инспектированием UDP/STUN"
    },
    "SIMPLE_FAKE_ALT": {
        "title": "Simple Fake Alt",
        "file": "general (SIMPLE FAKE ALT).bat",
        "description": "Упрощенный алгоритм с минимальной задержкой пинга",
        "provider": "Билайн, Т2, Yota"
    },
    "SIMPLE_FAKE": {
        "title": "Simple Fake Standard",
        "file": "general (SIMPLE FAKE).bat",
        "description": "Базовый фейковый TLS десинхронизатор",
        "provider": "Мегафон, мобильные операторы"
    },
    "EXP": {
        "title": "Experimental Multi-Split",
        "file": "general (EXP).bat",
        "description": "Экспериментальная агрессивная фрагментация пакетов",
        "provider": "Если другие стратегии не помогли"
    },
    "GENERAL": {
        "title": "General Base",
        "file": "general.bat",
        "description": "Базовый универсальный профиль",
        "provider": "Любые провайдеры"
    }
}

# Доступные варианты файлов-сигнатур для глубокой настройки
AVAILABLE_PAYLOADS = {
    "fake_tls": [
        "tls_clienthello_www_google_com.bin",
        "tls_clienthello_max_ru.bin",
        "tls_clienthello_5ka_ru.bin",
        "tls_clienthello_4pda_to.bin",
        "tls_clienthello_sochi_park.bin",
        "tls_clienthello_www_sferum_ru.bin"
    ],
    "fake_quic": [
        "quic_initial_www_google_com.bin",
        "quic_initial_rutube_ru.bin",
        "quic_initial_steamcommunity_com.bin",
        "quic_initial_4pda_to.bin",
        "quic_initial_5ka_ru.bin",
        "quic_initial_tencent_com.bin"
    ],
    "desync_modes": [
        "fake,fakedsplit",
        "fake",
        "fakedsplit",
        "split2",
        "disorder2"
    ],
    "tcp_fooling": [
        "ts",
        "badseq",
        "badsum",
        "none"
    ]
}

DEFAULT_CONFIG = {
    "mode": "preset",  # "preset" или "custom"
    "active_preset": "ALT",
    "custom": {
        "fake_tls": "tls_clienthello_www_google_com.bin",
        "fake_quic": "quic_initial_www_google_com.bin",
        "discord_udp": "ACTIVE_DISCORD_UDP.bin",
        "desync_mode": "fake,fakedsplit",
        "repeats": 6,
        "fooling": "ts",
        "udp_voice_enabled": True
    }
}

def load_config() -> dict:
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULT_CONFIG, **data}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
    except Exception:
        pass

def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def request_admin_elevation(target_script: str = None, args: list = None):
    script = target_script or sys.argv[0]
    script_path = os.path.abspath(script)
    arg_str = " ".join([f'"{a}"' for a in (args or sys.argv[1:])])
    ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        sys.executable,
        f'"{script_path}" {arg_str}',
        None,
        1
    )
    sys.exit(0)

# =====================================================================
# WinWS Booster Management
# =====================================================================

class WinWSBooster:
    def __init__(self):
        self.config = load_config()
        self.active_strategy_key = self.config.get("active_preset", "ALT")
        self._current_process = None

    def get_running_process(self):
        for p in psutil.process_iter(['pid', 'name', 'create_time', 'memory_info']):
            try:
                name = p.info['name']
                if name and name.lower() == 'winws.exe':
                    return p
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None

    def is_running(self) -> bool:
        return self.get_running_process() is not None

    def get_stats(self) -> dict:
        proc = self.get_running_process()
        mode = self.config.get("mode", "preset")
        if mode == "custom":
            strategy_name = f"Кастомная ({self.config['custom']['desync_mode']}, repeats={self.config['custom']['repeats']})"
        else:
            strategy_name = STRATEGIES.get(self.active_strategy_key, {}).get("title", self.active_strategy_key)

        if proc:
            try:
                mem_mb = round(proc.memory_info().rss / (1024 * 1024), 1)
                cpu = proc.cpu_percent(interval=None)
                uptime_sec = int(time.time() - proc.create_time())
                return {
                    "running": True,
                    "pid": proc.pid,
                    "memory_mb": mem_mb,
                    "cpu_percent": cpu,
                    "uptime_sec": uptime_sec,
                    "strategy": strategy_name
                }
            except Exception:
                pass
        return {
            "running": False,
            "pid": None,
            "memory_mb": 0,
            "cpu_percent": 0,
            "uptime_sec": 0,
            "strategy": strategy_name
        }

    def _generate_custom_bat(self) -> str:
        """Создает BAT-файл с индивидуальными настройками пользователя"""
        c = self.config["custom"]
        bat_path = os.path.join(CORE_DIR, "custom_profile.bat")
        
        udp_rule = ""
        if c.get("udp_voice_enabled", True):
            udp_rule = (
                f'--filter-udp=19294-19344,50000-50100 --filter-l7=discord,stun '
                f'--dpi-desync=fake --dpi-desync-fake-discord="%BIN%{c["discord_udp"]}" '
                f'--dpi-desync-fake-stun="%BIN%{c["discord_udp"]}" --dpi-desync-repeats={c["repeats"]} --new ^\n'
            )

        content = f"""@echo off
chcp 65001 > nul
cd /d "%~dp0"
set "BIN=%~dp0bin\\"
set "LISTS=%~dp0lists\\"
cd /d %BIN%

start "zapret: custom" /min "%BIN%winws.exe" --wf-tcp=80,443,2053,2083,2087,2096,8443 --wf-udp=443,19294-19344,50000-50100 ^
--filter-udp=443 --hostlist="%LISTS%list-general.txt" --hostlist-exclude="%LISTS%list-exclude.txt" --ipset-exclude="%LISTS%ipset-exclude.txt" --dpi-desync=fake --dpi-desync-repeats={c["repeats"]} --dpi-desync-fake-quic="%BIN%{c["fake_quic"]}" --new ^
{udp_rule}--filter-tcp=80,443 --hostlist="%LISTS%list-general.txt" --hostlist-exclude="%LISTS%list-exclude.txt" --ipset-exclude="%LISTS%ipset-exclude.txt" --dpi-desync={c["desync_mode"]} --dpi-desync-repeats={c["repeats"]} --dpi-desync-fooling={c["fooling"]} --dpi-desync-fakedsplit-pattern=0x00 --dpi-desync-fake-tls="%BIN%{c["fake_tls"]}"
"""
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(content)
        return bat_path

    def start(self, strategy_key: str = None, use_custom: bool = False) -> tuple[bool, str]:
        if strategy_key:
            self.active_strategy_key = strategy_key
            self.config["active_preset"] = strategy_key
            self.config["mode"] = "preset"
            save_config(self.config)
        elif use_custom:
            self.config["mode"] = "custom"
            save_config(self.config)

        if self.is_running():
            self.stop()
            time.sleep(0.5)

        if not os.path.isfile(WINWS_EXE):
            return False, f"Исполняемый файл winws.exe не найден: {WINWS_EXE}"

        if self.config.get("mode") == "custom":
            bat_file = self._generate_custom_bat()
            strat_title = "Пользовательская конфигурация"
            bat_exec = "custom_profile.bat"
        else:
            strat_info = STRATEGIES.get(self.active_strategy_key, STRATEGIES["ALT"])
            bat_file = os.path.join(CORE_DIR, strat_info["file"])
            strat_title = strat_info["title"]
            bat_exec = strat_info["file"]

        if not os.path.isfile(bat_file):
            return False, f"Файл конфигурации не найден: {bat_file}"

        try:
            p = subprocess.Popen(
                ["cmd.exe", "/c", bat_exec],
                cwd=CORE_DIR,
                creationflags=subprocess.CREATE_NO_WINDOW,
                close_fds=True
            )
            self._current_process = p

            time.sleep(1.5)
            if self.is_running():
                return True, f"Бустер успешно запущен: {strat_title}"
            else:
                if not is_admin():
                    return False, "Для перехвата сетевых пакетов требуются права Администратора."
                return False, "Процесс winws завершился с ошибкой. Попробуйте другой профиль."
        except Exception as e:
            return False, f"Ошибка при запуске: {e}"

    def stop(self) -> tuple[bool, str]:
        try:
            subprocess.run(["taskkill", "/F", "/IM", "winws.exe"], capture_output=True, text=True)
            subprocess.run(["net", "stop", "windivert", "/y"], capture_output=True, text=True)
            time.sleep(0.5)
            return True, "Бустер успешно остановлен."
        except Exception as e:
            return False, f"Ошибка при остановке: {e}"

    def install_windows_service(self) -> tuple[bool, str]:
        if not is_admin():
            return False, "Для установки службы Windows требуются права Администратора."
        service_bat = os.path.join(CORE_DIR, "service.bat")
        try:
            subprocess.Popen(
                ["cmd.exe", "/c", f'"{service_bat}" admin'],
                cwd=CORE_DIR,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            return True, "Открыто окно управления системной службой Windows."
        except Exception as e:
            return False, f"Ошибка запуска менеджера службы: {e}"

# =====================================================================
# Native Python Desync Proxy (Режим без прав Администратора)
# =====================================================================

class PythonDesyncProxy:
    def __init__(self, host: str = "127.0.0.1", port: int = 18080):
        self.host = host
        self.port = port
        self.server_socket = None
        self.is_running = False
        self._thread = None
        self._previous_proxy_state = None

    def _enable_system_proxy(self):
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS) as key:
                try:
                    prev_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
                    prev_server, _ = winreg.QueryValueEx(key, "ProxyServer")
                    self._previous_proxy_state = (prev_enable, prev_server)
                except Exception:
                    self._previous_proxy_state = (0, "")

                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, f"{self.host}:{self.port}")
                
            ctypes.windll.wininet.InternetSetOptionW(0, 39, 0, 0)
            ctypes.windll.wininet.InternetSetOptionW(0, 37, 0, 0)
        except Exception:
            pass

    def _restore_system_proxy(self):
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS) as key:
                if self._previous_proxy_state:
                    prev_enable, prev_server = self._previous_proxy_state
                    winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, prev_enable)
                    winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, prev_server)
                else:
                    winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
                    
            ctypes.windll.wininet.InternetSetOptionW(0, 39, 0, 0)
            ctypes.windll.wininet.InternetSetOptionW(0, 37, 0, 0)
        except Exception:
            pass

    def _handle_client(self, client_sock):
        remote_sock = None
        try:
            client_sock.settimeout(10)
            req_data = client_sock.recv(4096)
            if not req_data:
                client_sock.close()
                return

            first_line = req_data.split(b"\r\n")[0].decode("latin1", errors="ignore")
            parts = first_line.split()
            if len(parts) < 2 or parts[0].upper() != "CONNECT":
                client_sock.close()
                return

            dest = parts[1]
            if ":" in dest:
                dest_host, dest_port = dest.split(":")
                dest_port = int(dest_port)
            else:
                dest_host = dest
                dest_port = 443

            remote_ip = socket.gethostbyname(dest_host)

            remote_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_sock.settimeout(10)
            remote_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            remote_sock.connect((remote_ip, dest_port))

            client_sock.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")

            tls_data = client_sock.recv(4096)
            if tls_data:
                if len(tls_data) > 5 and tls_data[0] == 0x16 and tls_data[1] == 0x03:
                    split_pos = 2
                    part1 = tls_data[:split_pos]
                    part2 = tls_data[split_pos:]

                    remote_sock.sendall(part1)
                    time.sleep(0.025)
                    remote_sock.sendall(part2)
                else:
                    remote_sock.sendall(tls_data)

            client_sock.setblocking(False)
            remote_sock.setblocking(False)

            sockets = [client_sock, remote_sock]
            while self.is_running:
                readable, _, exceptional = select.select(sockets, [], sockets, 30)
                if exceptional or not readable:
                    break

                for s in readable:
                    data = s.recv(8192)
                    if not data:
                        return
                    if s is client_sock:
                        remote_sock.sendall(data)
                    else:
                        client_sock.sendall(data)

        except Exception:
            pass
        finally:
            try:
                client_sock.close()
            except Exception:
                pass
            if remote_sock:
                try:
                    remote_sock.close()
                except Exception:
                    pass

    def _run_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(128)
        self.server_socket.settimeout(1.0)

        self._enable_system_proxy()

        while self.is_running:
            try:
                client_sock, _ = self.server_socket.accept()
                t = threading.Thread(target=self._handle_client, args=(client_sock,), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except Exception:
                break

        self._restore_system_proxy()
        try:
            self.server_socket.close()
        except Exception:
            pass

    def start(self) -> tuple[bool, str]:
        if self.is_running:
            return True, "Python Desync Proxy уже работает."

        self.is_running = True
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()
        time.sleep(0.5)
        return True, f"Python Desync Proxy запущен на {self.host}:{self.port}"

    def stop(self) -> tuple[bool, str]:
        if not self.is_running:
            return True, "Python Proxy не был запущен."

        self.is_running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        self._restore_system_proxy()
        return True, "Python Proxy остановлен, системные настройки восстановлены."
