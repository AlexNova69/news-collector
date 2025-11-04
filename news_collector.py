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
    def __init__(self, config_file="sources.json"):
        self.config_file = config_file
        self.sources = self.load_sources()
        self.summarizer = SimpleSummarizer()
        
    def load_sources(self):
        """Загрузка конфигурации источников из JSON файла"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"sources": {}}
    
    def save_sources(self):
        """Сохранение конфигурации источников в JSON файл"""
        os.makedirs(os.path.dirname(self.config_file) if os.path.dirname(self.config_file) else '.', exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.sources, f, ensure_ascii=False, indent=2)
    
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
    
    def list_sources(self):
        """Вывод списка всех источников"""
        if not self.sources["sources"]:
            print("📭 Нет добавленных источников")
            return
        
        print("\n📋 Список источников:")
        for name, config in self.sources["sources"].items():
            print(f"  📰 {name}: {config['url']} (макс. новостей: {config['max_news']})")
    
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
    
    def clean_news_text(self, text):
        """Тщательная очистка текста новости"""
        if not text:
            return ""
        
        # Удаляем лишние пробелы
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # УСИЛЕННАЯ ОЧИСТКА ВРЕМЕННЫХ МЕТОК В НАЧАЛЕ ТЕКСТА
        # Удаляем время в формате HH:MM в начале текста (10:48, 10:38 и т.д.)
        text = re.sub(r'^\d{1,2}:\d{2}\s*', '', text)
        
        # Удаляем время с пробелами вокруг двоеточия
        text = re.sub(r'^\d{1,2}\s*:\s*\d{2}\s*', '', text)
        
        # Удаляем даты в формате MMDD в начале текста (0311, 0215 и т.д.)
        text = re.sub(r'^\d{3,4}', '', text)
        
        # Удаляем категории в начале текста
        text = re.sub(r'^(Чтиво|Происшествия|Образ жизни|Общество|Бизнес|На правах бизнеса|Афиша Plus|Доброе дело|Город|Лента добра|Афиша|ПроисшествияКрипта|Образ жизниОбщество|ОбществоПадали|Образ жизниУлица)\s*', '', text)
        
        # Удаляем временные метки в конце (более агрессивно)
        text = re.sub(r'\s*\d{1,2}\.\d{2}\.\s*$', '', text)
        text = re.sub(r'[\s\d]*\d{1,2}\s*час[а]?[\s\d]*$', '', text)
        text = re.sub(r'[\s\d:-]+\s*$', '', text)
        
        # Удаляем технические символы
        text = re.sub(r'[^\w\s\.\,\!\?\-\:\(\)]', '', text)
        
        # Восстанавливаем пробелы
        text = re.sub(r'([а-яё])([А-ЯЁ])', r'\1 \2', text)
        text = re.sub(r'([.!?])([А-ЯЁ])', r'\1 \2', text)
        text = re.sub(r'([,])([а-яё])', r'\1 \2', text)
        
        # Удаляем повторяющиеся точки и запятые
        text = re.sub(r'\.{2,}', '.', text)
        text = re.sub(r',{2,}', ',', text)
        
        # Удаляем даты и числа в скобках
        text = re.sub(r'\s*\(\s*\d+\s*\)\s*', ' ', text)
        
        # Удаляем лишние слова в начале и конце
        text = re.sub(r'^(Новость|Новости|Статья|Статьи|Читать|Подробнее)\s*', '', text)
        
        # Финальная очистка пробелов
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def extract_clean_news_text(self, element):
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
                    return self.clean_news_text(unique_candidates[0])
                    
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
    
    def process_news_text(self, text):
        """Обработка текста новости с помощью AI-агента"""
        # ПРЕДВАРИТЕЛЬНАЯ ОЧИСТКА ОТ ДАТ И ВРЕМЕНИ
        text = re.sub(r'^\d{1,2}:\d{2}\s*', '', text)
        text = re.sub(r'^\d{3,4}', '', text)
        cleaned_text = self.clean_news_text(text)
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
                        
                news_text = self.extract_clean_news_text(element)
                if news_text:
                    # ДОПОЛНИТЕЛЬНАЯ ОЧИСТКА ОТ ДАТ И ВРЕМЕНИ ПЕРЕД ОБРАБОТКОЙ
                    news_text = re.sub(r'^\d{1,2}:\d{2}\s*', '', news_text)
                    news_text = re.sub(r'^\d{3,4}', '', news_text)
                    
                    # Обрабатываем AI-агентом
                    processed_text = self.process_news_text(news_text)
                    
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
                filename = "news_call.txt"
            else:
                # В ручном режиме используем timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"news_ticker_{timestamp}.txt"
        
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
            
            # Показываем примеры с группировкой по источникам
            print(f"\n📄 Примеры обработанных новостей (с группировкой по источникам):")
            print("-" * 50)
            current_source = None
            example_count = 0
            for news_item in news_items:
                if news_item['source'] != current_source:
                    current_source = news_item['source']
                    print(f"\n{current_source}:")
                print(f"  {news_item['text']} ({news_item['length']} симв.)")
                example_count += 1
                if example_count >= 8:  # Показываем не более 8 примеров
                    break
            if len(news_items) > 8:
                print(f"\n... и еще {len(news_items) - 8} новостей")
            print("-" * 50)
            
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
            print("❌ Новости не найдены!")
            return
        
        filename = input("Введите имя файла для экспорта (или Enter для автоматического): ").strip()
        if not filename:
            filename = None
        
        # Передаем конфигурацию источников для группировки
        result_file = self.exporter.export_to_txt(
            news, 
            self.collector.sources["sources"], 
            filename, 
            is_scheduled=False
        )
        if result_file:
            print(f"📁 Файл сохранен: {os.path.abspath(result_file)}")
    
    def setup_schedule(self):
        """Настройка автоматического сбора по расписанию"""
        print("\n--- Настройка расписания ---")
        print("1. Ежедневно в определенное время")
        print("2. Каждый час")
        print("3. Каждые 30 минут")
        print("4. Каждые 2 часа")
        print("5. Каждые 3 часа")
        print("6. Каждые 4 часа")
        print("7. Каждые 5 часов")
        print("8. Отменить расписание")
        
        choice = input("Выберите вариант: ").strip()
        
        schedule.clear()
        
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
            schedule.every(2).hours.do(self.scheduled_task)
            print("✅ Расписание установлено на выполнение каждые 2 часа")
        elif choice == "5":
            schedule.every(3).hours.do(self.scheduled_task)
            print("✅ Расписание установлено на выполнение каждые 3 часа")
        elif choice == "6":
            schedule.every(4).hours.do(self.scheduled_task)
            print("✅ Расписание установлено на выполнение каждые 4 часа")
        elif choice == "7":
            schedule.every(5).hours.do(self.scheduled_task)
            print("✅ Расписание установлено на выполнение каждые 5 часа")
        elif choice == "8":
            print("✅ Расписание отменено")
        else:
            print("❌ Неверный выбор!")
    
    def scheduled_task(self):
        """Задача для выполнения по расписанию"""
        print(f"\n⏰ [Расписание] Автоматический сбор новостей в {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        try:
            news = self.collector.collect_news()
            if news:
                # В автоматическом режиме используем фиксированное имя файла
                filename = "news_call.txt"
                # Передаем конфигурацию источников для группировки
                result_file = self.exporter.export_to_txt(
                    news, 
                    self.collector.sources["sources"], 
                    filename, 
                    is_scheduled=True
                )
                if result_file:
                    print(f"📁 Файл обновлен: {os.path.abspath(result_file)}")
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
        example_sources = {
            "47news.ru": "https://47news.ru",
            "Фонтанка": "https://www.fontanka.ru",
            "78.ru": "https://78.ru",
            "МК Петербург": "https://spb.mk.ru"
        }
        
        for name, url in example_sources.items():
            if name not in self.collector.sources["sources"]:
                self.collector.add_source(name, url, 5)
        
        print("✅ Примеры источников добавлены!")
        self.collector.list_sources()
    
    def main_menu(self):
        """Главное меню приложения"""
        while True:
            print("\n" + "="*60)
            print("           🎯 СИСТЕМА СБОРА НОВОСТЕЙ")
            print("="*60)
            print("🤖 УПРОЩЕННЫЙ AI ДЛЯ ПЕРЕСКАЗА НОВОСТЕЙ")
            print("📝 ФОРМАТ: КАЖДАЯ НОВОСТЬ - ОДНА СТРОКА ДО 200 СИМВОЛОВ")
            print("📰 ГРУППИРОВКА ПО ИСТОЧНИКАМ С НАЗВАНИЯМИ")
            print("🚫 БЕЗ ЗАВИСИМОСТИ ОТ ВНЕШНИХ API")
            print("-"*60)
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
                print("❌ Неверный выбор!")

def main():
    """Основная функция запуска приложения"""
    print("🚀 Загрузка упрощенной системы сбора новостей...")
    print("💡 Работает без внешних зависимостей")
    print("📰 Новости группируются по источникам с названиями")
    
    app = NewsApp()
    
    if not app.collector.sources["sources"]:
        print("\nℹ️  Источники новостей не настроены.")
        quick_start = input("Хотите выполнить быстрый старт с примерами источников? (y/n): ").strip().lower()
        if quick_start in ['y', 'yes', 'д', 'да']:
            app.quick_start()
    
    app.main_menu()

if __name__ == "__main__":
    main()
