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
import re
from difflib import SequenceMatcher
import hashlib
import subprocess
import webbrowser

# Определяем, запущены ли мы как EXE
def is_frozen():
    return getattr(sys, 'frozen', False)

def get_base_path():
    """Возвращает правильный путь в зависимости от режима (EXE или скрипт)"""
    if is_frozen():
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def get_resource_path(relative_path):
    """Получает абсолютный путь к ресурсу, работает для dev и для PyInstaller"""
    try:
        # PyInstaller создает временную папку и хранит путь в _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = get_base_path()
    
    return os.path.join(base_path, relative_path)

class FilterManager:
    """Менеджер фильтров для очистки новостей"""
    
    def __init__(self, config_file=None):
        if config_file is None:
            self.config_file = os.path.join(get_base_path(), "filters.json")
        else:
            self.config_file = config_file
        self.filters = self.load_filters()
    
    def load_filters(self):
        """Загрузка фильтров из JSON файла"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"ℹ️ Файл фильтров {self.config_file} не найден, создан новый")
            default_filters = {
                "global_filters": {
                    "stop_words": [],
                    "stop_symbols": [],
                    "regex_patterns": []
                },
                "source_specific_filters": {}
            }
            self.save_filters(default_filters)
            return default_filters
        except Exception as e:
            print(f"❌ Ошибка загрузки фильтров: {e}")
            return {"global_filters": {}, "source_specific_filters": {}}
    
    def save_filters(self, filters=None):
        """Сохранение фильтров в JSON файл"""
        if filters is None:
            filters = self.filters
        try:
            os.makedirs(os.path.dirname(self.config_file) if os.path.dirname(self.config_file) else '.', exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(filters, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ Ошибка сохранения фильтров: {e}")
    
    def add_global_stop_word(self, word):
        """Добавление стоп-слова в глобальные фильтры"""
        if word not in self.filters["global_filters"]["stop_words"]:
            self.filters["global_filters"]["stop_words"].append(word)
            self.save_filters()
            print(f"✅ Стоп-слово '{word}' добавлено в глобальные фильтры")
    
    def add_source_stop_word(self, source_name, word):
        """Добавление стоп-слова для конкретного источника"""
        if source_name not in self.filters["source_specific_filters"]:
            self.filters["source_specific_filters"][source_name] = {
                "stop_words": [],
                "stop_symbols": [],
                "regex_patterns": []
            }
        
        if word not in self.filters["source_specific_filters"][source_name]["stop_words"]:
            self.filters["source_specific_filters"][source_name]["stop_words"].append(word)
            self.save_filters()
            print(f"✅ Стоп-слово '{word}' добавлено для источника '{source_name}'")
    
    def apply_filters(self, text, source_name=None):
        """Применение всех фильтров к тексту"""
        if not text:
            return text
        
        # Применяем глобальные фильтры
        filtered_text = self.apply_global_filters(text)
        
        # Применяем специфичные для источника фильтры
        if source_name:
            filtered_text = self.apply_source_filters(filtered_text, source_name)
        
        return filtered_text
    
    def apply_global_filters(self, text):
        """Применение глобальных фильтров"""
        # Стоп-слова
        for word in self.filters["global_filters"]["stop_words"]:
            text = re.sub(re.escape(word), '', text, flags=re.IGNORECASE)
        
        # Стоп-символы
        for symbol in self.filters["global_filters"]["stop_symbols"]:
            text = text.replace(symbol, '')
        
        # Регулярные выражения
        for pattern in self.filters["global_filters"]["regex_patterns"]:
            text = re.sub(pattern, '', text)
        
        return text.strip()
    
    def apply_source_filters(self, text, source_name):
        """Применение фильтров для конкретного источника"""
        if source_name not in self.filters["source_specific_filters"]:
            return text
        
        source_filters = self.filters["source_specific_filters"][source_name]
        
        # Стоп-слова
        for word in source_filters["stop_words"]:
            text = re.sub(re.escape(word), '', text, flags=re.IGNORECASE)
        
        # Стоп-символы
        for symbol in source_filters["stop_symbols"]:
            text = text.replace(symbol, '')
        
        # Регулярные выражения
        for pattern in source_filters["regex_patterns"]:
            text = re.sub(pattern, '', text)
        
        return text.strip()

class SimpleSummarizer:
    """Упрощенный AI-агент для пересказа новостей"""
    
    def summarize_text(self, text, max_length=200):
        """Пересказ текста новости"""
        if len(text) <= max_length:
            return text
        
        try:
            # Очищаем текст
            text = self.clean_text(text)
            
            # Разбиваем на предложения
            sentences = re.split(r'[.!?]+', text)
            sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 20]
            
            if not sentences:
                return text[:max_length-3] + '...'
            
            # Берем первое предложение (обычно содержит основную информацию)
            summary = sentences[0]
            
            # Если нужно, добавляем часть второго предложения
            if len(summary) < max_length * 0.7 and len(sentences) > 1:
                second_sentence = sentences[1]
                # Берем только начало второго предложения
                available_space = max_length - len(summary) - 2  # -2 для точки и пробела
                if available_space > 20:
                    second_part = second_sentence[:available_space-3] + '...' if len(second_sentence) > available_space else second_sentence
                    summary = summary + '. ' + second_part
            
            # Если все еще длиннее лимита, упрощаем
            if len(summary) > max_length:
                summary = self.simplify_sentence(summary, max_length)
            
            # Финальная проверка длины
            if len(summary) > max_length:
                summary = summary[:max_length-3] + '...'
            
            return summary
            
        except Exception as e:
            print(f"⚠️ Ошибка суммаризации: {e}")
            return text[:max_length-3] + '...'
    
    def clean_text(self, text):
        """Очистка текста"""
        # Удаляем временные метки
        text = re.sub(r'\d{1,2}\s*час[а]?[\s\d]*$', '', text)
        text = re.sub(r'\d{1,2}:\d{2}$', '', text)
        text = re.sub(r'[\s\d:-]+\s*$', '', text)
        
        # Удаляем категории
        text = re.sub(r'^(Чтиво|Происшествия|Образ жизни|Общество|Бизнес|На правах бизнеса|Афиша Plus|Доброе дело|Город|Лента добра|Афиша)\s*', '', text)
        
        return text.strip()
    
    def simplify_sentence(self, sentence, max_length):
        """Упрощение предложения"""
        words = sentence.split()
        
        if len(words) <= 6:
            return sentence[:max_length-3] + '...' if len(sentence) > max_length else sentence
        
        # Удаляем несущественные слова
        stop_words = {
            'который', 'которая', 'которое', 'которые', 'которым', 'которых',
            'очень', 'довольно', 'весьма', 'особенно', 'пожалуйста',
            'как правило', 'как обычно', 'в частности', 'например'
        }
        
        filtered_words = [word for word in words if word.lower() not in stop_words]
        
        # Если после фильтрации осталось достаточно слов
        if len(filtered_words) >= 5:
            simplified = ' '.join(filtered_words)
            if len(simplified) <= max_length:
                return simplified
        
        # Иначе берем первые слова
        return ' '.join(words[:8]) + '...'

class NewsCollector:
    def __init__(self, config_file=None):
        if config_file is None:
            self.config_file = os.path.join(get_base_path(), "sources.json")
        else:
            self.config_file = config_file
        self.sources = self.load_sources()
        self.summarizer = SimpleSummarizer()
        self.filter_manager = FilterManager()  # Добавляем менеджер фильтров
        
    def load_sources(self):
        """Загрузка конфигурации источников из JSON файла"""
        default_structure = {
            "sources": {},
            "settings": {
                "auto_save_directory": None  # Папка для автоматического сохранения
            }
        }
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            
            # Объединяем с дефолтной структурой для обратной совместимости
            if "settings" not in loaded_data:
                loaded_data["settings"] = default_structure["settings"]
            
            # Сохраняем обновленную структуру
            self.save_sources(loaded_data)
            
            return loaded_data
            
        except FileNotFoundError:
            print(f"ℹ️ Файл конфигурации {self.config_file} не найден, создан новый")
            self.save_sources(default_structure)
            return default_structure
        except Exception as e:
            print(f"❌ Ошибка загрузки конфигурации: {e}")
            return default_structure
    
    def save_sources(self, data=None):
        """Сохранение конфигурации источников в JSON файл"""
        if data is None:
            data = self.sources
            
        try:
            os.makedirs(os.path.dirname(self.config_file) if os.path.dirname(self.config_file) else '.', exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ Ошибка сохранения конфигурации: {e}")
    
    def set_auto_save_directory(self, directory):
        """Установка папки для автоматического сохранения"""
        if directory and os.path.exists(directory):
            self.sources["settings"]["auto_save_directory"] = directory
            self.save_sources()
            print(f"✅ Папка для автоматического сохранения установлена: {directory}")
            return True
        else:
            print("❌ Указанная папка не существует!")
            return False
    
    def get_auto_save_directory(self):
        """Получение папки для автоматического сохранения"""
        auto_dir = self.sources["settings"].get("auto_save_directory")
        if auto_dir and os.path.exists(auto_dir):
            return auto_dir
        return get_base_path()  # По умолчанию - папка программы
    
    def add_source(self, name, url, max_news=5):
        """Добавление нового источника новостей"""
        self.sources["sources"][name] = {
            "url": url,
            "max_news": max_news
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
    
    def edit_source(self, old_name, new_name, url, max_news):
        """Редактирование источника новостей"""
        if old_name in self.sources["sources"]:
            # Если имя изменилось, удаляем старый и создаем новый
            if old_name != new_name:
                del self.sources["sources"][old_name]
            
            self.sources["sources"][new_name] = {
                "url": url,
                "max_news": max_news
            }
            self.save_sources()
            print(f"✅ Источник '{old_name}' обновлен на '{new_name}'!")
            return True
        else:
            print(f"❌ Источник '{old_name}' не найден!")
            return False
    
    def list_sources(self):
        """Вывод списка всех источников"""
        if not self.sources["sources"]:
            print("📭 Нет добавленных источников")
            return
        
        print("\n📋 Список источников:")
        for i, (name, config) in enumerate(self.sources["sources"].items(), 1):
            print(f"  {i}. 📰 {name}: {config['url']} (макс. новостей: {config['max_news']})")
    
    def get_text_hash(self, text):
        """Создание хеша текста для проверки дубликатов"""
        normalized_text = self.normalize_text(text)
        return hashlib.md5(normalized_text.encode('utf-8')).hexdigest()
    
    def normalize_text(self, text):
        """Нормализация текста для лучшего сравнения дубликатов"""
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        stop_words = {'и', 'в', 'на', 'с', 'по', 'за', 'от', 'до', 'из', 'у', 'о', 'об', 'но', 'а', 'же'}
        words = [word for word in text.split() if word not in stop_words]
        return ' '.join(words).strip()
    
    def normalize_title(self, text):
        """Нормализация заголовка для лучшего сравнения"""
        if not text:
            return ""
        
        # Приводим к нижнему регистру
        text = text.lower()
        
        # Удаляем знаки препинания и лишние символы
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Удаляем лишние пробелы
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Удаляем стоп-слова которые не влияют на смысл
        stop_words = {
            'и', 'в', 'на', 'с', 'по', 'за', 'от', 'до', 'из', 'у', 'о', 
            'об', 'но', 'а', 'же', 'что', 'как', 'для', 'это', 'так'
        }
        words = [word for word in text.split() if word not in stop_words]
        
        return ' '.join(words)
    
    def is_similar_text(self, text1, text2, threshold=0.85):
        """Проверка схожести двух текстов"""
        normalized1 = self.normalize_text(text1)
        normalized2 = self.normalize_text(text2)
        return SequenceMatcher(None, normalized1, normalized2).ratio() > threshold
    
    def is_duplicate_news(self, new_text, existing_items, threshold=0.9):
        """Улучшенная проверка на дубликаты"""
        normalized_new = self.normalize_title(new_text)
        
        for existing in existing_items:
            normalized_existing = self.normalize_title(existing['text'])
            
            # Быстрая проверка по хешу
            if self.get_text_hash(normalized_new) == self.get_text_hash(normalized_existing):
                return True
            
            # Проверка по схожести
            if self.is_similar_text(normalized_new, normalized_existing, threshold):
                return True
            
            # Проверка на вхождение (одна новость является частью другой)
            if (normalized_new in normalized_existing or 
                normalized_existing in normalized_new) and len(normalized_new) > 30:
                return True
        
        return False
    
    def remove_duplicate_news(self, news_items):
        """Удаление дубликатов из финального списка"""
        unique_news = []
        used_hashes = set()
        
        for news in news_items:
            normalized = self.normalize_title(news['text'])
            text_hash = self.get_text_hash(normalized)
            
            if text_hash not in used_hashes:
                # Дополнительная проверка на частичные дубликаты
                is_duplicate = False
                for existing in unique_news:
                    if self.is_similar_text(news['text'], existing['text'], 0.9):
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    unique_news.append(news)
                    used_hashes.add(text_hash)
        
        return unique_news
    
    def clean_news_text(self, text, source_name=None):
        """Тщательная очистка текста новости с использованием фильтров"""
        if not text:
            return ""
        
        # Удаляем лишние пробелы
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # БАЗОВАЯ ОЧИСТКА (оставляем только самое необходимое)
        # Удаляем время в формате HH:MM в начале текста
        text = re.sub(r'^\d{1,2}:\d{2}\s*', '', text)
        text = re.sub(r'^\d{1,2}\s*:\s*\d{2}\s*', '', text)
        
        # Удаляем даты в формате MMDD в начале текста
        text = re.sub(r'^\d{3,4}', '', text)
        
        # Восстанавливаем пробелы
        text = re.sub(r'([а-яё])([А-ЯЁ])', r'\1 \2', text)
        text = re.sub(r'([.!?])([А-ЯЁ])', r'\1 \2', text)
        
        # Удаляем повторяющиеся точки и запятые
        text = re.sub(r'\.{2,}', '.', text)
        text = re.sub(r',{2,}', ',', text)
        
        # Финальная очистка пробелов
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # ПРИМЕНЯЕМ ФИЛЬТРЫ ИЗ ВНЕШНЕГО ФАЙЛА
        text = self.filter_manager.apply_filters(text, source_name)
        
        return text
    
    def extract_clean_news_text(self, element, source_name=None):
        """Извлечение и очистка текста новости из элемента"""
        try:
            # Удаляем ненужные элементы
            for unwanted in element.find_all(['script', 'style', 'time', 'small', 
                                            '.b-time', '.b-date', '.b-category',
                                            '.time', '.date', '.category',
                                            '.timestamp', '.news-date', '.date-time',
                                            '.news-time', '.item-time', '.p-time']):
                unwanted.decompose()
            
            # Пробуем разные стратегии извлечения текста
            text_candidates = []
            
            # 1. Текст из ссылок с атрибутами новостей
            links = element.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                text = link.get_text().strip()
                
                # ПРЕДВАРИТЕЛЬНАЯ ОЧИСТКА ОТ ВРЕМЕНИ
                text = re.sub(r'^\d{1,2}:\d{2}\s*', '', text)
                text = re.sub(r'^\d{3,4}', '', text)
                
                # Проверяем, что ссылка похожа на новостную
                if (self.is_valid_news(text) and 
                    any(keyword in href.lower() for keyword in ['news', 'article', 'novosti', 'novost', 'story'])):
                    text_candidates.append(text)
            
            # 2. Текст из заголовков
            for tag in ['h1', 'h2', 'h3', 'h4']:
                headers = element.find_all(tag)
                for header in headers:
                    text = header.get_text().strip()
                    
                    # ПРЕДВАРИТЕЛЬНАЯ ОЧИСТКА ОТ ВРЕМЕНИ
                    text = re.sub(r'^\d{1,2}:\d{2}\s*', '', text)
                    text = re.sub(r'^\d{3,4}', '', text)
                    
                    if self.is_valid_news(text):
                        text_candidates.append(text)
            
            # 3. Текст из элементов с новостными классами
            news_classes = element.find_all(class_=re.compile(r'news|article|title|header|story|item|content|text'))
            for elem in news_classes:
                text = elem.get_text().strip()
                
                # ПРЕДВАРИТЕЛЬНАЯ ОЧИСТКА ОТ ВРЕМЕНИ
                text = re.sub(r'^\d{1,2}:\d{2}\s*', '', text)
                text = re.sub(r'^\d{3,4}', '', text)
                
                if self.is_valid_news(text):
                    text_candidates.append(text)
            
            # 4. Текст всего элемента (только если короткий и валидный)
            full_text = element.get_text().strip()
            
            # ПРЕДВАРИТЕЛЬНАЯ ОЧИСТКА ОТ ВРЕМЕНИ
            full_text = re.sub(r'^\d{1,2}:\d{2}\s*', '', full_text)
            full_text = re.sub(r'^\d{3,4}', '', full_text)
            
            if self.is_valid_news(full_text) and len(full_text) < 400:
                text_candidates.append(full_text)
            
            # Выбираем лучший кандидат (самый длинный из валидных)
            if text_candidates:
                # Сначала сортируем по длине, потом убираем слишком похожие
                text_candidates.sort(key=len, reverse=True)
                unique_candidates = []
                used_hashes = set()
                
                for candidate in text_candidates:
                    # ДОПОЛНИТЕЛЬНАЯ ОЧИСТКА ОТ ДАТ И ВРЕМЕНИ
                    candidate = re.sub(r'^\d{1,2}:\d{2}\s*', '', candidate)
                    candidate = re.sub(r'^\d{3,4}', '', candidate)
                    
                    candidate_hash = self.get_text_hash(self.normalize_title(candidate))
                    if candidate_hash not in used_hashes:
                        unique_candidates.append(candidate)
                        used_hashes.add(candidate_hash)
                
                if unique_candidates:
                    return self.clean_news_text(unique_candidates[0], source_name)
                    
            return None
            
        except Exception as e:
            print(f"⚠️ Ошибка извлечения текста: {e}")
            return None
    
    def is_valid_news(self, text):
        """Проверка, является ли текст валидной новостью"""
        if not text or len(text) < 25 or len(text) > 500:
            return False
        
        # Исключаем технические тексты
        exclude_patterns = [
            r'читать\s+дальше', r'подробнее', r'комментарии', r'фото', r'видео',
            r'источник', r'новости', r'главное', r'смотрите также', r'реклама',
            r'афиша', r'расписание', r'лента\s+добра', r'хочешь\s+видеть',
            r'вернуться\s+в\s+обычную', r'все\s+новости', r'читать\s+полностью',
            r'подробности', r'ИИ-ассистент', r'МегаФон', r'Мега Фон',
            r'^\d{3,4}\s*$',  # Только даты без текста
            r'^\d{1,2}:\d{2}\s*$'  # Только время без текста
        ]
        
        text_lower = text.lower()
        for pattern in exclude_patterns:
            if re.search(pattern, text_lower):
                return False
        
        # Должны быть русские буквы
        if not re.search(r'[а-яё]', text_lower):
            return False
        
        # Исключаем тексты, состоящие в основном из цифр
        if len(re.findall(r'[а-яё]', text_lower)) < 10:
            return False
        
        # Исключаем тексты с временными метками в начале
        if re.match(r'^\d{1,2}\s*(час|ч|минут|мин|\.)', text_lower):
            return False
        
        # Исключаем тексты, которые начинаются только с дат
        if re.match(r'^\d{3,4}\s*[а-яё]', text_lower):
            # Это допустимо - дата и потом текст, мы очистим дату позже
            pass
        elif re.match(r'^\d{3,4}\s*$', text_lower):
            return False
            
        return True
    
    def process_news_text(self, text, source_name=None):
        """Обработка текста новости с помощью AI-агента"""
        # ПРЕДВАРИТЕЛЬНАЯ ОЧИСТКА ОТ ДАТ И ВРЕМЕНИ
        text = re.sub(r'^\d{1,2}:\d{2}\s*', '', text)
        text = re.sub(r'^\d{3,4}', '', text)
        cleaned_text = self.clean_news_text(text, source_name)
        summarized_text = self.summarizer.summarize_text(cleaned_text, 200)
        return summarized_text
    
    def fetch_news_from_source(self, source_name, config):
        """Улучшенный сбор новостей с одного источника"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            }
            
            print(f"🔍 Загрузка главной страницы: {config['url']}")
            response = requests.get(config["url"], headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            news_items = []
            used_hashes = set()
            
            # Более специфичные селекторы для разных источников
            news_selectors = [
                'a[href*="news"]', 'a[href*="article"]', 'a[href*="story"]',
                '.news-item', '.news__item', '.article', '.news-title',
                'h1', 'h2', 'h3', '.title', '[class*="news"]',
                '.b-news-item', '.item', '.b-article', '.b-link',
                '.story', '.news-list-item', '.news-block',
                '.content-item', '.item-content', '.news-content'
            ]
            
            all_elements = []
            for selector in news_selectors:
                elements = soup.select(selector)
                all_elements.extend(elements)
            
            # Убираем дубликаты элементов
            unique_elements = []
            element_hashes = set()
            
            for element in all_elements:
                element_html = str(element)
                element_hash = hashlib.md5(element_html.encode()).hexdigest()
                if element_hash not in element_hashes:
                    unique_elements.append(element)
                    element_hashes.add(element_hash)
            
            for element in unique_elements:
                if len(news_items) >= config["max_news"]:
                    break
                        
                news_text = self.extract_clean_news_text(element, source_name)
                if news_text:
                    # ДОПОЛНИТЕЛЬНАЯ ОЧИСТКА ОТ ДАТ И ВРЕМЕНИ ПЕРЕД ОБРАБОТКОЙ
                    news_text = re.sub(r'^\d{1,2}:\d{2}\s*', '', news_text)
                    news_text = re.sub(r'^\d{3,4}', '', news_text)
                    
                    # Обрабатываем AI-агентом
                    processed_text = self.process_news_text(news_text, source_name)
                    
                    if (processed_text and len(processed_text) >= 40 and 
                        len(processed_text) <= 200):
                        
                        # Проверяем на дубликаты
                        if not self.is_duplicate_news(processed_text, news_items, 0.9):
                            text_hash = self.get_text_hash(self.normalize_title(processed_text))
                            
                            if text_hash not in used_hashes:
                                news_items.append({
                                    'text': processed_text,
                                    'source': source_name,
                                    'length': len(processed_text),
                                    'hash': text_hash,
                                    'original_length': len(news_text)
                                })
                                used_hashes.add(text_hash)
                                print(f"   ✅ Обработано: {len(news_text)} → {len(processed_text)} симв.")
            
            return news_items
            
        except Exception as e:
            print(f"❌ Ошибка при сборе новостей с {source_name}: {e}")
            return []
    
    def collect_news(self):
        """Сбор новостей со всех источников"""
        all_news = []
        today = datetime.now().strftime("%Y-%m-%d")
        
        print(f"\n🚀 Начало сбора новостей за {today}...")
        print("🤖 Используется упрощенный AI для пересказа новостей")
        print("🔍 Усиленная борьба с дубликатами...")
        print("🗑️  Агрессивное удаление дат и временных меток...")
        print("🛠️  Применение фильтров из filters.json...")
        
        for source_name, config in self.sources["sources"].items():
            print(f"\n📡 Сбор с {source_name}...")
            news = self.fetch_news_from_source(source_name, config)
            
            # Добавляем с проверкой на меж-источниковые дубликаты
            for news_item in news:
                if not self.is_duplicate_news(news_item['text'], all_news, 0.9):
                    all_news.append(news_item)
            
            if news:
                print(f"✅ Обработано {len(news)} новостей")
            else:
                print("❌ Новости не найдены")
        
        # Финальная очистка от дубликатов
        all_news = self.remove_duplicate_news(all_news)
        
        print(f"\n📊 Всего собрано уникальных новостей: {len(all_news)}")
        return all_news

class NewsExporter:
    """Экспорт новостей в файл для бегущей строки"""
    
    @staticmethod
    def export_to_txt(news_items, sources_config, filename=None, is_scheduled=False):
        """Экспорт новостей в текстовый файл с группировкой по источникам"""
        if not news_items:
            print("❌ Нет новостей для экспорта!")
            return None
            
        if not filename:
            if is_scheduled:
                # В автоматическом режиме используем фиксированное имя
                filename = os.path.join(get_base_path(), "news_call.txt")
            else:
                # В ручном режиме используем timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(get_base_path(), f"news_ticker_{timestamp}.txt")
        else:
            # Если указано имя файла, используем базовый путь
            filename = os.path.join(get_base_path(), filename)
        
        try:
            # Группируем новости по источникам
            news_by_source = {}
            for news in news_items:
                source = news['source']
                if source not in news_by_source:
                    news_by_source[source] = []
                news_by_source[source].append(news)
            
            # Записываем в файл с группировкой по источникам
            with open(filename, 'w', encoding='utf-8') as f:
                # Проходим по источникам в порядке конфигурации
                for source_name in sources_config.keys():
                    if source_name in news_by_source and news_by_source[source_name]:
                        # Записываем название источника
                        f.write(f"{source_name}\n")
                        # Записываем новости этого источника
                        for news in news_by_source[source_name]:
                            f.write(news['text'] + '\n')
                        # Добавляем пустую строку между источниками
                        f.write('\n')
            
            # Статистика
            total_chars = sum(len(news['text']) for news in news_items)
            avg_length = total_chars // len(news_items)
            
            if is_scheduled:
                print(f"✅ Новости экспортированы в файл (авто-режим): {filename}")
            else:
                print(f"✅ Новости экспортированы в файл: {filename}")
                
            print(f"📊 Статистика обработки:")
            print(f"   📰 Количество новостей: {len(news_items)}")
            print(f"   📏 Средняя длина: {avg_length} символов")
            print(f"   🎯 В диапазоне 150-200: {sum(1 for n in news_items if 150 <= n['length'] <= 200)}")
            print(f"   📐 Диапазон: {min(n['length'] for n in news_items)}-{max(n['length'] for n in news_items)} символов")
            
            return filename
        except Exception as e:
            print(f"❌ Ошибка при экспорте в файл: {e}")
            return None

class NewsApp:
    """Главный класс приложения"""
    
    def __init__(self):
        self.collector = NewsCollector()
        self.exporter = NewsExporter()
        self.scheduler_running = False
        self.scheduler_thread = None
    
    def clear_screen(self):
        """Очистка экрана консоли"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self):
        """Вывод заголовка приложения"""
        self.clear_screen()
        print("=" * 70)
        print("           🎯 СИСТЕМА СБОРА НОВОСТЕЙ - WINDOWS ПРИЛОЖЕНИЕ")
        print("=" * 70)
        mode = "EXE" if is_frozen() else "Python"
        print(f"🤖 РЕЖИМ: {mode} | УПРОЩЕННЫЙ AI ДЛЯ ПЕРЕСКАЗА НОВОСТЕЙ")
        print("📝 ФОРМАТ: КАЖДАЯ НОВОСТЬ - ОДНА СТРОКА ДО 200 СИМВОЛОВ")
        print("📰 ГРУППИРОВКА ПО ИСТОЧНИКАМ С НАЗВАНИЯМИ")
        print("🛠️  ВНЕШНИЕ ФИЛЬТРЫ: filters.json")
        print("🚫 БЕЗ ЗАВИСИМОСТИ ОТ ВНЕШНИХ API")
        print("-" * 70)
    
    def wait_for_enter(self):
        """Ожидание нажатия Enter"""
        input("\n↵ Нажмите Enter для продолжения...")
    
<<<<<<< Updated upstream
=======
    def choose_directory(self):
        """Выбор каталога для сохранения через диалоговое окно"""
        try:
            # Создаем скрытое окно Tkinter
            root = tk.Tk()
            root.withdraw()  # Скрываем главное окно
            
            # Открываем диалог выбора папки
            directory = filedialog.askdirectory(
                title="Выберите папку для сохранения новостей",
                initialdir=get_base_path()
            )
            
            root.destroy()
            
            if directory:
                print(f"📁 Выбрана папка: {directory}")
                return directory
            else:
                print("ℹ️  Используется папка программы")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка при выборе папки: {e}")
            print("ℹ️  Используется папка программы")
            return None
    
    def setup_auto_save_directory(self):
        """Настройка папки для автоматического сохранения"""
        self.print_header()
        print("--- НАСТРОЙКА ПАПКИ ДЛЯ АВТОМАТИЧЕСКОГО СОХРАНЕНИЯ ---")
        
        current_dir = self.collector.get_auto_save_directory()
        print(f"📁 Текущая папка для автоматического сохранения: {current_dir}")
        
        print("\nВыберите действие:")
        print("1. 📁 Выбрать другую папку")
        print("2. 🔄 Сбросить на папку программы")
        print("0. ↩️  Назад")
        
        choice = input("Выберите вариант (0-2): ").strip()
        
        if choice == "1":
            directory = self.choose_directory()
            if directory:
                if self.collector.set_auto_save_directory(directory):
                    print(f"✅ Папка для автоматического сохранения установлена: {directory}")
        elif choice == "2":
            if self.collector.set_auto_save_directory(None):
                print("✅ Папка для автоматического сохранения сброшена на папку программы")
        elif choice == "0":
            return
        else:
            print("❌ Неверный выбор!")
        
        self.wait_for_enter()
    
>>>>>>> Stashed changes
    def add_source_interface(self):
        """Интерфейс добавления источника"""
        self.print_header()
        print("--- ДОБАВЛЕНИЕ НОВОГО ИСТОЧНИКА ---")
        name = input("Введите название источника: ").strip()
        if not name:
            print("❌ Название не может быть пустым!")
            self.wait_for_enter()
            return
            
        url = input("Введите URL источника: ").strip()
        if not url.startswith('http'):
            print("❌ URL должен начинаться с http:// или https://")
            self.wait_for_enter()
            return
        
        try:
            max_news = int(input("Введите максимальное количество новостей (по умолчанию 5): ") or "5")
        except ValueError:
            max_news = 5
        
        self.collector.add_source(name, url, max_news)
        self.wait_for_enter()
    
    def edit_source_interface(self):
        """Интерфейс редактирования источника"""
        self.print_header()
        print("--- РЕДАКТИРОВАНИЕ ИСТОЧНИКА ---")
        
        sources = list(self.collector.sources["sources"].keys())
        if not sources:
            print("📭 Нет добавленных источников для редактирования")
            self.wait_for_enter()
            return
        
        print("📋 Список источников для редактирования:")
        for i, source_name in enumerate(sources, 1):
            config = self.collector.sources["sources"][source_name]
            print(f"  {i}. {source_name} - {config['url']} (макс: {config['max_news']})")
        
        try:
            choice = int(input(f"\nВыберите номер источника для редактирования (1-{len(sources)}): "))
            if 1 <= choice <= len(sources):
                old_name = sources[choice - 1]
                old_config = self.collector.sources["sources"][old_name]
                
                print(f"\nРедактирование источника: {old_name}")
                new_name = input(f"Новое название [{old_name}]: ").strip() or old_name
                new_url = input(f"Новый URL [{old_config['url']}]: ").strip() or old_config['url']
                new_max_news = input(f"Новое макс. количество новостей [{old_config['max_news']}]: ").strip()
                new_max_news = int(new_max_news) if new_max_news else old_config['max_news']
                
                self.collector.edit_source(old_name, new_name, new_url, new_max_news)
            else:
                print("❌ Неверный выбор!")
        except (ValueError, IndexError):
            print("❌ Неверный ввод!")
        
        self.wait_for_enter()
    
    def remove_source_interface(self):
        """Интерфейс удаления источника"""
        self.print_header()
        print("--- УДАЛЕНИЕ ИСТОЧНИКА ---")
        
        sources = list(self.collector.sources["sources"].keys())
        if not sources:
            print("📭 Нет добавленных источников")
            self.wait_for_enter()
            return
        
        print("📋 Список источников для удаления:")
        for i, source_name in enumerate(sources, 1):
            config = self.collector.sources["sources"][source_name]
            print(f"  {i}. {source_name} - {config['url']}")
        
        try:
            choice = int(input(f"\nВыберите номер источника для удаления (1-{len(sources)}): "))
            if 1 <= choice <= len(sources):
                source_name = sources[choice - 1]
                confirm = input(f"Вы уверены, что хотите удалить источник '{source_name}'? (y/n): ").strip().lower()
                if confirm in ['y', 'yes', 'д', 'да']:
                    self.collector.remove_source(source_name)
                else:
                    print("❌ Удаление отменено")
            else:
                print("❌ Неверный выбор!")
        except (ValueError, IndexError):
            print("❌ Неверный ввод!")
        
        self.wait_for_enter()
    
    def manage_filters_interface(self):
        """Интерфейс управления фильтрами"""
        self.print_header()
        print("--- УПРАВЛЕНИЕ ФИЛЬТРАМИ ---")
        
        print("1. 📝 Добавить глобальное стоп-слово")
        print("2. 📝 Добавить стоп-слово для источника")
        print("3. 📋 Показать текущие фильтры")
        print("4. 📁 Открыть файл фильтров вручную")
        print("0. ↩️  Назад")
        
        choice = input("Выберите действие (0-4): ").strip()
        
        if choice == "1":
            self.add_global_stop_word()
        elif choice == "2":
            self.add_source_stop_word()
        elif choice == "3":
            self.show_filters()
        elif choice == "4":
            self.open_filters_file()
        elif choice == "0":
            return
        else:
            print("❌ Неверный выбор!")
            self.wait_for_enter()
    
    def add_global_stop_word(self):
        """Добавление глобального стоп-слова"""
        self.print_header()
        print("--- ДОБАВЛЕНИЕ ГЛОБАЛЬНОГО СТОП-СЛОВА ---")
        
        word = input("Введите стоп-слово или фразу для удаления: ").strip()
        if word:
            self.collector.filter_manager.add_global_stop_word(word)
            print(f"✅ Слово '{word}' будет удаляться из всех новостей")
        else:
            print("❌ Слово не может быть пустым!")
        
        self.wait_for_enter()
    
    def add_source_stop_word(self):
        """Добавление стоп-слова для конкретного источника"""
        self.print_header()
        print("--- ДОБАВЛЕНИЕ СТОП-СЛОВА ДЛЯ ИСТОЧНИКА ---")
        
        sources = list(self.collector.sources["sources"].keys())
        if not sources:
            print("📭 Нет добавленных источников")
            self.wait_for_enter()
            return
        
        print("📋 Список источников:")
        for i, source_name in enumerate(sources, 1):
            print(f"  {i}. {source_name}")
        
        try:
            choice = int(input(f"Выберите источник (1-{len(sources)}): "))
            if 1 <= choice <= len(sources):
                source_name = sources[choice - 1]
                word = input("Введите стоп-слово или фразу для удаления: ").strip()
                if word:
                    self.collector.filter_manager.add_source_stop_word(source_name, word)
                    print(f"✅ Слово '{word}' будет удаляться из новостей источника '{source_name}'")
                else:
                    print("❌ Слово не может быть пустым!")
            else:
                print("❌ Неверный выбор!")
        except (ValueError, IndexError):
            print("❌ Неверный ввод!")
        
        self.wait_for_enter()
    
    def show_filters(self):
        """Показать текущие фильтры"""
        self.print_header()
        print("--- ТЕКУЩИЕ ФИЛЬТРЫ ---")
        
        filters = self.collector.filter_manager.filters
        
        print("\n🌍 ГЛОБАЛЬНЫЕ ФИЛЬТРЫ:")
        print(f"   Стоп-слова: {len(filters['global_filters']['stop_words'])}")
        for word in filters['global_filters']['stop_words']:
            print(f"     - {word}")
        
        print(f"   Стоп-символы: {len(filters['global_filters']['stop_symbols'])}")
        for symbol in filters['global_filters']['stop_symbols']:
            print(f"     - {symbol}")
        
        print(f"   Regex-паттерны: {len(filters['global_filters']['regex_patterns'])}")
        
        print("\n📰 ФИЛЬТРЫ ПО ИСТОЧНИКАМ:")
        for source_name, source_filters in filters['source_specific_filters'].items():
            print(f"   {source_name}: {len(source_filters['stop_words'])} стоп-слов")
            for word in source_filters['stop_words']:
                print(f"     - {word}")
        
        self.wait_for_enter()
    
    def open_filters_file(self):
        """Открыть файл фильтров в блокноте"""
        filters_path = os.path.join(get_base_path(), "filters.json")
        try:
            if os.name == 'nt':  # Windows
                os.system(f'notepad "{filters_path}"')
            else:
                # Для Linux/Mac
                subprocess.call(['xdg-open', filters_path])
            print("✅ Файл filters.json открыт для редактирования")
        except Exception as e:
            print(f"❌ Не удалось открыть файл: {e}")
        
        self.wait_for_enter()
    
    def collect_and_export(self):
        """Сбор и экспорт новостей"""
        self.print_header()
        print("--- СБОР И ЭКСПОРТ НОВОСТЕЙ ---")
        
        if not self.collector.sources["sources"]:
            print("❌ Нет добавленных источников! Добавьте источники сначала.")
            self.wait_for_enter()
            return
        
        news = self.collector.collect_news()
        
        if not news:
            print("❌ Новости не найдены!")
            self.wait_for_enter()
            return
        
        print("\n💾 Настройка экспорта:")
        print("1. Автоматическое имя файла (с timestamp)")
        print("2. Указать имя файла вручную")
        print("3. Использовать news_call.txt (для автоматического режима)")
        
        choice = input("Выберите вариант (1-3): ").strip()
        
        if choice == "1":
            filename = None
        elif choice == "2":
            filename = input("Введите имя файла: ").strip()
            if not filename:
                filename = None
        elif choice == "3":
            filename = "news_call.txt"
        else:
            filename = None
        
        result_file = self.exporter.export_to_txt(
            news, 
            self.collector.sources["sources"], 
            filename, 
            is_scheduled=False
        )
        if result_file:
            print(f"📁 Файл сохранен: {result_file}")
        
        self.wait_for_enter()
    
    def setup_schedule(self):
        """Настройка автоматического сбора по расписанию"""
        self.print_header()
        print("--- НАСТРОЙКА АВТОМАТИЧЕСКОГО СБОРА ---")
        
        if not self.collector.sources["sources"]:
            print("❌ Нет добавленных источников! Добавьте источники сначала.")
            self.wait_for_enter()
            return
        
        # Показываем текущую папку для автоматического сохранения
        auto_save_dir = self.collector.get_auto_save_directory()
        print(f"📁 Текущая папка для автоматического сохранения: {auto_save_dir}")
        
        print("\nВыберите интервал автоматического сбора:")
        print("1. Каждые 30 минут")
        print("2. Каждый час")
        print("3. Каждые 2 часа")
        print("4. Каждые 3 часа")
        print("5. Каждые 4 часа")
        print("6. Каждые 5 часов")
        print("7. Ежедневно в определенное время")
        print("8. Отменить расписание")
        
        choice = input("Выберите вариант (1-8): ").strip()
        
        schedule.clear()
        
        if choice == "1":
            schedule.every(30).minutes.do(self.scheduled_task)
            print("✅ Расписание установлено: каждые 30 минут")
        elif choice == "2":
            schedule.every().hour.do(self.scheduled_task)
            print("✅ Расписание установлено: каждый час")
        elif choice == "3":
            schedule.every(2).hours.do(self.scheduled_task)
            print("✅ Расписание установлено: каждые 2 часа")
        elif choice == "4":
            schedule.every(3).hours.do(self.scheduled_task)
            print("✅ Расписание установлено: каждые 3 часа")
        elif choice == "5":
            schedule.every(4).hours.do(self.scheduled_task)
            print("✅ Расписание установлено: каждые 4 часа")
        elif choice == "6":
            schedule.every(5).hours.do(self.scheduled_task)
            print("✅ Расписание установлено: каждые 5 часов")
        elif choice == "7":
            time_str = input("Введите время в формате HH:MM: ").strip()
            try:
                schedule.every().day.at(time_str).do(self.scheduled_task)
                print(f"✅ Расписание установлено: ежедневно в {time_str}")
            except Exception as e:
                print(f"❌ Ошибка установки расписания: {e}")
        elif choice == "8":
            print("✅ Расписание отменено")
        else:
            print("❌ Неверный выбор!")
        
        self.wait_for_enter()
    
    def scheduled_task(self):
        """Задача для выполнения по расписания"""
        print(f"\n⏰ [Расписание] Автоматический сбор новостей в {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        try:
            news = self.collector.collect_news()
            if news:
                filename = "news_call.txt"
                # Используем папку для автоматического сохранения
                auto_save_dir = self.collector.get_auto_save_directory()
                result_file = self.exporter.export_to_txt(
                    news, 
                    self.collector.sources["sources"], 
                    filename, 
                    is_scheduled=True,
                    directory=auto_save_dir
                )
                if result_file:
                    print(f"📁 Файл обновлен: {result_file}")
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
        self.print_header()
        print("--- ЗАПУСК ПЛАНИРОВЩИКА ---")
        
        if not self.scheduler_running:
            self.scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
            self.scheduler_thread.start()
            print("✅ Планировщик запущен в фоновом режиме")
            print("💡 Планировщик будет работать, пока приложение активно")
        else:
            print("ℹ️  Планировщик уже запущен")
        
        self.wait_for_enter()
    
    def stop_scheduler(self):
        """Остановка планировщика"""
        self.scheduler_running = False
        schedule.clear()
        print("✅ Планировщик остановлен")
    
    def quick_start(self):
        """Быстрый старт с примером источников"""
        self.print_header()
        print("--- БЫСТРЫЙ СТАРТ ---")
        
        example_sources = {
            "47news.ru": "https://47news.ru",
            "Фонтанка": "https://www.fontanka.ru",
            "78.ru": "https://78.ru",
            "МК Петербург": "https://spb.mk.ru"
        }
        
        added_count = 0
        for name, url in example_sources.items():
            if name not in self.collector.sources["sources"]:
                self.collector.add_source(name, url, 5)
                added_count += 1
        
        if added_count > 0:
            print(f"✅ Добавлено {added_count} примеров источников!")
        else:
            print("ℹ️  Все примеры источников уже добавлены")
        
        self.collector.list_sources()
        self.wait_for_enter()
    
    def show_system_info(self):
        """Показать системную информацию"""
        self.print_header()
        print("--- СИСТЕМНАЯ ИНФОРМАЦИЯ ---")
        
        print(f"📁 Текущая папка: {get_base_path()}")
        print(f"🐍 Версия Python: {sys.version.split()[0]}")
        print(f"📦 Режим: {'EXE' if is_frozen() else 'Python Script'}")
        print(f"📰 Количество источников: {len(self.collector.sources['sources'])}")
        print(f"⏰ Планировщик: {'✅ Активен' if self.scheduler_running else '❌ Остановлен'}")
        
        # Папка для автоматического сохранения
        auto_save_dir = self.collector.get_auto_save_directory()
        print(f"📁 Папка автосохранения: {auto_save_dir}")
        
        # Проверяем наличие файлов
        files_to_check = ["sources.json", "news_call.txt", "filters.json"]
        for file in files_to_check:
            file_path = os.path.join(get_base_path(), file)
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                print(f"📄 {file}: {size} байт")
            else:
                print(f"📄 {file}: ❌ Не найден")
        
        # Информация о фильтрах
        filters = self.collector.filter_manager.filters
        print(f"🛠️  Глобальных фильтров: {len(filters['global_filters']['stop_words'])}")
        print(f"📰 Источников с фильтрами: {len(filters['source_specific_filters'])}")
        
        self.wait_for_enter()
    
    def main_menu(self):
        """Главное меню приложения"""
        while True:
            self.print_header()
            
            print("ГЛАВНОЕ МЕНЮ:")
            print("1. 📋 Показать источники")
            print("2. ➕ Добавить источник")
            print("3. ✏️  Редактировать источник")
            print("4. ❌ Удалить источник")
            print("5. 📡 Собрать и экспортировать новости")
            print("6. ⚙️  Настроить автоматический сбор")
            print("7. 🔄 Запустить фоновый планировщик")
            print("8. ⏹️  Остановить планировщик")
            print("9. 🚀 Быстрый старт (добавить примеры источников)")
            print("10. ℹ️  Системная информация")
            print("0. 🚪 Выход")
            print("-" * 70)
            
            choice = input("Выберите действие (0-10): ").strip()
            
            if choice == "1":
                self.print_header()
                self.collector.list_sources()
                self.wait_for_enter()
            elif choice == "2":
                self.add_source_interface()
            elif choice == "3":
                self.edit_source_interface()
            elif choice == "4":
                self.remove_source_interface()
            elif choice == "5":  # НОВЫЙ ПУНКТ
                self.manage_filters_interface()
            elif choice == "6":
                self.collect_and_export()
            elif choice == "7":
                self.setup_schedule()
            elif choice == "8":
                self.start_scheduler()
            elif choice == "9":
                self.stop_scheduler()
                self.wait_for_enter()
            elif choice == "9":
                self.quick_start()
            elif choice == "10":
                self.show_system_info()
            elif choice == "0":
                self.stop_scheduler()
                print("\n👋 До свидания!")
                break
            else:
                print("❌ Неверный выбор!")
                self.wait_for_enter()

def main():
    """Основная функция запуска приложения"""
    print("🚀 Загрузка News Collector System...")
    print("💡 Самодостаточное Windows приложение...")
    print("🛠️  Система внешних фильтров...")
    time.sleep(1)
    
    app = NewsApp()
    
    # Проверяем наличие источников, предлагаем быстрый старт
    if not app.collector.sources["sources"]:
        app.print_header()
        print("ℹ️  Источники новостей не настроены.")
        quick_start = input("Хотите выполнить быстрый старт с примерами источников? (y/n): ").strip().lower()
        if quick_start in ['y', 'yes', 'д', 'да']:
            app.quick_start()
    
    app.main_menu()

if __name__ == "__main__":
    main()
