from http.server import BaseHTTPRequestHandler
import json
import sqlite3
import os

# Инициализация базы данных
def init_db():
    try:
        conn = sqlite3.connect('/tmp/subscriptions.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                service_name TEXT,
                price REAL,
                charge_day INTEGER,
                is_active BOOLEAN DEFAULT TRUE,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database init error: {e}")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write('Bot is running successfully!'.encode())
    
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            update = json.loads(post_data)
            
            print(f"Received: {update}")
            
            if 'message' in update:
                chat_id = update['message']['chat']['id']
                text = update['message'].get('text', '')
                
                print(f"Processing: {text} from {chat_id}")
                
                if text == '/start':
                    response_text = """Я — Единый центр контроля подписок.

Используйте команды:
/subs - Управление подписками  
/laws - Информация о законе
/unsub - Отмена подписок
/help - Помощь"""
                    
                    response_data = {
                        'method': 'sendMessage',
                        'chat_id': chat_id,
                        'text': response_text
                    }
                
                elif text == '/subs':
                    keyboard = [
                        [{"text": "🛍️ Яндекс Плюс"}, {"text": "📺 СберПрайм"}],
                        [{"text": "🎬 Ozon Premium"}, {"text": "🛒 ВБ Клуб"}],
                        [{"text": "📱 Сотовые услуги"}, {"text": "🎵 VK Музыка"}],
                        [{"text": "➕ Добавить свою подписку"}, {"text": "📊 Мои подписки"}],
                        [{"text": "🔙 Назад"}]
                    ]
                    
                    response_text = "Выберите подписку для управления:"
                    
                    response_data = {
                        'method': 'sendMessage',
                        'chat_id': chat_id,
                        'text': response_text,
                        'reply_markup': {
                            'keyboard': keyboard,
                            'resize_keyboard': True,
                            'one_time_keyboard': False
                        }
                    }
                
                elif text in ['🛍️ Яндекс Плюс', '📺 СберПрайм', '🎬 Ozon Premium', '🛒 ВБ Клуб', '📱 Сотовые услуги']:
                    prices = {
                        '🛍️ Яндекс Плюс': '399₽',
                        '📺 СберПрайм': '299₽', 
                        '🎬 Ozon Premium': '199₽',
                        '🛒 ВБ Клуб': '199₽',
                        '📱 Сотовые услуги': 'от 300₽'
                    }
                    
                    response_text = f"{text}\nСтоимость: {prices.get(text, '?')} в месяц"
                    
                    response_data = {
                        'method': 'sendMessage',
                        'chat_id': chat_id,
                        'text': response_text
                    }
                
                elif text == '/laws':
                    response_text = "Федеральный закон № 376-ФЗ защищает ваши права с 15.10.2025"
                    response_data = {
                        'method': 'sendMessage',
                        'chat_id': chat_id,
                        'text': response_text
                    }
                
                elif text == '/unsub':
                    response_text = "Для отмены подписки зайдите в личный кабинет сервиса и найдите раздел 'Отключить автопродление'"
                    response_data = {
                        'method': 'sendMessage',
                        'chat_id': chat_id,
                        'text': response_text
                    }
                
                elif text == '/help':
                    response_text = "Помощь: опишите вашу проблему"
                    response_data = {
                        'method': 'sendMessage',
                        'chat_id': chat_id,
                        'text': response_text
                    }
                
                elif text == '➕ Добавить свою подписку':
                    response_text = "Введите подписку в формате: Название - Цена - Дата\nПример: Netflix - 599 - 15"
                    response_data = {
                        'method': 'sendMessage',
                        'chat_id': chat_id,
                        'text': response_text
                    }
                
                elif text == '📊 Мои подписки':
                    # Проверяем работу базы данных
                    try:
                        conn = sqlite3.connect('/tmp/subscriptions.db')
                        cursor = conn.cursor()
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                        tables = cursor.fetchall()
                        conn.close()
                        
                        response_text = f"База данных работает! Таблицы: {tables}"
                    except Exception as e:
                        response_text = f"Ошибка БД: {e}"
                    
                    response_data = {
                        'method': 'sendMessage',
                        'chat_id': chat_id,
                        'text': response_text
                    }
                
                elif text == '🔙 Назад':
                    response_text = "Возврат в главное меню"
                    response_data = {
                        'method': 'sendMessage',
                        'chat_id': chat_id,
                        'text': response_text
                    }
                
                else:
                    response_text = "Используйте команды: /start, /subs, /laws, /unsub, /help"
                    response_data = {
                        'method': 'sendMessage',
                        'chat_id': chat_id,
                        'text': response_text
                    }
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode())
                return
                
        except Exception as e:
            print(f"Error: {e}")
        
        self.send_response(200)
        self.end_headers()

def main(request):
    init_db()
    return Handler()
