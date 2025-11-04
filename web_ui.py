from flask import Flask, render_template_string, request, redirect, url_for, jsonify
import os
import json
from datetime import datetime
from news_collector import NewsCollector, NewsExporter
import threading
import time
import schedule
import atexit

app = Flask(__name__)

# Глобальные переменные для состояния
collector = NewsCollector()
exporter = NewsExporter()
is_collecting = False
last_collection_time = None
collection_status = "Готов к работе"
scheduler_running = False
scheduler_thread = None
scheduler_interval = 60  # минуты

# HTML шаблон
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>News Collector Web UI</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #2c3e50, #34495e);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .header p {
            opacity: 0.9;
            font-size: 1.1em;
        }
        .content {
            padding: 30px;
        }
        .controls {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: #f8f9fa;
            padding: 25px;
            border-radius: 10px;
            border-left: 5px solid #667eea;
        }
        .card-scheduler {
            border-left-color: #28a745;
        }
        .btn {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 12px 25px;
            border-radius: 8px;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
            text-align: center;
            margin: 5px;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }
        .btn:disabled {
            background: #6c757d;
            cursor: not-allowed;
            transform: none;
        }
        .btn-success {
            background: linear-gradient(135deg, #28a745, #20c997);
        }
        .btn-danger {
            background: linear-gradient(135deg, #e74c3c, #c0392b);
        }
        .btn-warning {
            background: linear-gradient(135deg, #ffc107, #fd7e14);
        }
        .btn-sm {
            padding: 8px 15px;
            font-size: 12px;
        }
        .status {
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
            font-weight: bold;
        }
        .status-collecting {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
        }
        .status-ready {
            background: #d1ecf1;
            border: 1px solid #bee5eb;
            color: #0c5460;
        }
        .status-error {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }
        .status-scheduler {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .news-list {
            max-height: 500px;
            overflow-y: auto;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 20px;
            background: white;
        }
        .news-item {
            padding: 15px;
            border-bottom: 1px solid #e9ecef;
            margin-bottom: 10px;
        }
        .news-item:last-child {
            border-bottom: none;
            margin-bottom: 0;
        }
        .news-source {
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
            font-size: 1.1em;
        }
        .news-text {
            color: #2c3e50;
            line-height: 1.5;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            border: 1px solid #e9ecef;
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }
        .stat-label {
            color: #6c757d;
            margin-top: 5px;
        }
        .sources-list {
            margin: 20px 0;
        }
        .source-item {
            padding: 15px;
            background: #f8f9fa;
            margin: 10px 0;
            border-radius: 8px;
            border-left: 3px solid #667eea;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .source-actions {
            display: flex;
            gap: 10px;
        }
        .last-update {
            text-align: center;
            color: #6c757d;
            margin: 20px 0;
            font-style: italic;
        }
        .alert {
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
        }
        .alert-success {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .alert-info {
            background: #d1ecf1;
            border: 1px solid #bee5eb;
            color: #0c5460;
        }
        .scheduler-controls {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .form-group {
            margin: 15px 0;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input, select {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        .edit-form {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 News Collector System</h1>
            <p>Автоматический сбор и обработка новостей</p>
        </div>
        
        <div class="content">
            <!-- Статус и уведомления -->
            {% if message %}
            <div class="alert alert-success">
                {{ message }}
            </div>
            {% endif %}
            
            <div class="status status-{{ status_type }}">
                📊 {{ status }}
            </div>

            {% if scheduler_running %}
            <div class="status status-scheduler">
                ⏰ Планировщик активен (интервал: {{ scheduler_interval }} мин.)
            </div>
            {% endif %}

            <!-- Статистика -->
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number">{{ sources_count }}</div>
                    <div class="stat-label">Источников</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ last_news_count }}</div>
                    <div class="stat-label">Последних новостей</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ last_collection_time or 'Никогда' }}</div>
                    <div class="stat-label">Последнее обновление</div>
                </div>
            </div>

            <!-- Панель управления -->
            <div class="controls">
                <div class="card">
                    <h3>📡 Сбор новостей</h3>
                    <p>Запустите сбор новостей со всех источников</p>
                    <form method="POST" action="/collect">
                        <button type="submit" class="btn" {% if is_collecting %}disabled{% endif %}>
                            {% if is_collecting %}⏳ Сбор...{% else %}🚀 Запустить сбор{% endif %}
                        </button>
                    </form>
                </div>

                <div class="card">
                    <h3>📋 Управление источниками</h3>
                    <p>Добавьте или удалите источники новостей</p>
                    <a href="/sources" class="btn">🔧 Управление источниками</a>
                </div>

                <div class="card card-scheduler">
                    <h3>⏰ Планировщик</h3>
                    <p>Автоматический сбор по расписанию</p>
                    {% if scheduler_running %}
                    <a href="/scheduler/stop" class="btn btn-danger">⏹️ Остановить</a>
                    {% else %}
                    <a href="/scheduler" class="btn btn-success">🔄 Настроить</a>
                    {% endif %}
                    <div style="margin-top: 10px; font-size: 12px; color: #666;">
                        Статус: {% if scheduler_running %}✅ Активен{% else %}❌ Остановлен{% endif %}
                    </div>
                </div>

                <div class="card">
                    <h3>💾 Экспорт новостей</h3>
                    <p>Скачайте последние собранные новости</p>
                    <a href="/download" class="btn">📥 Скачать файл</a>
                </div>
            </div>

            <!-- Список источников -->
            <div class="sources-list">
                <h3>📰 Активные источники:</h3>
                {% for source in sources %}
                <div class="source-item">
                    <div>
                        <strong>{{ source }}</strong><br>
                        <small>URL: {{ sources[source]['url'] }}</small><br>
                        <small>Макс. новостей: {{ sources[source]['max_news'] }}</small>
                    </div>
                    <div class="source-actions">
                        <a href="/edit_source/{{ source }}" class="btn btn-warning btn-sm">✏️ Редактировать</a>
                        <a href="/delete_source/{{ source }}" onclick="return confirm('Удалить источник {{ source }}?')" class="btn btn-danger btn-sm">❌ Удалить</a>
                    </div>
                </div>
                {% endfor %}
            </div>

            <!-- Последние новости -->
            {% if last_news %}
            <h3>📄 Последние новости:</h3>
            <div class="news-list">
                {% for news in last_news %}
                <div class="news-item">
                    <div class="news-source">{{ news.source }}</div>
                    <div class="news-text">{{ news.text }}</div>
                </div>
                {% endfor %}
            </div>
            {% endif %}

            <div class="last-update">
                🤖 Система работает на упрощенном AI для пересказа новостей
            </div>
        </div>
    </div>

    <script>
        // Авто-обновление статуса каждые 5 секунд
        setInterval(function() {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    if (data.is_collecting || data.reload) {
                        window.location.reload();
                    }
                });
        }, 5000);

        // Показываем уведомления на 5 секунд
        setTimeout(function() {
            const alerts = document.querySelectorAll('.alert');
            alerts.forEach(alert => {
                alert.style.display = 'none';
            });
        }, 5000);
    </script>
</body>
</html>
'''

def background_collect():
    """Фоновая задача сбора новостей"""
    global is_collecting, collection_status, last_collection_time, last_news
    
    try:
        is_collecting = True
        collection_status = "⏳ Идет сбор новостей..."
        
        # Сбор новостей
        news = collector.collect_news()
        
        # Экспорт в файл
        if news:
            exporter.export_to_txt(news, collector.sources["sources"], "news_call.txt", is_scheduled=True)
            collection_status = f"✅ Сбор завершен! Обработано {len(news)} новостей"
            last_news = news[:10]  # Сохраняем последние 10 новостей для показа
        else:
            collection_status = "❌ Новости не найдены"
        
        last_collection_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    except Exception as e:
        collection_status = f"❌ Ошибка при сборе: {str(e)}"
    finally:
        is_collecting = False

def run_scheduler():
    """Запуск планировщика в отдельном потоке"""
    global scheduler_running
    scheduler_running = True
    while scheduler_running:
        schedule.run_pending()
        time.sleep(1)

def start_scheduler(interval_minutes):
    """Запуск планировщика с указанным интервалом"""
    global scheduler_thread, scheduler_running, scheduler_interval
    
    stop_scheduler()
    
    # Очищаем предыдущее расписание
    schedule.clear()
    
    # Устанавливаем новое расписание
    schedule.every(interval_minutes).minutes.do(scheduled_task)
    scheduler_interval = interval_minutes
    
    # Запускаем планировщик в отдельном потоке
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    print(f"✅ Планировщик запущен с интервалом {interval_minutes} минут")

def stop_scheduler():
    """Остановка планировщика"""
    global scheduler_running, scheduler_thread
    scheduler_running = False
    schedule.clear()
    if scheduler_thread and scheduler_thread.is_alive():
        scheduler_thread.join(timeout=1)
    print("✅ Планировщик остановлен")

def scheduled_task():
    """Задача для выполнения по расписанию"""
    print(f"⏰ [Планировщик] Автоматический сбор новостей в {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    background_collect()

# Глобальные переменные для хранения состояния
last_news = []

@app.route('/')
def index():
    """Главная страница"""
    global last_collection_time, collection_status, is_collecting, scheduler_running, scheduler_interval
    
    return render_template_string(HTML_TEMPLATE,
        sources=collector.sources["sources"],
        sources_count=len(collector.sources["sources"]),
        last_news_count=len(last_news),
        last_collection_time=last_collection_time,
        status=collection_status,
        status_type="ready" if not is_collecting else "collecting",
        is_collecting=is_collecting,
        last_news=last_news,
        message=request.args.get('message'),
        scheduler_running=scheduler_running,
        scheduler_interval=scheduler_interval
    )

@app.route('/collect', methods=['POST'])
def collect_news():
    """Запуск сбора новостей"""
    global is_collecting
    
    if is_collecting:
        return redirect('/?message=Сбор+уже+запущен')
    
    # Запускаем в отдельном потоке
    thread = threading.Thread(target=background_collect)
    thread.daemon = True
    thread.start()
    
    return redirect('/?message=Запущен+сбор+новостей')

@app.route('/sources')
def manage_sources():
    """Страница управления источниками"""
    sources_html = f'''
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Управление источниками</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
            .btn {{ background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 5px; }}
            .btn-success {{ background: #28a745; }}
            .btn-warning {{ background: #ffc107; color: black; }}
            .btn-danger {{ background: #dc3545; }}
            .form-group {{ margin: 15px 0; }}
            label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
            input {{ width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }}
            .source-item {{ padding: 15px; border: 1px solid #eee; margin: 10px 0; border-radius: 8px; }}
            .source-header {{ display: flex; justify-content: space-between; align-items: center; }}
            .source-actions {{ display: flex; gap: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔧 Управление источниками</h1>
            <a href="/" class="btn">← Назад</a>
            
            <h2>Добавить источник</h2>
            <form method="POST" action="/add_source">
                <div class="form-group">
                    <label>Название:</label>
                    <input type="text" name="name" required>
                </div>
                <div class="form-group">
                    <label>URL:</label>
                    <input type="url" name="url" required>
                </div>
                <div class="form-group">
                    <label>Макс. новостей:</label>
                    <input type="number" name="max_news" value="5" min="1" max="20">
                </div>
                <button type="submit" class="btn btn-success">➕ Добавить источник</button>
            </form>
            
            <h2>Текущие источники</h2>
            {'<p>Нет добавленных источников</p>' if not collector.sources["sources"] else ''}
    '''
    
    # Добавляем список источников с кнопками редактирования
    for name, config in collector.sources["sources"].items():
        sources_html += f'''
            <div class="source-item">
                <div class="source-header">
                    <div>
                        <strong>{name}</strong><br>
                        <small>URL: {config['url']}</small><br>
                        <small>Макс. новостей: {config['max_news']}</small>
                    </div>
                    <div class="source-actions">
                        <a href="/edit_source/{name}" class="btn btn-warning">✏️ Редактировать</a>
                        <a href="/delete_source/{name}" onclick="return confirm('Удалить источник {name}?')" class="btn btn-danger">❌ Удалить</a>
                    </div>
                </div>
            </div>
        '''
    
    sources_html += '''
        </div>
    </body>
    </html>
    '''
    return sources_html

@app.route('/add_source', methods=['POST'])
def add_source():
    """Добавление нового источника"""
    name = request.form['name']
    url = request.form['url']
    max_news = int(request.form['max_news'])
    
    collector.add_source(name, url, max_news)
    return redirect('/?message=Источник+успешно+добавлен')

@app.route('/edit_source/<name>')
def edit_source(name):
    """Страница редактирования источника"""
    if name not in collector.sources["sources"]:
        return redirect('/sources?message=Источник+не+найден')
    
    config = collector.sources["sources"][name]
    
    edit_html = f'''
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Редактирование источника</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
            .btn {{ background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }}
            .btn-success {{ background: #28a745; }}
            .form-group {{ margin: 15px 0; }}
            label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
            input {{ width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>✏️ Редактирование источника</h1>
            <a href="/sources" class="btn">← Назад</a>
            
            <form method="POST" action="/update_source/{name}">
                <div class="form-group">
                    <label>Название:</label>
                    <input type="text" name="name" value="{name}" required>
                </div>
                <div class="form-group">
                    <label>URL:</label>
                    <input type="url" name="url" value="{config['url']}" required>
                </div>
                <div class="form-group">
                    <label>Макс. новостей:</label>
                    <input type="number" name="max_news" value="{config['max_news']}" min="1" max="20">
                </div>
                <button type="submit" class="btn btn-success">💾 Сохранить изменения</button>
            </form>
        </div>
    </body>
    </html>
    '''
    return edit_html

@app.route('/update_source/<old_name>', methods=['POST'])
def update_source(old_name):
    """Обновление источника"""
    new_name = request.form['name']
    url = request.form['url']
    max_news = int(request.form['max_news'])
    
    # Если имя изменилось, удаляем старый и создаем новый
    if old_name != new_name:
        collector.remove_source(old_name)
    
    collector.add_source(new_name, url, max_news)
    return redirect('/sources?message=Источник+успешно+обновлен')

@app.route('/delete_source/<name>')
def delete_source(name):
    """Удаление источника"""
    collector.remove_source(name)
    return redirect('/sources?message=Источник+удален')

@app.route('/scheduler')
def scheduler_page():
    """Страница настройки планировщика"""
    scheduler_html = f'''
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Настройка планировщика</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
            .btn {{ background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }}
            .btn-success {{ background: #28a745; }}
            .form-group {{ margin: 15px 0; }}
            label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
            select, input {{ width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }}
            .status {{ padding: 15px; border-radius: 8px; margin: 10px 0; }}
            .status-active {{ background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⏰ Настройка планировщика</h1>
            <a href="/" class="btn">← Назад</a>
            
            {'<div class="status status-active">✅ Планировщик активен</div>' if scheduler_running else ''}
            
            <form method="POST" action="/scheduler/start">
                <div class="form-group">
                    <label>Интервал сбора (минуты):</label>
                    <select name="interval">
                        <option value="30">30 минут</option>
                        <option value="60" selected>1 час</option>
                        <option value="120">2 часа</option>
                        <option value="180">3 часа</option>
                        <option value="240">4 часа</option>
                        <option value="300">5 часов</option>
                    </select>
                </div>
                
                <button type="submit" class="btn btn-success">
                    {'🔄 Перезапустить' if scheduler_running else '🚀 Запустить планировщик'}
                </button>
            </form>
            
            {'<a href="/scheduler/stop" class="btn" style="background: #dc3545; margin-top: 10px;">⏹️ Остановить планировщик</a>' if scheduler_running else ''}
            
            <div style="margin-top: 30px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                <h3>ℹ️ Информация</h3>
                <p>Планировщик автоматически собирает новости с указанным интервалом.</p>
                <p>Собранные новости сохраняются в файл <code>news_call.txt</code></p>
            </div>
        </div>
    </body>
    </html>
    '''
    return scheduler_html

@app.route('/scheduler/start', methods=['POST'])
def scheduler_start():
    """Запуск планировщика"""
    interval = int(request.form['interval'])
    start_scheduler(interval)
    return redirect('/?message=Планировщик+запущен')

@app.route('/scheduler/stop')
def scheduler_stop():
    """Остановка планировщика"""
    stop_scheduler()
    return redirect('/?message=Планировщик+остановлен')

@app.route('/download')
def download_news():
    """Скачивание файла с новостями"""
    if os.path.exists("news_call.txt"):
        return redirect('/static/news_call.txt')
    else:
        return redirect('/?message=Файл+с+новостями+не+найден')

@app.route('/status')
def get_status():
    """API статуса для AJAX"""
    return jsonify({
        'is_collecting': is_collecting,
        'status': collection_status,
        'last_update': last_collection_time,
        'scheduler_running': scheduler_running,
        'reload': request.args.get('reload', False)
    })

def cleanup():
    """Очистка при завершении"""
    stop_scheduler()

# Регистрируем функцию очистки
atexit.register(cleanup)

if __name__ == '__main__':
    # Создаем папку для статических файлов
    if not os.path.exists('static'):
        os.makedirs('static')
    
    # Копируем файл новостей в статическую папку для доступа
    if os.path.exists("news_call.txt"):
        import shutil
        shutil.copy2("news_call.txt", "static/news_call.txt")
    
    print("🚀 Запуск Web UI...")
    print("📧 Доступно по адресу: http://localhost:5000")
    print("⏰ Планировщик: /scheduler")
    print("🔧 Управление источниками: /sources")
    print("💡 Для остановки нажмите Ctrl+C")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
