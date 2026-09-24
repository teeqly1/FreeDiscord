"""
FreeDiscord - Professional Discord Booster for Windows (Console Edition)
Разработано для стабильного доступа к Discord в РФ без задержек и ограничений.
"""

import os
import sys
import time
import atexit

import pyui
from pyui import UIColors, colorize, render_badge, panel, set_title, clear
import booster_engine
from booster_engine import (
    WinWSBooster,
    PythonDesyncProxy,
    STRATEGIES,
    AVAILABLE_PAYLOADS,
    load_config,
    save_config,
    is_admin,
    request_admin_elevation
)
import discord_launcher
import network_utils

# Инициализация ядра
booster = WinWSBooster()
py_proxy = PythonDesyncProxy()

def cleanup():
    if py_proxy.is_running:
        py_proxy.stop()

atexit.register(cleanup)

def load_ascii_art() -> str:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ascii.txt")
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().rstrip()
        except Exception:
            pass
    return "  FreeDiscord Booster"

ASCII_ART = load_ascii_art()

def draw_header():
    clear()
    set_title("FreeDiscord v2.5 - Professional Edition")
    
    # 1. Логотип с градиентом
    print(pyui.gradient_text(ASCII_ART, (88, 101, 242), (0, 210, 255)))
    print()

    # 2. Информационная панель статуса
    stats = booster.get_stats()
    is_adm = is_admin()

    if stats["running"]:
        status_line = f"{render_badge('АКТИВЕН', 'RUNNING')}  PID: {stats['pid']}  |  RAM: {stats['memory_mb']} MB  |  Аптайм: {stats['uptime_sec']}с"
    else:
        status_line = f"{render_badge('ОСТАНОВЛЕН', 'STOPPED')}  (Служба не запущена)"

    if py_proxy.is_running:
        status_line += f"  {colorize('[Proxy: 18080]', UIColors.CYAN)}"

    admin_badge = render_badge("АДМИНИСТРАТОР", "ADMIN") if is_adm else render_badge("ПОЛЬЗОВАТЕЛЬ (Голос требует Админ)", "USER")
    
    discord_apps = discord_launcher.find_discord_installations()
    app_info = f"{discord_apps[0]['name']} [Обнаружен]" if discord_apps else "Не найден в %LocalAppData%"

    info_lines = [
        f"Статус сервиса:   {status_line}",
        f"Активный режим:   {colorize(stats['strategy'], UIColors.WHITE)}",
        f"Права доступа:    {admin_badge}",
        f"Клиент Discord:   {colorize(app_info, UIColors.LIGHT_GRAY)}"
    ]
    print(panel("МОНИТОРИНГ СИСТЕМЫ", info_lines, width=76, color=UIColors.DISCORD_BLURPLE))
    print()

def print_menu():
    cat1 = [
        f"  {colorize('[1]', UIColors.CYAN)} {colorize('Запустить zapret', UIColors.WHITE)}      - Рекомендуемый режим (Голос + Текст + CDN)",
        f"  {colorize('[2]', UIColors.CYAN)} {colorize('Остановить zapret', UIColors.WHITE)}               - Завершение процессов и очистка драйвера",
        f"  {colorize('[3]', UIColors.CYAN)} {colorize('Запустить Discord App', UIColors.WHITE)}            - Запуск найденного десктопного приложения",
        f"  {colorize('[4]', UIColors.CYAN)} {colorize('Открыть Discord Web', UIColors.WHITE)}            - Открытие веб-версии в браузере"
    ]
    print(panel("1. УПРАВЛЕНИЕ И ЗАПУСК", cat1, width=76, color=UIColors.CYAN))
    print()

    cat2 = [
        f"  {colorize('[5]', UIColors.DISCORD_BLURPLE)} {colorize('Профили провайдеров', UIColors.WHITE)}             - 8 готовых стратегий обхода (Ростелеком, МТС, Дом.ру)",
        f"  {colorize('[6]', UIColors.DISCORD_BLURPLE)} {colorize('Глубокая настройка параметров', UIColors.WHITE)}     - Fake-TLS, Fake-QUIC, UDP Voice, Repeats, Fooling",
        f"  {colorize('[7]', UIColors.DISCORD_BLURPLE)} {colorize('Локальный Python Proxy', UIColors.WHITE)}            - Альтернативный сплиттер (без прав Администратора)"
    ]
    print(panel("2. КОНФИГУРАЦИЯ И АЛГОРИТМЫ", cat2, width=76, color=UIColors.DISCORD_BLURPLE))
    print()

    cat3 = [
        f"  {colorize('[8]', UIColors.MINT)} {colorize('Диагностика узлов Discord', UIColors.WHITE)}      - Тестирование REST API, Gateway, CDN и замер пинга",
        f"  {colorize('[9]', UIColors.MINT)} {colorize('Очистить DNS и оптимизировать', UIColors.WHITE)}  - Сброс кэша resolver и установка DNS 1.1.1.1 / 8.8.8.8",
        f"  {colorize('[S]', UIColors.MINT)} {colorize('Служба Windows (Автозапуск)', UIColors.WHITE)}     - Установка службы для работы в фоне после перезагрузки",
        f"  {colorize('[U]', UIColors.YELLOW)} {colorize('Перезапуск от Администратора', UIColors.WHITE)}    - Запрос прав UAC для перехвата UDP голосовых каналов",
        f"  {colorize('[0]', UIColors.RED)} {colorize('Выход из программы', UIColors.WHITE)}"
    ]
    print(panel("3. СЕТЬ И СИСТЕМА", cat3, width=76, color=UIColors.MINT))
    print()

def handle_start_booster():
    if booster.is_running():
        print(colorize("\n  [*]  уже активен.", UIColors.YELLOW))
        time.sleep(1.2)
        return

    if not is_admin():
        print(colorize("\n  [!] Внимание: для перехвата сетевых пакетов и работы голосовых каналов", UIColors.YELLOW))
        print(colorize("      рекомендуется запуск от имени Администратора.", UIColors.YELLOW))
        choice = input("  Перезапустить с правами Администратора? (y/n, Enter=y): ").strip().lower()
        if choice in ('', 'y', 'yes', 'д', 'да'):
            request_admin_elevation()
            return

    print(colorize("\n  [*] Запуск...", UIColors.CYAN))
    ok, msg = booster.start()
    if ok:
        print(colorize(f"  [+] {msg}", UIColors.MINT))
    else:
        print(colorize(f"  [-] {msg}", UIColors.RED))
    print("\n  Нажмите Enter для возврата...")
    input()

def handle_stop_booster():
    print(colorize("\n  [*] Остановка всех компонентов...", UIColors.YELLOW))
    ok1, msg1 = booster.stop()
    ok2, msg2 = py_proxy.stop()
    print(colorize(f"  [+] {msg1}", UIColors.MINT))
    time.sleep(1.0)

def handle_launch_discord_app():
    print(colorize("\n  [*] Поиск Discord в системе...", UIColors.CYAN))
    installs = discord_launcher.find_discord_installations()
    if not installs:
        print(colorize("  [-] Приложение не найдено в %LocalAppData%\\Discord.", UIColors.RED))
        c = input("  Открыть веб-версию в браузере? (y/n, Enter=y): ").strip().lower()
        if c in ('', 'y', 'yes', 'д', 'да'):
            discord_launcher.open_discord_web()
    else:
        app = installs[0]
        print(colorize(f"  [+] Найдено: {app['name']}", UIColors.MINT))
        if not booster.is_running() and not py_proxy.is_running:
            print(colorize("  [!] Предупреждение: zapret остановлен, к discord'у невозможно подключится", UIColors.YELLOW))
        ok, msg = discord_launcher.launch_discord_app()
        if ok:
            print(colorize(f"  [+] {msg}", UIColors.MINT))
        else:
            print(colorize(f"  [-] {msg}", UIColors.RED))
    time.sleep(1.5)

def handle_launch_discord_web():
    print(colorize("\n  [*] Открытие https://discord.com/app в браузере...", UIColors.CYAN))
    ok, msg = discord_launcher.open_discord_web()
    if ok:
        print(colorize(f"  [+] {msg}", UIColors.MINT))
    else:
        print(colorize(f"  [-] {msg}", UIColors.RED))
    time.sleep(1.2)

def handle_choose_strategy():
    clear()
    keys = list(STRATEGIES.keys())
    lines = []
    lines.append("Выберите оптимальный пресет под вашего интернет-провайдера:\n")
    for idx, k in enumerate(keys, 1):
        strat = STRATEGIES[k]
        is_cur = " [АКТИВЕН]" if (k == booster.active_strategy_key and booster.config.get("mode") != "custom") else ""
        lines.append(f"  [{idx}] {strat['title']}{is_cur}")
        lines.append(f"      Описание:    {strat['description']}")
        lines.append(f"      Провайдеры:  {strat['provider']}\n")
    lines.append("  [0] Отмена и возврат в главное меню")
    
    print(panel("ВЫБОР ГОТОВОГО ПРОФИЛЯ ОБХОДА", lines, width=76, color=UIColors.DISCORD_BLURPLE))
    print()
    choice = input("  Номер профиля (0-" + str(len(keys)) + "): ").strip()

    if choice.isdigit() and 1 <= int(choice) <= len(keys):
        sel_key = keys[int(choice) - 1]
        print(colorize(f"\n  [+] Выбран профиль: {STRATEGIES[sel_key]['title']}", UIColors.MINT))
        booster.start(strategy_key=sel_key)
        time.sleep(1.2)

def handle_deep_configuration():
    """Меню глубокой кастомизации сетевых параметров обхода"""
    while True:
        clear()
        cfg = booster.config["custom"]
        lines = [
            f"Текущие параметры пользовательского профиля:\n",
            f"  [1] Fake TLS сигнатура:   {colorize(cfg['fake_tls'], UIColors.CYAN)}",
            f"  [2] Fake QUIC сигнатура:  {colorize(cfg['fake_quic'], UIColors.CYAN)}",
            f"  [3] Режим десинхрона:     {colorize(cfg['desync_mode'], UIColors.CYAN)}",
            f"  [4] Повторы (Repeats):    {colorize(str(cfg['repeats']), UIColors.CYAN)}",
            f"  [5] TCP Fooling:          {colorize(cfg['fooling'], UIColors.CYAN)}",
            f"  [6] Discord UDP Voice:    {colorize('ВКЛЮЧЕН' if cfg['udp_voice_enabled'] else 'ОТКЛЮЧЕН', UIColors.MINT if cfg['udp_voice_enabled'] else UIColors.RED)}",
            f"",
            f"  [S] {colorize('Сохранить и запустить кастомный профиль', UIColors.MINT)}",
            f"  [R] Сбросить настройки на рекомендованные",
            f"  [0] Назад в главное меню"
        ]
        print(panel("Настройка", lines, width=76, color=UIColors.DISCORD_BLURPLE))
        print()
        c = input("  Выберите параметр для изменения: ").strip().upper()

        if c == "1":
            print("\n  Доступные сигнатуры Fake TLS:")
            for i, p in enumerate(AVAILABLE_PAYLOADS["fake_tls"], 1):
                print(f"    [{i}] {p}")
            sub = input("  Выберите номер: ").strip()
            if sub.isdigit() and 1 <= int(sub) <= len(AVAILABLE_PAYLOADS["fake_tls"]):
                cfg["fake_tls"] = AVAILABLE_PAYLOADS["fake_tls"][int(sub) - 1]
                save_config(booster.config)

        elif c == "2":
            print("\n  Доступные сигнатуры Fake QUIC:")
            for i, p in enumerate(AVAILABLE_PAYLOADS["fake_quic"], 1):
                print(f"    [{i}] {p}")
            sub = input("  Выберите номер: ").strip()
            if sub.isdigit() and 1 <= int(sub) <= len(AVAILABLE_PAYLOADS["fake_quic"]):
                cfg["fake_quic"] = AVAILABLE_PAYLOADS["fake_quic"][int(sub) - 1]
                save_config(booster.config)

        elif c == "3":
            print("\n  Режимы десинхронизации TCP:")
            for i, m in enumerate(AVAILABLE_PAYLOADS["desync_modes"], 1):
                print(f"    [{i}] {m}")
            sub = input("  Выберите номер: ").strip()
            if sub.isdigit() and 1 <= int(sub) <= len(AVAILABLE_PAYLOADS["desync_modes"]):
                cfg["desync_mode"] = AVAILABLE_PAYLOADS["desync_modes"][int(sub) - 1]
                save_config(booster.config)

        elif c == "4":
            sub = input("\n  Введите количество повторов (1-12, по умолчанию 6): ").strip()
            if sub.isdigit() and 1 <= int(sub) <= 12:
                cfg["repeats"] = int(sub)
                save_config(booster.config)

        elif c == "5":
            print("\n  Методы обхода DPI (TCP Fooling):")
            for i, f in enumerate(AVAILABLE_PAYLOADS["tcp_fooling"], 1):
                print(f"    [{i}] {f}")
            sub = input("  Выберите номер: ").strip()
            if sub.isdigit() and 1 <= int(sub) <= len(AVAILABLE_PAYLOADS["tcp_fooling"]):
                cfg["fooling"] = AVAILABLE_PAYLOADS["tcp_fooling"][int(sub) - 1]
                save_config(booster.config)

        elif c == "6":
            cfg["udp_voice_enabled"] = not cfg["udp_voice_enabled"]
            save_config(booster.config)

        elif c == "S":
            save_config(booster.config)
            print(colorize("\n  [*] Запуск кастомного профиля...", UIColors.CYAN))
            booster.start(use_custom=True)
            time.sleep(1.5)
            break

        elif c == "R":
            booster.config["custom"] = booster_engine.DEFAULT_CONFIG["custom"].copy()
            save_config(booster.config)
            print(colorize("\n  [+] Параметры сброшены на рекомендованные.", UIColors.MINT))
            time.sleep(1.0)

        elif c == "0":
            break

def handle_diagnostics():
    clear()
    print(colorize("  [*] Выполняется параллельная диагностика узлов Discord...", UIColors.CYAN))
    results = network_utils.run_diagnostics()

    lines = []
    for r in results:
        name = r["name"]
        host = r["host"]
        ip = r["ip"] or "DNS не разрешен"
        if r["tls_ok"]:
            badge = render_badge("ДОСТУПЕН", "SUCCESS")
            detail = f"HTTP {r['status_code']}  |  Ping: {r['latency_ms']} ms  |  IP: {ip}"
        else:
            badge = render_badge("БЛОКИРУЕТСЯ", "DANGER")
            detail = f"IP: {ip}  |  {r['error']}"

        lines.append(f"{badge}  {colorize(name, UIColors.WHITE)} ({host})")
        lines.append(f"     {colorize(detail, UIColors.LIGHT_GRAY)}")
        lines.append("")

    all_ok = all(r["tls_ok"] for r in results)
    if all_ok:
        lines.append(colorize("Итог: все узлы Discord работают штатно.", UIColors.MINT))
    else:
        lines.append(colorize("Итог: часть узлов заблокирована. Запустите freediscord или смените профиль.", UIColors.YELLOW))

    print(panel("РЕЗУЛЬТАТЫ ДИАГНОСТИКИ СЕТИ", lines, width=76, color=UIColors.MINT))
    print()
    input("  Нажмите Enter для возврата...")

def handle_python_proxy():
    if py_proxy.is_running:
        print(colorize("\n  [*] Остановка Python Desync Proxy...", UIColors.YELLOW))
        py_proxy.stop()
        print(colorize("  [+] Локальный прокси остановлен, настройки Windows восстановлены.", UIColors.MINT))
    else:
        print(colorize("\n  [*] Запуск Python Desync Proxy (порт 18080)...", UIColors.CYAN))
        ok, msg = py_proxy.start()
        if ok:
            print(colorize(f"  [+] {msg}", UIColors.MINT))
            print(colorize("      Системный прокси Windows переключен на 127.0.0.1:18080.", UIColors.LIGHT_GRAY))
        else:
            print(colorize(f"  [-] {msg}", UIColors.RED))
    time.sleep(1.5)

def handle_windows_service():
    if not is_admin():
        print(colorize("\n  [!] Для управления службой Windows необходимы права Администратора.", UIColors.YELLOW))
        choice = input("  Перезапустить с правами Администратора? (y/n, Enter=y): ").strip().lower()
        if choice in ('', 'y', 'yes', 'д', 'да'):
            request_admin_elevation()
            return
    print(colorize("\n  [*] Запуск менеджера службы Windows...", UIColors.CYAN))
    booster.install_windows_service()
    time.sleep(1.5)

def handle_flush_dns():
    print(colorize("\n  [*] Очистка кэша сопоставителя DNS...", UIColors.CYAN))
    ok, msg = network_utils.flush_dns()
    if ok:
        print(colorize(f"  [+] {msg}", UIColors.MINT))
    else:
        print(colorize(f"  [-] {msg}", UIColors.RED))

    if is_admin():
        print(colorize("  [*] Установка быстрых DNS серверов (Cloudflare 1.1.1.1, Google 8.8.8.8)...", UIColors.CYAN))
        ok2, msg2 = network_utils.set_fast_dns("1.1.1.1", "8.8.8.8")
        if ok2:
            print(colorize(f"  [+] {msg2}", UIColors.MINT))
        else:
            print(colorize(f"  [!] {msg2}", UIColors.YELLOW))
    else:
        print(colorize("  [i] Для автоматической установки DNS запустите программу от Администратора [U].", UIColors.GRAY))

    time.sleep(1.8)

def main():
    while True:
        try:
            draw_header()
            print_menu()
            
            choice = input("  Выберите действие: ").strip().upper()
            
            if choice == "1":
                handle_start_booster()
            elif choice == "2":
                handle_stop_booster()
            elif choice == "3":
                handle_launch_discord_app()
            elif choice == "4":
                handle_launch_discord_web()
            elif choice == "5":
                handle_choose_strategy()
            elif choice == "6":
                handle_deep_configuration()
            elif choice == "7":
                handle_python_proxy()
            elif choice == "8":
                handle_diagnostics()
            elif choice == "9":
                handle_flush_dns()
            elif choice in ("S", "Ы"):
                handle_windows_service()
            elif choice in ("U", "Г"):
                if is_admin():
                    print(colorize("\n  [+] Программа уже запущена с правами Администратора.", UIColors.MINT))
                    time.sleep(1.2)
                else:
                    request_admin_elevation()
            elif choice in ("0", "Q", "EXIT", "QUIT"):
                handle_stop_booster()
                print(colorize("\n  Завершение работы FreeDiscord. До свидания!\n", UIColors.CYAN))
                time.sleep(0.5)
                sys.exit(0)
            else:
                print(colorize("\n  [!] Неизвестная команда. Повторите ввод.", UIColors.RED))
                time.sleep(0.8)
        except (KeyboardInterrupt, SystemExit):
            handle_stop_booster()
            sys.exit(0)
        except Exception as e:
            print(colorize(f"\n  [!] Ошибка: {e}", UIColors.RED))
            time.sleep(2.0)

if __name__ == "__main__":
    main()
