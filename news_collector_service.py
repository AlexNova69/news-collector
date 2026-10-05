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
import logging
from logging.handlers import RotatingFileHandler

# Настройка логирования для службы
def setup_logging():
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    logger = logging.getLogger('NewsCollector')
    logger.setLevel(logging.INFO)
    
    # Форматтер для логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Файловый обработчик с ротацией
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'news_collector.log'),
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    
    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

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
            logger.error(f"Ошибка суммаризации: {e}")
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
            logger.warning(f"Файл конфигурации {self.config_file} не найден")
            return {"sources": {}}
    
    def save_sources(self):
        """Сохранение конфигурации источников в JSON файл"""
        try:
            os.makedirs(os.path.dirname(self.config_file) if os.path.dirname(self.config_file) else '.', exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.sources, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения конфигурации: {e}")
    
    def add_source(self, name, url, max_news=5):
        """Добавление нового источника новостей"""
        try:
            self.sources["sources"][name] = {
                "url": url,
                "max_news": max_news
            }
            self.save_sources()
            logger.info(f"Источник '{name}' добавлен успешно")
        except Exception as e:
            logger.error(f"Ошибка добавления источника: {e}")
    
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
        
        # Удаляем категории в начале текста
        text = re.sub(r'^(Чтиво|Происшествия|Образ жизни|Общество|Бизнес|На правах бизнеса|Афиша Plus|Доброе дело|Город|Лента добра|Афиша|ПроисшествияКрипта|Образ жизниОбщество|ОбществоПадали|Образ жизниУлица)\s*', '', text)
        
        # УДАЛЯЕМ ДАТЫ В ФОРМАТЕ MMDD В НАЧАЛЕ ТЕКСТА (0311, 0215 и т.д.)
        text = re.sub(r'^\d{3,4}', '', text)
        
        # Удаляем временные метки (более агрессивно)
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
                                            '.timestamp', '.news-date', '.date-time']):
                unwanted.decompose()
            
            # Пробуем разные стратегии извлечения текста
            text_candidates = []
            
            # 1. Текст из ссылок с атрибутами новостей
            links = element.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                text = link.get_text().strip()
                
                # Проверяем, что ссылка похожа на новостную
                if (self.is_valid_news(text) and 
                    any(keyword in href.lower() for keyword in ['news', 'article', 'novosti', 'novost', 'story'])):
                    text_candidates.append(text)
            
            # 2. Текст из заголовков
            for tag in ['h1', 'h2', 'h3', 'h4']:
                headers = element.find_all(tag)
                for header in headers:
                    text = header.get_text().strip()
                    if self.is_valid_news(text):
                        text_candidates.append(text)
            
            # 3. Текст из элементов с новостными классами
            news_classes = element.find_all(class_=re.compile(r'news|article|title|header|story|item'))
            for elem in news_classes:
                text = elem.get_text().strip()
                if self.is_valid_news(text):
                    text_candidates.append(text)
            
            # 4. Текст всего элемента (только если короткий и валидный)
            full_text = element.get_text().strip()
            if self.is_valid_news(full_text) and len(full_text) < 400:
                text_candidates.append(full_text)
            
            # Выбираем лучший кандидат (самый длинный из валидных)
            if text_candidates:
                # Сначала сортируем по длине, потом убираем слишком похожие
                text_candidates.sort(key=len, reverse=True)
                unique_candidates = []
                used_hashes = set()
                
                for candidate in text_candidates:
                    # ПРЕДВАРИТЕЛЬНАЯ ОЧИСТКА ОТ ДАТ
                    candidate = re.sub(r'^\d{3,4}', '', candidate)
                    candidate_hash = self.get_text_hash(self.normalize_title(candidate))
                    if candidate_hash not in used_hashes:
                        unique_candidates.append(candidate)
                        used_hashes.add(candidate_hash)
                
                if unique_candidates:
                    return self.clean_news_text(unique_candidates[0])
                    
            return None
            
        except Exception as e:
            logger.error(f"Ошибка извлечения текста: {e}")
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
            r'^\d{3,4}\s*$'  # Только даты без текста
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
        # ПРЕДВАРИТЕЛЬНАЯ ОЧИСТКА ОТ ДАТ
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
            
            logger.info(f"Загрузка главной страницы: {config['url']}")
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
                '.story', '.news-list-item', '.news-block'
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
                    # ДОПОЛНИТЕЛЬНАЯ ОЧИСТКА ОТ ДАТ ПЕРЕД ОБРАБОТКОЙ
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
                                logger.info(f"Обработано: {len(news_text)} → {len(processed_text)} симв.")
            
            return news_items
            
        except Exception as e:
            logger.error(f"Ошибка при сборе новостей с {source_name}: {e}")
            return []
    
    def collect_news(self):
        """Сбор новостей со всех источников"""
        all_news = []
        today = datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"Начало сбора новостей за {today}")
        
        for source_name, config in self.sources["sources"].items():
            logger.info(f"Сбор с {source_name}")
            news = self.fetch_news_from_source(source_name, config)
            
            # Добавляем с проверкой на меж-источниковые дубликаты
            for news_item in news:
                if not self.is_duplicate_news(news_item['text'], all_news, 0.9):
                    all_news.append(news_item)
            
            if news:
                logger.info(f"Обработано {len(news)} новостей с {source_name}")
            else:
                logger.warning(f"Новости не найдены для {source_name}")
        
        # Финальная очистка от дубликатов
        all_news = self.remove_duplicate_news(all_news)
        
        logger.info(f"Всего собрано уникальных новостей: {len(all_news)}")
        return all_news

class NewsExporter:
    """Экспорт новостей в файл для бегущей строки"""
    
    @staticmethod
    def export_to_txt(news_items, filename=None, is_scheduled=False):
        """Экспорт новостей в текстовый файл"""
        if not news_items:
            logger.warning("Нет новостей для экспорта")
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
            # В автоматическом режиме перезаписываем файл
            mode = 'w'
            with open(filename, mode, encoding='utf-16') as f:
                for news in news_items:
                    f.write(news['text'] + '\n')
            
            # Статистика
            total_chars = sum(len(news['text']) for news in news_items)
            avg_length = total_chars // len(news_items)
            
            logger.info(f"Новости экспортированы в файл: {filename}")
            logger.info(f"Статистика: {len(news_items)} новостей, средняя длина {avg_length} символов")
            
            return filename
        except Exception as e:
            logger.error(f"Ошибка при экспорте в файл: {e}")
            return None

class NewsService:
    """Служба для автоматического сбора новостей"""
    
    def __init__(self):
        self.collector = NewsCollector()
        self.exporter = NewsExporter()
        self.scheduler_running = False
        self.scheduler_thread = None
        self.interval_hours = 1  # Интервал по умолчанию
    
    def set_interval(self, hours):
        """Установка интервала сбора новостей"""
        self.interval_hours = hours
        logger.info(f"Установлен интервал сбора: каждые {hours} часов")
    
    def load_config(self):
        """Загрузка конфигурации службы"""
        try:
            config_file = "service_config.json"
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.interval_hours = config.get('interval_hours', 1)
                    logger.info(f"Конфигурация загружена: интервал {self.interval_hours} часов")
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
    
    def save_config(self):
        """Сохранение конфигурации службы"""
        try:
            config = {
                'interval_hours': self.interval_hours,
                'last_update': datetime.now().isoformat()
            }
            with open("service_config.json", 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения конфигурации: {e}")
    
    def scheduled_task(self):
        """Задача для выполнения по расписанию"""
        logger.info(f"Автоматический сбор новостей в {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        try:
            news = self.collector.collect_news()
            if news:
                # В автоматическом режиме используем фиксированное имя файла
                filename = "news_call.txt"
                result_file = self.exporter.export_to_txt(news, filename, is_scheduled=True)
                if result_file:
                    logger.info(f"Файл обновлен: {os.path.abspath(result_file)}")
                    self.save_config()  # Сохраняем время последнего обновления
            else:
                logger.warning("Новости не найдены в запланированном сборе")
        except Exception as e:
            logger.error(f"Ошибка в запланированной задаче: {e}")
    
    def setup_schedule(self):
        """Настройка расписания"""
        schedule.clear()
        
        # Настраиваем расписание в зависимости от интервала
        if self.interval_hours == 1:
            schedule.every().hour.do(self.scheduled_task)
        elif self.interval_hours == 2:
            schedule.every(2).hours.do(self.scheduled_task)
        elif self.interval_hours == 3:
            schedule.every(3).hours.do(self.scheduled_task)
        elif self.interval_hours == 4:
            schedule.every(4).hours.do(self.scheduled_task)
        elif self.interval_hours == 5:
            schedule.every(5).hours.do(self.scheduled_task)
        else:
            schedule.every().hour.do(self.scheduled_task)  # По умолчанию каждый час
        
        logger.info(f"Расписание настроено: каждые {self.interval_hours} часов")
    
    def run_scheduler(self):
        """Запуск планировщика в отдельном потоке"""
        logger.info("Планировщик запущен")
        self.scheduler_running = True
        while self.scheduler_running:
            schedule.run_pending()
            time.sleep(1)
    
    def start_service(self):
        """Запуск службы"""
        logger.info("Запуск службы сбора новостей")
        
        # Загружаем конфигурацию
        self.load_config()
        
        # Настраиваем расписание
        self.setup_schedule()
        
        # Запускаем планировщик в отдельном потоке
        self.scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        # Выполняем немедленный сбор при запуске
        self.scheduled_task()
        
        logger.info("Служба успешно запущена")
    
    def stop_service(self):
        """Остановка службы"""
        logger.info("Остановка службы")
        self.scheduler_running = False
        schedule.clear()
        logger.info("Служба остановлена")

def main():
    """Основная функция запуска службы"""
    logger.info("Запуск службы сбора новостей")
    
    service = NewsService()
    
    try:
        # Запускаем службу
        service.start_service()
        
        # Бесконечный цикл для поддержания работы службы
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания")
    except Exception as e:
        logger.error(f"Критическая ошибка в службе: {e}")
    finally:
        service.stop_service()
        logger.info("Служба завершена")

if __name__ == "__main__":
    main()