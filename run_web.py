#!/usr/bin/env python3
"""
Простой запуск Web UI для News Collector
"""

import os
import sys

def main():
    print("🎯 News Collector Web UI")
    print("=" * 50)
    
    # Проверяем наличие основного файла
    if not os.path.exists("news_collector.py"):
        print("❌ Файл news_collector.py не найден!")
        print("💡 Убедитесь, что вы запускаете скрипт из правильной папки")
        return
    
    # Проверяем зависимости
    try:
        from flask import Flask
        print("✅ Flask установлен")
    except ImportError:
        print("❌ Flask не установлен!")
        print("📦 Устанавливаем зависимости...")
        os.system("pip install -r requirements.txt")
    
    # Запускаем Web UI
    print("🚀 Запускаем Web UI...")
    print("📧 Web интерфейс будет доступен по адресу: http://localhost:5000")
    print("⏰ Новые возможности:")
    print("   - Редактирование источников")
    print("   - Управление планировщиком")
    print("   - Автоматический сбор по расписанию")
    os.system("python web_ui.py")

if __name__ == "__main__":
    main()
