@echo off
chcp 65001 > nul
title FreeDiscord Launcher

:: Проверка прав администратора
net session >nul 2>&1
if %errorLevel% == 0 (
    goto :run_app
) else (
    echo [i] Запрос прав Администратора для перехвата пакетов и работы Discord...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

:run_app
cd /d "%~dp0"
python src/installer.py
python src/main.py
if %errorLevel% neq 0 (
    echo.
    echo [!] Произошла ошибка при выполнении. Нажмите любую клавишу для выхода...
    pause > nul
)
