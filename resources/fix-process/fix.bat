@echo off
:: Проверка, запущен ли скрипт с правами администратора
net session >nul 2>&1
if %errorlevel% neq 0 (
    :: Перезапуск скрипта с правами администратора
    powershell -Command "Start-Process '%~f0' -Verb runAs"
    exit
)

:: Закрытие процесса winws.exe
taskkill /f /im winws.exe

:: Остановка службы WinDivert
net stop WinDivert

:: Завершение работы
exit
