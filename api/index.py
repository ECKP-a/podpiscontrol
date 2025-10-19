from http.server import BaseHTTPRequestHandler
import json
import sqlite3
import re

class DatabaseManager:
    def __init__(self):
        self.db_path = '/tmp/subscriptions.db'
        self._init_db()
    
    def _init_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    service_name TEXT,
                    price REAL,
                    charge_day INTEGER,
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Database error: {e}")
    
    def add_subscription(self, user_id, service_name, price, charge_day):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_subscriptions (user_id, service_name, price, charge_day)
                VALUES (?, ?, ?, ?)
            ''', (user_id, service_name, price, charge_day))
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def get_user_subscriptions(self, user_id):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT service_name, price, charge_day 
                FROM user_subscriptions 
                WHERE user_id = ? AND is_active = TRUE
            ''', (user_id,))
            subscriptions = cursor.fetchall()
            conn.close()
            return subscriptions
        except:
            return []
    
    def delete_subscription(self, user_id, service_name):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE user_subscriptions 
                SET is_active = FALSE 
                WHERE user_id = ? AND service_name = ?
            ''', (user_id, service_name))
            conn.commit()
            conn.close()
            return True
        except:
            return False

class TelegramBotHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.db = DatabaseManager()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write('Bot is working perfectly!'.encode('utf-8'))
    
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            update = json.loads(post_data)
            
            if 'message' in update:
                chat_id = update['message']['chat']['id']
                text = update['message'].get('text', '').strip()
                response_data = self._process_command(chat_id, text)
                self._send_telegram_response(response_data)
                return
                
        except Exception as e:
            print(f"Error: {e}")
        
        self.send_response(200)
        self.end_headers()
    
    def _process_command(self, chat_id, text):
        # Основные команды
        if text == '/start':
            keyboard = [
                [{"text": "Управление подписками"}],
                [{"text": "О законе"}, {"text": "Помощь"}]
            ]
            return {
                'chat_id': chat_id,
                'text': 'Единый Центр Контроля Подписок. Используйте меню ниже.',
                'reply_markup': {'keyboard': keyboard, 'resize_keyboard': True}
            }
        
        elif text == 'Управление подписками' or text == '/subs':
            keyboard = [
                [{"text": "Яндекс Плюс"}, {"text": "СберПрайм"}],
                [{"text": "Ozon Premium"}, {"text": "ВБ Клуб"}],
                [{"text": "Добавить свою подписку"}, {"text": "Мои подписки"}],
                [{"text": "Удалить подписку"}, {"text": "Главное меню"}]
            ]
            return {
                'chat_id': chat_id,
                'text': 'Управление подписками:',
                'reply_markup': {'keyboard': keyboard, 'resize_keyboard': True}
            }
        
        elif text == 'Мои подписки':
            subscriptions = self.db.get_user_subscriptions(chat_id)
            if subscriptions:
                sub_list = "\n".join([f"{name}: {price} руб ({day} число)" for name, price, day in subscriptions])
                text_response = f"Ваши подписки:\n\n{sub_list}"
            else:
                text_response = "У вас пока нет подписок"
            return {'chat_id': chat_id, 'text': text_response}
        
        elif text == 'Добавить свою подписку':
            return {'chat_id': chat_id, 'text': 'Введите: Название - Цена - Дата (например: Netflix - 599 - 15)'}
        
        elif text == 'Удалить подписку':
            subscriptions = self.db.get_user_subscriptions(chat_id)
            if subscriptions:
                keyboard = [[{"text": f"Удалить {name}"}] for name, _, _ in subscriptions]
                keyboard.append([{"text": "Назад"}])
                return {
                    'chat_id': chat_id,
                    'text': 'Выберите подписку для удаления:',
                    'reply_markup': {'keyboard': keyboard, 'resize_keyboard': True}
                }
            else:
                return {'chat_id': chat_id, 'text': 'Нет подписок для удаления'}
        
        elif text.startswith('Удалить '):
            service_name = text.replace('Удалить ', '')
            success = self.db.delete_subscription(chat_id, service_name)
            response = f"Подписка {service_name} удалена" if success else "Ошибка удаления"
            return {'chat_id': chat_id, 'text': response}
        
        elif text in ['Яндекс Плюс', 'СберПрайм', 'Ozon Premium', 'ВБ Клуб']:
            prices = {'Яндекс Плюс': 399, 'СберПрайм': 299, 'Ozon Premium': 199, 'ВБ Клуб': 199}
            keyboard = [[{"text": f"Добавить {text}"}], [{"text": "Назад"}]]
            return {
                'chat_id': chat_id,
                'text': f'{text}\nЦена: {prices[text]} руб/мес\nДобавить для отслеживания?',
                'reply_markup': {'keyboard': keyboard, 'resize_keyboard': True}
            }
        
        elif text.startswith('Добавить '):
            service_name = text.replace('Добавить ', '')
            prices = {'Яндекс Плюс': 399, 'СберПрайм': 299, 'Ozon Premium': 199, 'ВБ Клуб': 199}
            success = self.db.add_subscription(chat_id, service_name, prices.get(service_name, 199), 1)
            response = f"Подписка {service_name} добавлена" if success else "Ошибка добавления"
            return {'chat_id': chat_id, 'text': response}
        
        elif self._is_subscription_format(text):
            return self._handle_custom_subscription(chat_id, text)
        
        elif text in ['Главное меню', 'Назад']:
            return self._process_command(chat_id, '/start')
        
        elif text == 'О законе' or text == '/laws':
            return {'chat_id': chat_id, 'text': 'Закон 376-ФЗ защищает права с 15.10.2025'}
        
        elif text == 'Помощь' or text == '/help':
            return {'chat_id': chat_id, 'text': 'Помощь: опишите проблему'}
        
        else:
            return {'chat_id': chat_id, 'text': 'Используйте команды из меню'}
    
    def _is_subscription_format(self, text):
        return bool(re.match(r'^[^-]+ - \d+ - (?:[1-9]|[12][0-9]|3[01])$', text))
    
    def _handle_custom_subscription(self, chat_id, text):
        try:
            name, price, day = [part.strip() for part in text.split(' - ')]
            success = self.db.add_subscription(chat_id, name, float(price), int(day))
            response = f"Подписка {name} добавлена" if success else "Ошибка добавления"
        except:
            response = "Неверный формат. Пример: Netflix - 599 - 15"
        return {'chat_id': chat_id, 'text': response}
    
    def _send_telegram_response(self, response_data):
        payload = {'method': 'sendMessage', 'chat_id': response_data['chat_id'], 'text': response_data['text']}
        if 'reply_markup' in response_data:
            payload['reply_markup'] = response_data['reply_markup']
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode('utf-8'))

handler = TelegramBotHandler
