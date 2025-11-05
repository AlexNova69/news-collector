class SimpleSummarizer:
    """Упрощенный AI-агент для пересказа новостей"""
    
    def summarize_text(self, text, max_length=200):
        """Пересказ текста новости с сохранением целостности предложений"""
        if len(text) <= max_length:
            return text
        
        try:
            # Очищаем текст
            text = self.clean_text(text)
            
            # Улучшенное разбиение на предложения с сохранением пунктуации
            sentences = []
            current_sentence = ""
            
            for char in text:
                current_sentence += char
                if char in '.!?…' and len(current_sentence) > 10:
                    sentences.append(current_sentence.strip())
                    current_sentence = ""
            
            # Добавляем последнее предложение, если оно есть
            if current_sentence.strip():
                sentences.append(current_sentence.strip())
            
            # Фильтруем слишком короткие предложения
            sentences = [s for s in sentences if len(s) > 15]
            
            if not sentences:
                return text[:max_length-3] + '...'
            
            # Берем первое предложение - обычно содержит основную информацию
            summary = sentences[0]
            
            # Добавляем следующие предложения, пока не достигнем лимита
            for i in range(1, len(sentences)):
                test_summary = summary + ' ' + sentences[i]
                if len(test_summary) <= max_length:
                    summary = test_summary
                else:
                    # Если не помещается целиком, пробуем добавить часть
                    available_space = max_length - len(summary) - 4  # -4 для " ..."
                    if available_space > 20:
                        # Добавляем часть следующего предложения
                        words = sentences[i].split()
                        partial_sentence = ""
                        for word in words:
                            if len(partial_sentence + ' ' + word) <= available_space:
                                partial_sentence += ' ' + word if partial_sentence else word
                            else:
                                break
                        if partial_sentence:
                            summary += ' ' + partial_sentence + '...'
                    break
            
            # Финальная проверка длины
            if len(summary) > max_length:
                # Пытаемся найти точку для обрезки
                if '.' in summary:
                    last_dot = summary.rfind('.', 0, max_length-3)
                    if last_dot > max_length * 0.6:  # Не обрезать слишком рано
                        summary = summary[:last_dot+1]
                    else:
                        summary = summary[:max_length-3] + '...'
                else:
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