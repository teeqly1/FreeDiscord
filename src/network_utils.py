"""
FreeDiscord - Network Utilities & Diagnostics Module
Обеспечивает проверку связи с серверами Discord, очистку DNS и оптимизацию сети.
"""

import socket
import ssl
import time
import subprocess
import urllib.request

DISCORD_HOSTS = [
    {
        "name": "Discord Web & API",
        "host": "discord.com",
        "url": "https://discord.com",
        "description": "Основной сайт и API авторизации/сообщений"
    },
    {
        "name": "Discord Gateway",
        "host": "gateway.discord.gg",
        "url": "https://gateway.discord.gg",
        "description": "Шлюз передачи сообщений и статусов в реальном времени"
    },
    {
        "name": "Discord CDN / Media",
        "host": "cdn.discordapp.com",
        "url": "https://cdn.discordapp.com",
        "description": "Сервер загрузки аватарок, картинок, файлов и медиа"
    },
    {
        "name": "Discord Status",
        "host": "status.discord.com",
        "url": "https://status.discord.com",
        "description": "Официальный статус инфраструктуры Discord"
    }
]

def check_single_endpoint(endpoint: dict, timeout: float = 3.5) -> dict:
    """
    Проверяет доступность одного узла Discord:
    1. Разрешение DNS
    2. TCP соединение
    3. TLS рукопожатие (HTTPS)
    """
    host = endpoint["host"]
    url = endpoint["url"]
    result = {
        "name": endpoint["name"],
        "host": host,
        "description": endpoint["description"],
        "ip": None,
        "dns_time_ms": None,
        "tcp_time_ms": None,
        "tls_ok": False,
        "status_code": None,
        "latency_ms": None,
        "error": None
    }
    
    # 1. DNS Resolution
    t_start = time.time()
    try:
        ip = socket.gethostbyname(host)
        result["ip"] = ip
        result["dns_time_ms"] = round((time.time() - t_start) * 1000, 1)
    except Exception as e:
        result["error"] = f"Ошибка DNS: {e}"
        return result

    # 2. TCP Ping
    t_tcp = time.time()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((ip, 443))
        result["tcp_time_ms"] = round((time.time() - t_tcp) * 1000, 1)
        s.close()
    except Exception as e:
        result["error"] = f"TCP порт 443 недоступен: {e}"
        return result

    # 3. HTTP / TLS Handshake
    t_req = time.time()
    try:
        # Проверяем реальный HTTPS запрос
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            result["status_code"] = response.status
            result["tls_ok"] = True
            result["latency_ms"] = round((time.time() - t_req) * 1000, 1)
    except urllib.error.HTTPError as e:
        # HTTP ошибки вроде 403/404 на cdn тоже означают успешное TLS соединение
        result["status_code"] = e.code
        result["tls_ok"] = True
        result["latency_ms"] = round((time.time() - t_req) * 1000, 1)
    except Exception as e:
        err_msg = str(e)
        if "timed out" in err_msg.lower():
            result["error"] = "Таймаут TLS Handshake (Блокировка DPI ТСПУ)"
        elif "connection reset" in err_msg.lower():
            result["error"] = "Сброс соединения TCP RST (Блокировка провайдера)"
        else:
            result["error"] = f"Ошибка: {err_msg[:60]}"
            
    return result

from concurrent.futures import ThreadPoolExecutor

def run_diagnostics() -> list:
    """Выполняет параллельную проверку всех серверов Discord"""
    with ThreadPoolExecutor(max_workers=len(DISCORD_HOSTS)) as executor:
        results = list(executor.map(check_single_endpoint, DISCORD_HOSTS))
    return results

def flush_dns() -> tuple[bool, str]:
    """Сбрасывает системный кэш DNS Windows"""
    try:
        res = subprocess.run(
            ["ipconfig", "/flushdns"],
            capture_output=True,
            text=True,
            check=True
        )
        return True, "Кэш сопоставителя DNS успешно очищен."
    except Exception as e:
        return False, f"Не удалось очистить кэш DNS: {e}"

def set_fast_dns(primary: str = "1.1.1.1", secondary: str = "8.8.8.8") -> tuple[bool, str]:
    """
    Устанавливает быстрые незаблокированные DNS (Cloudflare / Google)
    на активных сетевых адаптерах (требует прав администратора).
    """
    try:
        # PowerShell команда для установки DNS на основном адаптере
        ps_cmd = (
            f"Get-NetAdapter | Where-Object {{ $_.Status -eq 'Up' }} | "
            f"Set-DnsClientServerAddress -ServerAddresses ('{primary}', '{secondary}')"
        )
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True
        )
        if res.returncode == 0:
            flush_dns()
            return True, f"Установлены быстрые DNS: {primary}, {secondary}"
        else:
            return False, f"Ошибка установки DNS (нужны права администратора): {res.stderr.strip()}"
    except Exception as e:
        return False, f"Исключение при смене DNS: {e}"
