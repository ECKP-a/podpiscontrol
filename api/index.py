from http.server import BaseHTTPRequestHandler
import json
import sqlite3

# ==================== БАЗА ДАННЫХ ====================
def init_db():
    """Инициализация базы данных"""
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
        print("✅ База данных инициализирована")
    except Exception as e:
        print(f"❌ Ошибка БД: {e}")

# ==================== ОСНОВНОЙ ОБРАБОТЧИК ====================
class TelegramBotHandler(BaseHTTPRequestHandler):
    """Обработчик Telegram бота"""
    
    def do_GET(self):
        """Обработка GET запросов (проверка работы)"""
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write('✅ Бот работает!'.encode('utf-8'))
    
    def do_POST(self):
        """Обработка сообщений от Telegram"""
        try:
            # Читаем данные запроса
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            update = json.loads(post_data)
            
            print(f"📨 Получено сообщение: {update}")
            
            if 'message' in update:
                chat_id = update['message']['chat']['id']
                text = update['message'].get('text', '').strip()
                
                print(f"💬 Обработка: '{text}' от {chat_id}")
                
                # Обрабатываем команды
                response_data = self._process_command(chat_id, text)
                
                # Отправляем ответ
                self._send_telegram_response(response_data)
                return
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            print(f"📋 Детали: {traceback.format_exc()}")
        
        # Всегда отвечаем 200 для Telegram
        self.send_response(200)
        self.end_headers()
    
    def _process_command(self, chat_id: int, text: str) -> dict:
        """Обработка команд пользователя"""
        
        if text == '/start':
            return {
                'chat_id': chat_id,
                'text': """🎯 *Единый Центр Контроля Подписок*

*Ваш персональный помощник в управлении подписками*

📊 *Возможности:*
• Учет всех подписок в одном месте
• Напоминания о списаниях  
• Анализ расходов
• Помощь в отмене подписок

*Используйте команды ниже ↓*""",
                'parse_mode': 'Markdown'
            }
        
        elif text == '/subs':
            keyboard = [
                [{"text": "🛍️ Яндекс Плюс"}, {"text": "📺 СберПрайм"}],
                [{"text": "🎬 Ozon Premium"}, {"text": "🛒 ВБ Клуб"}],
                [{"text": "📱 Сотовые услуги"}, {"text": "🎵 VK Музыка"}],
                [{"text": "➕ Добавить свою подписку"}, {"text": "📊 Мои подписки"}],
                [{"text": "🔙 Главное меню"}]
            ]
            
            return {
                'chat_id': chat_id,
                'text': "📋 *Управление подписками*\n\nВыберите действие:",
                'reply_markup': {
                    'keyboard': keyboard,
                    'resize_keyboard': True,
                    'one_time_keyboard': False
                },
                'parse_mode': 'Markdown'
            }
        
        elif text == '/laws':
            return {
                'chat_id': chat_id,
                'text': """⚖️ *Федеральный закон № 376-ФЗ*

*С 15 октября 2025 года:*

✅ Сервисы обязаны получать ваше *прямое согласие* на каждое списание
✅ *Запрещено* автоматическое продление без подтверждения  
✅ Отмена подписки должна быть *не сложнее*, чем оформление

*Ваши права защищены!*""",
                'parse_mode': 'Markdown'
            }
        
        elif text == '📊 Мои подписки':
            # Проверяем работу базы данных
            try:
                conn = sqlite3.connect('/tmp/subscriptions.db')
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                conn.close()
                
                response_text = f"✅ База данных работает! Таблицы: {tables}"
            except Exception as e:
                response_text = f"❌ Ошибка БД: {e}"
            
            return {
                'chat_id': chat_id,
                'text': response_text
            }
        
        elif text == '➕ Добавить свою подписку':
            return {
                'chat_id': chat_id,
                'text': """➕ *Добавление своей подписки*

Введите данные в формате:
`Название - Стоимость - Дата списания`

*Примеры:*
• `Netflix - 599 - 15`
• `Спортзал - 2000 - 1`
• `Apple Music - 169 - 10`""",
                'parse_mode': 'Markdown'
            }
        
        elif text in ['🛍️ Яндекс Плюс', '📺 СберПрайм', '🎬 Ozon Premium', '🛒 ВБ Клуб']:
            prices = {
                '🛍️ Яндекс Плюс': '399₽',
                '📺 СберПрайм': '299₽', 
                '🎬 Ozon Premium': '199₽',
                '🛒 ВБ Клуб': '199₽'
            }
            
            return {
                'chat_id': chat_id,
                'text': f"🔍 *{text}*\n\n*Стоимость:* {prices.get(text, '?')} в месяц\n\nДобавить для отслеживания?",
                'parse_mode': 'Markdown'
            }
        
        elif text == '🔙 Главное меню':
            return {
                'chat_id': chat_id,
                'text': "Возврат в главное меню",
                'parse_mode': 'Markdown'
            }
        
        else:
            return {
                'chat_id': chat_id,
                'text': "🤔 Не понял команду. Используйте /start для начала работы",
                'parse_mode': 'Markdown'
            }
    
    def _send_telegram_response(self, response_data: dict):
        """Отправка ответа в Telegram"""
        payload = {
            'method': 'sendMessage',
            'chat_id': response_data['chat_id'],
            'text': response_data['text']
        }
        
        # Добавляем дополнительные параметры если есть
        if 'reply_markup' in response_data:
            payload['reply_markup'] = response_data['reply_markup']
        if 'parse_mode' in response_data:
            payload['parse_mode'] = response_data['parse_mode']
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode('utf-8'))

# ==================== ВАЖНО: ЭКСПОРТ ПЕРЕМЕННОЙ ====================
# Vercel требует эту переменную!
handler = TelegramBotHandler

# Инициализируем базу данных при запуске
init_db()
