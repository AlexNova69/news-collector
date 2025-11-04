from flask import Flask, render_template_string, request, redirect, url_for, jsonify
import os
import json
from datetime import datetime
from news_collector import NewsCollector, NewsExporter
import threading
import time

app = Flask(__name__)

# Глобальные переменные для состояния
collector = NewsCollector()
exporter = NewsExporter()
is_collecting = False
last_collection_time = None
collection_status = "Готов к работе"

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
            max-width: 1200px;
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
        .btn {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
            text-align: center;
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
        .btn-danger {
            background: linear-gradient(135deg, #e74c3c, #c0392b);
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
            padding: 10px 15px;
            background: #f8f9fa;
            margin: 5px 0;
            border-radius: 5px;
            border-left: 3px solid #667eea;
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
                    <strong>{{ source }}</strong> - {{ sources[source]['url'] }}
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
                    if (data.is_collecting) {
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

# Глобальные переменные для хранения состояния
last_news = []

@app.route('/')
def index():
    """Главная страница"""
    global last_collection_time, collection_status, is_collecting
    
    return render_template_string(HTML_TEMPLATE,
        sources=collector.sources["sources"],
        sources_count=len(collector.sources["sources"]),
        last_news_count=len(last_news),
        last_collection_time=last_collection_time,
        status=collection_status,
        status_type="ready" if not is_collecting else "collecting",
        is_collecting=is_collecting,
        last_news=last_news,
        message=request.args.get('message')
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
    sources_html = '''
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Управление источниками</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
            .btn { background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }
            .form-group { margin: 15px 0; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
            .source-item { padding: 10px; border: 1px solid #eee; margin: 5px 0; }
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
                    <input type="number" name="max_news" value="5">
                </div>
                <button type="submit" class="btn">➕ Добавить</button>
            </form>
            
            <h2>Текущие источники</h2>
            ''' + ''.join([f'''
            <div class="source-item">
                <strong>{name}</strong> - {config['url']} (макс: {config['max_news']})
                <a href="/delete_source/{name}" onclick="return confirm('Удалить источник?')" style="color: red; margin-left: 10px;">❌ Удалить</a>
            </div>
            ''' for name, config in collector.sources["sources"].items()]) + '''
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

@app.route('/delete_source/<name>')
def delete_source(name):
    """Удаление источника"""
    collector.remove_source(name)
    return redirect('/sources')

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
        'last_update': last_collection_time
    })

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
    print("💡 Для остановки нажмите Ctrl+C")
    
    app.run(debug=True, host='0.0.0.0', port=5000)