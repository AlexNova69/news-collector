@echo off
echo Установка службы News Collector Service...

:: Проверяем, запущен ли скрипт от администратора
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Ошибка: Скрипт должен быть запущен от имени администратора
    pause
    exit /b 1
)

:: Устанавливаем службу с помощью NSSM
nssm install NewsCollectorService "%CD%\venv\Scripts\python.exe" "%CD%\news_collector_service.py"

:: Настраиваем службу
nssm set NewsCollectorService DisplayName "News Collector Service"
nssm set NewsCollectorService Description "Служба автоматического сбора и обработки новостей"
nssm set NewsCollectorService Start SERVICE_AUTO_START
nssm set NewsCollectorService AppDirectory "%CD%"
nssm set NewsCollectorService AppStdout "%CD%\logs\service.log"
nssm set NewsCollectorService AppStderr "%CD%\logs\service_error.log"

echo Служба установлена. Запуск службы...
nssm start NewsCollectorService

echo.
echo Служба успешно установлена и запущена!
echo Управление службой:
echo   - Остановка: nssm stop NewsCollectorService
echo   - Запуск: nssm start NewsCollectorService
echo   - Удаление: nssm remove NewsCollectorService confirm
echo.
pause