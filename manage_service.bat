@echo off
echo Управление службой News Collector Service
echo.
echo 1. Запустить службу
echo 2. Остановить службу
echo 3. Перезапустить службу
echo 4. Показать статус
echo 5. Удалить службу
echo.
set /p choice="Выберите действие: "

if "%choice%"=="1" (
    nssm start NewsCollectorService
) else if "%choice%"=="2" (
    nssm stop NewsCollectorService
) else if "%choice%"=="3" (
    nssm restart NewsCollectorService
) else if "%choice%"=="4" (
    nssm status NewsCollectorService
) else if "%choice%"=="5" (
    nssm remove NewsCollectorService confirm
) else (
    echo Неверный выбор
)

pause