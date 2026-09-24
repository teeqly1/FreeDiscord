"""
PyUI - Console UI Engine for FreeDiscord
Профессиональный терминальный интерфейс:
- Нативная поддержка VT100 / TrueColor в Windows
- Модульная верстка (панели, вкладки, статусные карточки, таблицы)
- Полное отсутствие эмодзи (строгий презентабельный стиль)
- Цветовая палитра Discord Dark & Neon
"""

import os
import sys
import ctypes

# Инициализация консоли Windows в режим VT100 / Virtual Terminal Processing
def init_terminal():
    if os.name == 'nt':
        os.system('chcp 65001 > nul')
        try:
            kernel32 = ctypes.windll.kernel32
            hStdOut = kernel32.GetStdHandle(-11)
            mode = ctypes.c_ulong()
            kernel32.GetConsoleMode(hStdOut, ctypes.byref(mode))
            ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            kernel32.SetConsoleMode(hStdOut, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
        except Exception:
            pass
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stdin.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

init_terminal()

# Палитра цветов (RGB TrueColor)
class UIColors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"

    # Основные цвета интерфейса
    DISCORD_BLURPLE = "\033[38;2;88;101;242m"
    CYAN = "\033[38;2;0;210;255m"
    MINT = "\033[38;2;87;242;135m"
    RED = "\033[38;2;237;66;69m"
    YELLOW = "\033[38;2;254;231;92m"
    GRAY = "\033[38;2;120;125;135m"
    LIGHT_GRAY = "\033[38;2;200;205;215m"
    DARK_GRAY = "\033[38;2;60;65;75m"
    WHITE = "\033[38;2;255;255;255m"
    
    # Фоны
    BG_DARK = "\033[48;2;30;32;36m"
    BG_BLURPLE = "\033[48;2;88;101;242m"

def colorize(text: str, color: str) -> str:
    return f"{color}{text}{UIColors.RESET}"

def gradient_text(text: str, rgb_start=(88, 101, 242), rgb_end=(0, 210, 255)) -> str:
    """Плавный RGB-градиент по строке без артефактов 'm'"""
    lines = text.split("\n")
    out_lines = []
    for line in lines:
        if not line:
            out_lines.append("")
            continue
        line_len = len(line)
        if line_len == 1:
            out_lines.append(f"\033[38;2;{rgb_start[0]};{rgb_start[1]};{rgb_start[2]}m{line}{UIColors.RESET}")
            continue
        res = []
        for i, char in enumerate(line):
            t = i / (line_len - 1)
            r = int(rgb_start[0] + (rgb_end[0] - rgb_start[0]) * t)
            g = int(rgb_start[1] + (rgb_end[1] - rgb_start[1]) * t)
            b = int(rgb_start[2] + (rgb_end[2] - rgb_start[2]) * t)
            res.append(f"\033[38;2;{r};{g};{b}m{char}")
        res.append(UIColors.RESET)
        out_lines.append("".join(res))
    return "\n".join(out_lines)

def clear():
    """Очистка экрана без мигания"""
    if os.name == 'nt':
        os.system('cls')
    else:
        sys.stdout.write("\033[H\033[2J")
        sys.stdout.flush()

def set_title(title: str):
    """Установка заголовка окна консоли"""
    if os.name == 'nt':
        ctypes.windll.kernel32.SetConsoleTitleW(title)
    else:
        sys.stdout.write(f"\033]0;{title}\007")
        sys.stdout.flush()

# UI Компоненты

def render_badge(text: str, style: str = "INFO") -> str:
    """Рендерит текстовый индикатор (бейдж) без эмодзи"""
    if style == "SUCCESS":
        return f"{UIColors.MINT}[OK]{UIColors.RESET} {text}"
    elif style == "RUNNING":
        return f"{UIColors.MINT}[АКТИВЕН]{UIColors.RESET} {text}"
    elif style == "STOPPED":
        return f"{UIColors.RED}[ОСТАНОВЛЕН]{UIColors.RESET} {text}"
    elif style == "WARN":
        return f"{UIColors.YELLOW}[ВНИМАНИЕ]{UIColors.RESET} {text}"
    elif style == "DANGER":
        return f"{UIColors.RED}[ОШИБКА]{UIColors.RESET} {text}"
    elif style == "ADMIN":
        return f"{UIColors.MINT}[АДМИНИСТРАТОР]{UIColors.RESET}"
    elif style == "USER":
        return f"{UIColors.YELLOW}[ПОЛЬЗОВАТЕЛЬ]{UIColors.RESET}"
    else:
        return f"{UIColors.CYAN}[ИНФО]{UIColors.RESET} {text}"

def panel(title: str, lines: list[str], width: int = 76, color: str = UIColors.DISCORD_BLURPLE) -> str:
    """Отрисовывает аккуратную панель с рамкой и заголовком"""
    border_color = color
    reset = UIColors.RESET
    
    t_clean = f" {title} " if title else ""
    t_len = len(t_clean)
    top_bar = "─" * (width - 2 - t_len)
    
    res = [f"{border_color}┌──{UIColors.WHITE}{UIColors.BOLD}{t_clean}{border_color}{top_bar}┐{reset}"]
    for line in lines:
        # Учитываем видимую длину без escape-последовательностей для выравнивания
        import re
        visible_len = len(re.sub(r'\033\[[0-9;]*m', '', line))
        pad = " " * max(0, width - 4 - visible_len)
        res.append(f"{border_color}│  {reset}{line}{pad}{border_color}│{reset}")
    res.append(f"{border_color}└{'─' * (width - 2)}┘{reset}")
    return "\n".join(res)

def tabs(active_tab: int = 1) -> str:
    """Отрисовывает строку вкладок категорий"""
    tab_list = [
        "1. Управление",
        "2. Конфигурация",
        "3. Диагностика",
        "4. Сеть и Службы"
    ]
    parts = []
    for i, t in enumerate(tab_list, 1):
        if i == active_tab:
            parts.append(f"{UIColors.DISCORD_BLURPLE}{UIColors.BOLD}[ {t.upper()} ]{UIColors.RESET}")
        else:
            parts.append(f"{UIColors.GRAY}  {t}  {UIColors.RESET}")
    return "   ".join(parts)

def separator(width: int = 76, color: str = UIColors.DARK_GRAY) -> str:
    return f"{color}{'─' * width}{UIColors.RESET}"
