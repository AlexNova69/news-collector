import requests
import json
import schedule
import time
import threading
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import sys

class NewsCollector:
    def __init__(self, config_file="sources.json"):
        self.config_file = config_file
        self.sources = self.load_sources()
        
    def load_sources(self):
        """Загрузка конфигурации источников из JSON файла"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # Создаем базовую структуру если файла нет
            return {"sources": {}}
    
    def save_sources(self):
        """Сохранение конфигурации источников в JSON файл"""
        # Создаем директорию если не существует
        os.makedirs(os.path.dirname(self.config_file) if os.path.dirname(self.config_file) else '.', exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.sources, f, ensure_ascii=False, indent=2)
    
    def add_source(self, name, url, max_news=5, selector="auto"):
        """Добавление нового источника новостей"""
        self.sources["sources"][name] = {
            "url": url,
            "max_news": max_news,
            "selector": selector
        }
        self.save_sources()
        print(f"✅ Источник '{name}' добавлен успешно!")
    
    def remove_source(self, name):
        """Удаление источника новостей"""
        if name in self.sources["sources"]:
            del self.sources["sources"][name]
            self.save_sources()
            print(f"✅ Источник '{name}' удален успешно!")
        else:
            print(f"❌ Источник '{name}' не найден!")
    
    def list_sources(self):
        """Вывод списка всех источников"""
        if not self.sources["sources"]:
            print("📭 Нет добавленных источников")
            return
        
        print("\n📋 Список источников:")
        for name, config in self.sources["sources"].items():
            print(f"  📰 {name}: {config['url']} (макс. новостей: {config['max_news']})")
    
    def fetch_news_from_source(self, source_name, config):
        """Сбор новостей с одного источника"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            print(f"🔍 Загрузка страницы: {config['url']}")
            response = requests.get(config["url"], headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            news_items = []
            
            # Универсальные селекторы для поиска новостей
            selectors = [
                'article',
                '.news-item',
                '.post',
                '.story',
                '.news',
                '.article',
                '[class*="news"]',
                '[class*="article"]',
                'h1', 'h2', 'h3'
            ]
            
            for selector in selectors:
                items = soup.select(selector)
                for item in items[:config["max_news"] * 2]:  # Берем больше для фильтрации
                    title = self.extract_title(item)
                    if title and len(title) > 15 and len(title) < 500:  # Фильтр коротких и длинных текстов
                        link = self.extract_link(item, config["url"])
                        content = self.extract_content(item)
                        
                        news_item = {
                            'title': title.strip(),
                            'link': link,
                            'source': source_name,
                            'content': content[:200] + '...' if len(content) > 200 else content,
                            'date': datetime.now().strftime("%Y-%m-%d")
                        }
                        
                        # Проверяем дубликаты
                        if not any(item['title'] == news_item['title'] for item in news_items):
                            news_items.append(news_item)
                    
                    if len(news_items) >= config["max_news"]:
                        break
                
                if len(news_items) >= config["max_news"]:
                    break
            
            return news_items[:config["max_news"]]
            
        except requests.RequestException as e:
            print(f"❌ Ошибка сети при сборе с {source_name}: {e}")
            return []
        except Exception as e:
            print(f"❌ Ошибка при сборе новостей с {source_name}: {e}")
            return []
    
    def extract_title(self, element):
        """Извлечение заголовка из элемента"""
        # Пытаемся найти текст в различных тегах
        if element.name in ['h1', 'h2', 'h3', 'h4']:
            text = element.get_text().strip()
            return text if text and len(text) > 10 else None
        
        # Ищем заголовок внутри элемента
        for tag in ['h1', 'h2', 'h3', 'h4', 'a']:
            title_elem = element.find(tag)
            if title_elem and title_elem.get_text().strip():
                text = title_elem.get_text().strip()
                return text if len(text) > 10 else None
        
        text = element.get_text().strip()
        return text if len(text) > 10 else None
    
    def extract_link(self, element, base_url):
        """Извлечение ссылки из элемента"""
        link_elem = element.find('a')
        if link_elem and link_elem.get('href'):
            href = link_elem.get('href')
            if href.startswith('http'):
                return href
            else:
                return urljoin(base_url, href)
        return base_url
    
    def extract_content(self, element):
        """Извлечение контента новости"""
        # Ищем параграфы с текстом
        paragraphs = element.find_all('p')
        content = ' '.join([p.get_text().strip() for p in paragraphs[:3] if p.get_text().strip()])
        return content if content else element.get_text().strip()[:200]
    
    def collect_news(self):
        """Сбор новостей со всех источников"""
        all_news = []
        today = datetime.now().strftime("%Y-%m-%d")
        
        print(f"\n🚀 Начало сбора новостей за {today}...")
        
        for source_name, config in self.sources["sources"].items():
            print(f"\n📡 Сбор с {source_name}...")
            news = self.fetch_news_from_source(source_name, config)
            all_news.extend(news)
            print(f"✅ Найдено {len(news)} новостей")
        
        print(f"\n📊 Всего собрано новостей: {len(all_news)}")
        return all_news

class AISummarizer:
    """AI-агент для сжатия и обработки текста"""
    
    @staticmethod
    def summarize_news(news_items):
        """Сжатие и обработка новостей"""
        summarized_news = []
        
        print("🤖 Обработка новостей AI-агентом...")
        
        for news in news_items:
            try:
                original_title = news['title']
                original_content = news.get('content', '')
                
                # Создаем сжатое изложение
                compressed_title = AISummarizer.compress_text(original_title)
                compressed_content = AISummarizer.summarize_content(original_content)
                
                summarized_news.append({
                    'source': news['source'],
                    'original_title': original_title,
                    'title': compressed_title,
                    'content': compressed_content,
                    'link': news['link'],
                    'processed_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'date': news['date']
                })
                
            except Exception as e:
                print(f"❌ Ошибка при обработке новости: {e}")
                # В случае ошибки используем оригинальный текст
                summarized_news.append({
                    'source': news['source'],
                    'original_title': news['title'],
                    'title': news['title'][:100] + '...' if len(news['title']) > 100 else news['title'],
                    'content': news.get('content', '')[:150] + '...',
                    'link': news['link'],
                    'processed_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'date': news['date']
                })
        
        return summarized_news
    
    @staticmethod
    def compress_text(text):
        """Сжатие текста путем удаления стоп-слов и лишней информации"""
        if len(text) <= 80:
            return text
            
        # Список стоп-слов для русского и английского языков
        stop_words = {
            'что', 'как', 'это', 'вот', 'для', 'после', 'перед', 'из', 'на', 'о', 'по', 'за', 'от', 'до', 'при',
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'
        }
        
        words = text.split()
        filtered_words = [word for word in words if word.lower() not in stop_words]
        
        # Ограничиваем длину
        compressed = ' '.join(filtered_words)
        if len(compressed) > 80:
            compressed = compressed[:77] + '...'
        
        return compressed
    
    @staticmethod
    def summarize_content(content):
        """Создание краткого изложения контента"""
        if not content or len(content) < 50:
            return content
            
        # Упрощенный алгоритм суммаризации - берем первые предложения
        sentences = content.split('.')
        summary = '. '.join(sentences[:2]) + '.' if len(sentences) > 1 else content
        
        if len(summary) > 150:
            summary = summary[:147] + '...'
            
        return summary

class NewsExporter:
    """Экспорт новостей в файл"""
    
    @staticmethod
    def export_to_txt(news_items, filename=None):
        """Экспорт новостей в текстовый файл"""
        if not news_items:
            print("❌ Нет новостей для экспорта!")
            return None
            
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"news_export_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"📰 Экспорт новостей от {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                
                current_source = None
                for i, news in enumerate(news_items, 1):
                    if news['source'] != current_source:
                        current_source = news['source']
                        f.write(f"\n🔹 ИСТОЧНИК: {current_source}\n")
                        f.write("-" * 40 + "\n")
                    
                    f.write(f"{i}. {news['title']}\n")
                    if news.get('content'):
                        f.write(f"   📝 {news['content']}\n")
                    f.write(f"   🔗 Ссылка: {news['link']}\n")
                    f.write(f"   ⏰ Обработано: {news['processed_at']}\n")
                    f.write("\n")
            
            print(f"✅ Новости экспортированы в файл: {filename}")
            return filename
        except Exception as e:
            print(f"❌ Ошибка при экспорте в файл: {e}")
            return None

class NewsApp:
    """Главный класс приложения"""
    
    def __init__(self):
        self.collector = NewsCollector()
        self.summarizer = AISummarizer()
        self.exporter = NewsExporter()
        self.scheduler_running = False
        self.scheduler_thread = None
    
    def add_source_interface(self):
        """Интерфейс добавления источника"""
        print("\n--- Добавление нового источника ---")
        name = input("Введите название источника: ").strip()
        if not name:
            print("❌ Название не может быть пустым!")
            return
            
        url = input("Введите URL источника: ").strip()
        if not url.startswith('http'):
            print("❌ URL должен начинаться с http:// или https://")
            return
        
        try:
            max_news = int(input("Введите максимальное количество новостей (по умолчанию 5): ") or "5")
        except ValueError:
            max_news = 5
        
        self.collector.add_source(name, url, max_news)
    
    def remove_source_interface(self):
        """Интерфейс удаления источника"""
        print("\n--- Удаление источника ---")
        self.collector.list_sources()
        name = input("Введите название источника для удаления: ").strip()
        if name:
            self.collector.remove_source(name)
    
    def collect_and_export(self):
        """Сбор и экспорт новостей"""
        news = self.collector.collect_news()
        
        if not news:
            print("❌ Новости не найдены или произошла ошибка при сборе!")
            return
        
        processed_news = self.summarizer.summarize_news(news)
        
        filename = input("Введите имя файла для экспорта (или Enter для автоматического): ").strip()
        if not filename:
            filename = None
        
        result_file = self.exporter.export_to_txt(processed_news, filename)
        if result_file:
            print(f"📁 Файл сохранен: {os.path.abspath(result_file)}")
    
    def setup_schedule(self):
        """Настройка автоматического сбора по расписанию"""
        print("\n--- Настройка расписания ---")
        print("1. Ежедневно в определенное время")
        print("2. Каждый час")
        print("3. Каждые 30 минут")
        print("4. Отменить расписание")
        
        choice = input("Выберите вариант: ").strip()
        
        schedule.clear()  # Очищаем предыдущее расписание
        
        if choice == "1":
            time_str = input("Введите время (формат HH:MM): ").strip()
            schedule.every().day.at(time_str).do(self.scheduled_task)
            print(f"✅ Расписание установлено на ежедневное выполнение в {time_str}")
        elif choice == "2":
            schedule.every().hour.do(self.scheduled_task)
            print("✅ Расписание установлено на выполнение каждый час")
        elif choice == "3":
            schedule.every(30).minutes.do(self.scheduled_task)
            print("✅ Расписание установлено на выполнение каждые 30 минут")
        elif choice == "4":
            print("✅ Расписание отменено")
        else:
            print("❌ Неверный выбор!")
    
    def scheduled_task(self):
        """Задача для выполнения по расписанию"""
        print(f"\n⏰ [Расписание] Автоматический сбор новостей в {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        try:
            news = self.collector.collect_news()
            if news:
                processed_news = self.summarizer.summarize_news(news)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"scheduled_news_{timestamp}.txt"
                self.exporter.export_to_txt(processed_news, filename)
            else:
                print("ℹ️  Новости не найдены в запланированном сборе")
        except Exception as e:
            print(f"❌ Ошибка в запланированной задаче: {e}")
    
    def run_scheduler(self):
        """Запуск планировщика в отдельном потоке"""
        print("🔄 Планировщик запущен...")
        self.scheduler_running = True
        while self.scheduler_running:
            schedule.run_pending()
            time.sleep(1)
    
    def start_scheduler(self):
        """Запуск фонового планировщика"""
        if not self.scheduler_running:
            self.scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
            self.scheduler_thread.start()
            print("✅ Планировщик запущен в фоновом режиме")
            print("ℹ️  Для остановки выберите пункт 'Остановить планировщик'")
        else:
            print("ℹ️  Планировщик уже запущен")
    
    def stop_scheduler(self):
        """Остановка планировщика"""
        self.scheduler_running = False
        schedule.clear()
        print("✅ Планировщик остановлен")
    
    def quick_start(self):
        """Быстрый старт с примером источников"""
        print("\n🚀 Быстрый старт...")
        # Добавляем несколько примеров источников
        example_sources = {
            "Lenta.ru": "https://lenta.ru",
            "РИА Новости": "https://ria.ru",
            "ТАСС": "https://tass.ru"
        }
        
        for name, url in example_sources.items():
            if name not in self.collector.sources["sources"]:
                self.collector.add_source(name, url, 3)
        
        print("✅ Примеры источников добавлены!")
        self.collector.list_sources()
    
    def main_menu(self):
        """Главное меню приложения"""
        while True:
            print("\n" + "="*60)
            print("           🚀 СИСТЕМА АВТОМАТИЧЕСКОГО СБОРА НОВОСТЕЙ")
            print("="*60)
            print("1. 📋 Показать источники")
            print("2. ➕ Добавить источник")
            print("3. ❌ Удалить источник")
            print("4. 📡 Собрать и экспортировать новости")
            print("5. ⚙️  Настроить автоматический сбор")
            print("6. 🔄 Запустить фоновый планировщик")
            print("7. ⏹️  Остановить планировщик")
            print("8. 🚀 Быстрый старт (добавить примеры источников)")
            print("0. 🚪 Выход")
            print("-"*60)
            
            choice = input("Выберите действие: ").strip()
            
            if choice == "1":
                self.collector.list_sources()
            elif choice == "2":
                self.add_source_interface()
            elif choice == "3":
                self.remove_source_interface()
            elif choice == "4":
                self.collect_and_export()
            elif choice == "5":
                self.setup_schedule()
            elif choice == "6":
                self.start_scheduler()
            elif choice == "7":
                self.stop_scheduler()
            elif choice == "8":
                self.quick_start()
            elif choice == "0":
                self.stop_scheduler()
                print("\n👋 До свидания!")
                break
            else:
                print("❌ Неверный выбор! Попробуйте снова.")

def main():
    """Основная функция запуска приложения"""
    print("Загрузка приложения...")
    app = NewsApp()
    
    # Проверяем наличие источников, если нет - предлагаем быстрый старт
    if not app.collector.sources["sources"]:
        print("\nℹ️  Источники новостей не настроены.")
        quick_start = input("Хотите выполнить быстрый старт с примерами источников? (y/n): ").strip().lower()
        if quick_start in ['y', 'yes', 'д', 'да']:
            app.quick_start()
    
    app.main_menu()

if __name__ == "__main__":
    main()