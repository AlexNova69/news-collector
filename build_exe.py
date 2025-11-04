#!/usr/bin/env python3
"""
Скрипт для сборки News Collector в самодостаточный EXE файл
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_pyinstaller():
    """Проверка наличия PyInstaller"""
    try:
        import PyInstaller
        print("✅ PyInstaller установлен")
        return True
    except ImportError:
        print("❌ PyInstaller не установлен")
        return False

def install_dependencies():
    """Установка необходимых зависимостей"""
    print("📦 Установка зависимостей...")
    
    dependencies = [
        "requests==2.31.0",
        "beautifulsoup4==4.12.2", 
        "schedule==1.2.0",
        "lxml==4.9.3"
    ]
    
    for dep in dependencies:
        print(f"Установка {dep}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
        except subprocess.CalledProcessError:
            print(f"❌ Ошибка установки {dep}")
            return False
    
    return True

def ensure_config_files():
    """Создание необходимых конфигурационных файлов если их нет"""
    print("📁 Проверка конфигурационных файлов...")
    
    # Создаем filters.json если его нет
    if not os.path.exists("filters.json"):
        filters_content = {
            "global_filters": {
                "stop_words": [
                    "читать дальше", "подробнее", "комментарии", "фото", "видео",
                    "источник", "новости", "главное", "смотрите также", "реклама",
                    "афиша", "расписание", "лента добра", "хочешь видеть",
                    "вернуться в обычную", "все новости", "читать полностью",
                    "подробности", "ИИ-ассистент", "МегаФон", "Мега Фон"
                ],
                "stop_symbols": ["➡", "⭐", "🔥", "❗", "❌", "✅"],
                "regex_patterns": [
                    "^\\d{1,2}:\\d{2}\\s*$", "^\\d{3,4}\\s*$", "^\\d{1,2}\\.\\d{2}\\.\\s*$",
                    "^\\d{1,2}\\s*(час|ч|минут|мин|\\.)", "Сегодня,\\s*\\d{1,2}:\\d{2}",
                    "Вчера,\\s*\\d{1,2}:\\d{2}", "\\d{1,2}\\s+января,\\s*\\d{1,2}:\\d{2}",
                    "\\d{1,2}\\s+февраля,\\s*\\d{1,2}:\\d{2}", "\\d{1,2}\\s+марта,\\s*\\d{1,2}:\\d{2}",
                    "\\d{1,2}\\s+апреля,\\s*\\d{1,2}:\\d{2}", "\\d{1,2}\\s+мая,\\s*\\d{1,2}:\\d{2}",
                    "\\d{1,2}\\s+июня,\\s*\\d{1,2}:\\d{2}", "\\d{1,2}\\s+июля,\\s*\\d{1,2}:\\d{2}",
                    "\\d{1,2}\\s+августа,\\s*\\d{1,2}:\\d{2}", "\\d{1,2}\\s+сентября,\\s*\\d{1,2}:\\d{2}",
                    "\\d{1,2}\\s+октября,\\s*\\d{1,2}:\\d{2}", "\\d{1,2}\\s+ноября,\\s*\\d{1,2}:\\d{2}",
                    "\\d{1,2}\\s+декабря,\\s*\\d{1,2}:\\d{2}", "^\\d{2}/\\d{2}", "^\\d{1,2}/\\d{1,2}",
                    "^\\d{2}\\.\\d{2}", "^\\d{1,2}\\.\\d{1,2}", "\\s*\\d{1,2}:\\d{2}\\s*$", "\\s+\\d{1,2}:\\d{2}$"
                ]
            },
            "source_specific_filters": {
                "47news.ru": {
                    "stop_words": ["47news", "новости Ленобласти"],
                    "stop_symbols": [],
                    "regex_patterns": ["\\s*\\d{1,2}:\\d{2}\\s*$", "\\s+\\d{1,2}:\\d{2}$"]
                },
                "47news": {
                    "stop_words": ["47news", "новости Ленобласти"],
                    "stop_symbols": [],
                    "regex_patterns": ["\\s*\\d{1,2}:\\d{2}\\s*$", "\\s+\\d{1,2}:\\d{2}$"]
                },
                "Фонтанка": {
                    "stop_words": ["Фонтанка", "Санкт-Петербург"],
                    "stop_symbols": [],
                    "regex_patterns": ["^\\d{2}/\\d{2}", "^\\d{1,2}/\\d{1,2}"]
                },
                "fontanka": {
                    "stop_words": ["Фонтанка", "Санкт-Петербург"],
                    "stop_symbols": [],
                    "regex_patterns": ["^\\d{2}/\\d{2}", "^\\d{1,2}/\\d{1,2}"]
                }
            }
        }
        
        with open("filters.json", "w", encoding="utf-8") as f:
            json.dump(filters_content, f, ensure_ascii=False, indent=2)
        print("✅ Создан filters.json")
    
    # Создаем sources.json если его нет
    if not os.path.exists("sources.json"):
        sources_content = {
            "sources": {
                "47news.ru": {"url": "https://47news.ru", "max_news": 5},
                "47news": {"url": "https://47news.ru", "max_news": 5},
                "Фонтанка": {"url": "https://www.fontanka.ru", "max_news": 5},
                "fontanka": {"url": "https://www.fontanka.ru", "max_news": 5}
            }
        }
        
        with open("sources.json", "w", encoding="utf-8") as f:
            json.dump(sources_content, f, ensure_ascii=False, indent=2)
        print("✅ Создан sources.json")

def create_spec_file():
    """Создание spec файла для PyInstaller"""
    print("📄 Создание spec файла...")
    
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['news_collector.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('filters.json', '.'),
        ('sources.json', '.')
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='news_collector',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codepage='utf8',
)
'''
    
    with open('news_collector.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("✅ Создан news_collector.spec")

def build_exe():
    """Сборка EXE файла"""
    print("🔨 Сборка EXE файла...")
    
    try:
        # Используем spec файл для сборки
        result = subprocess.run([
            'pyinstaller', 
            'news_collector.spec',
            '--clean',
            '--noconfirm'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ EXE файл успешно собран!")
            
            # Создаем папку для дистрибутива
            dist_dir = 'NewsCollectorDist'
            if os.path.exists(dist_dir):
                shutil.rmtree(dist_dir)
            os.makedirs(dist_dir)
            
            # Копируем EXE файл
            exe_src = os.path.join('dist', 'news_collector.exe')
            exe_dst = os.path.join(dist_dir, 'news_collector.exe')
            
            if os.path.exists(exe_src):
                shutil.copy2(exe_src, exe_dst)
                
                # Копируем конфигурационные файлы в дистрибутив
                for config_file in ['filters.json', 'sources.json']:
                    if os.path.exists(config_file):
                        shutil.copy2(config_file, os.path.join(dist_dir, config_file))
                
                print(f"📁 Дистрибутив создан в папке: {dist_dir}")
                print("🚀 Запустите news_collector.exe для использования приложения")
                
                # Статистика
                exe_size = os.path.getsize(exe_dst) / (1024 * 1024)  # MB
                print(f"📊 Размер EXE файла: {exe_size:.2f} MB")
                
                print("\n📋 В дистрибутив включены:")
                print("   ✅ news_collector.exe - основное приложение")
                print("   ✅ filters.json - файл фильтров")
                print("   ✅ sources.json - файл источников")
                
                return True
            else:
                print("❌ EXE файл не найден после сборки!")
                return False
        else:
            print(f"❌ Ошибка при сборке: {result.stderr}")
            return False
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при сборке: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

def cleanup():
    """Очистка временных файлов"""
    print("🧹 Очистка временных файлов...")
    
    folders_to_remove = ['build', '__pycache__']
    files_to_remove = ['news_collector.spec']
    
    for folder in folders_to_remove:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"✅ Удалена папка: {folder}")
    
    for file in files_to_remove:
        if os.path.exists(file):
            os.remove(file)
            print(f"✅ Удален файл: {file}")

def main():
    """Основная функция"""
    print("🎯 News Collector - Сборка самодостаточного EXE файла")
    print("=" * 60)
    print("💡 Создается один EXE файл, не требующий установки Python!")
    print("🛠️  Включает систему внешних фильтров filters.json")
    print("=" * 60)
    
    # Проверяем наличие основного файла
    if not os.path.exists("news_collector.py"):
        print("❌ Файл news_collector.py не найден!")
        return
    
    # Создаем необходимые конфигурационные файлы
    ensure_config_files()
    
    # Проверяем PyInstaller
    if not check_pyinstaller():
        print("❌ Требуется установка PyInstaller")
        install = input("Установить зависимости автоматически? (y/n): ").strip().lower()
        if install in ['y', 'yes', 'д', 'да']:
            if not install_dependencies():
                print("❌ Не удалось установить зависимости")
                return
        else:
            print("❌ Сборка невозможна без PyInstaller")
            return
    
    # Создаем spec файл
    create_spec_file()
    
    # Собираем EXE
    if build_exe():
        print("\n🎉 Сборка завершена успешно!")
        print("\n📋 Важная информация:")
        print("✅ EXE файл полностью самодостаточен")
        print("✅ Не требует установки Python")
        print("✅ Не требует дополнительных библиотек")
        print("✅ Все файлы создаются рядом с EXE")
        print("✅ Кодировка UTF-8 для русского языка")
        print("✅ Включена система фильтров filters.json")
        
        # Очистка
        cleanup_choice = input("\nОчистить временные файлы сборки? (y/n): ").strip().lower()
        if cleanup_choice in ['y', 'yes', 'д', 'да']:
            cleanup()
    else:
        print("\n❌ Сборка не удалась!")

if __name__ == "__main__":
    main()
