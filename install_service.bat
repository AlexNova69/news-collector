@echo off
rem ============================================================
rem  install_service.bat — установка NewsCollector как службы
rem  Windows с АВТОЗАПУСКОМ после перезагрузки компьютера.
rem  ЗАПУСКАТЬ ОТ ИМЕНИ АДМИНИСТРАТОРА (правый клик по файлу).
rem ============================================================
chcp 65001 >nul
cd /d "%~dp0"

net session >nul 2>&1
if errorlevel 1 (
    echo Требуются права администратора.
    echo Щёлкните этот файл правой кнопкой и выберите
    echo «Запуск от имени администратора».
    pause
    exit /b 1
)

news_collector.exe install --startup auto || goto :err
news_collector.exe start || goto :err

echo.
sc qc NewsCollector | findstr /C:"BINARY_PATH_NAME" /C:"START_TYPE" /C:"DISPLAY_NAME"
echo.
echo Служба NewsCollector установлена (автозапуск) и запущена.
echo Настройки: sources.json, журнал: news_collector.log
echo Управление: news_collector.exe stop ^| restart ^| remove
pause
exit /b 0

:err
echo ОШИБКА установки службы.
pause
exit /b 1
