@echo off
chcp 65001 >nul
echo ========================================
echo    Установка News Collector
echo ========================================
echo.

echo Проверка установки Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не установлен или не добавлен в PATH
    echo Установите Python с https://python.org
    pause
    exit /b 1
)

echo ✅ Python обнаружен
echo.

echo Установка зависимостей...
pip install -r requirements.txt

if errorlevel 1 (
    echo ❌ Ошибка при установке зависимостей
    pause
    exit /b 1
)

echo ✅ Зависимости установлены
echo.

echo Установка приложения...
python setup.py install

if errorlevel 1 (
    echo ❌ Ошибка при установке приложения
    pause
    exit /b 1
)

echo.
echo ========================================
echo    ✅ Установка завершена успешно!
echo ========================================
echo.
echo Запуск приложения: news-collector
echo.
pause