#!/usr/bin/env python3
"""
Диагностический скрипт для проверки окружения сборки
"""

import os
import sys
import subprocess

def check_environment():
    """Проверка окружения"""
    print("🔍 Диагностика окружения сборки...")
    print("=" * 50)
    
    # Проверяем Python
    print(f"🐍 Python версия: {sys.version}")
    
    # Проверяем текущую директорию
    print(f"📁 Текущая директория: {os.getcwd()}")
    
    # Проверяем необходимые файлы
    required_files = ['news_collector.py', 'filters.json', 'sources.json']
    for file in required_files:
        if os.path.exists(file):
            size = os.path.getsize(file)
            print(f"✅ {file}: найден ({size} байт)")
        else:
            print(f"❌ {file}: не найден")
    
    # Проверяем PyInstaller
    try:
        import PyInstaller
        print("✅ PyInstaller: установлен")
    except ImportError:
        print("❌ PyInstaller: не установлен")
    
    # Проверяем другие зависимости
    dependencies = ['requests', 'beautifulsoup4', 'schedule', 'lxml']
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"✅ {dep}: установлен")
        except ImportError:
            print(f"❌ {dep}: не установлен")
    
    print("=" * 50)

def test_build():
    """Тест сборки"""
    print("\n🧪 Тест сборки...")
    
    # Простой тестовый скрипт
    test_script = """
import os
print("✅ Тестовый скрипт выполнен успешно!")
print(f"📁 Рабочая директория: {os.getcwd()}")
"""
    
    with open('test_build.py', 'w', encoding='utf-8') as f:
        f.write(test_script)
    
    try:
        # Пробуем собрать тестовый скрипт
        result = subprocess.run([
            'pyinstaller', 
            '--onefile',
            '--name', 'test_app',
            'test_build.py'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Тестовая сборка успешна!")
            
            # Проверяем созданный EXE
            if os.path.exists('dist/test_app.exe'):
                print("✅ EXE файл создан")
                os.remove('dist/test_app.exe')
            else:
                print("❌ EXE файл не создан")
        else:
            print(f"❌ Ошибка тестовой сборки: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Ошибка при тестовой сборке: {e}")
    
    # Убираем временные файлы
    for temp_file in ['test_build.py', 'test_app.spec']:
        if os.path.exists(temp_file):
            os.remove(temp_file)
    
    for temp_dir in ['build', 'dist']:
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    check_environment()
    test_build()
    
    print("\n📋 Рекомендации:")
    print("1. Запустите: python debug_build.py")
    print("2. Если есть ошибки, установите недостающие зависимости:")
    print("   pip install requests beautifulsoup4 schedule lxml pyinstaller")
    print("3. Запустите сборку снова: python build_exe.py")