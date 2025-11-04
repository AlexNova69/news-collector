@echo off
chcp 65001 >nul
echo ========================================
echo    Установка News Collector
echo ========================================
echo.

echo Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не установлен
    pause
    exit /b 1
)

echo Установка зависимостей...
pip install requests beautifulsoup4 schedule lxml

echo.
echo ========================================
echo    ✅ Установка завершена!
echo ========================================
echo.
echo Для запуска: python news_collector.py
echo или дважды щелкните run_news_collector.bat
echo.
pause