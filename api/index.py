from http.server import BaseHTTPRequestHandler
import json
import sqlite3
import re

class DatabaseManager:
    def __init__(self):
        self.db_path = '/tmp/subscriptions.db'
        self._init_db()
    
    def _init_db(self):
        """Инициализация базы данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS subscriptions (
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
    
    def add_subscription(self, user_id, service_name, price, charge_day):
        """Добавление подписки в базу"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем, нет ли уже такой активной подписки
            cursor.execute('''
                SELECT id FROM subscriptions 
                WHERE user_id = ? AND service_name = ? AND is_active = TRUE
            ''', (user_id, service_name))
            
            existing = cursor.fetchone()
            if existing:
                conn.close()
                return False, "Подписка уже добавлена"
            
            # Добавляем новую подписку
            cursor.execute('''
                INSERT INTO subscriptions (user_id, service_name, price, charge_day)
                VALUES (?, ?, ?, ?)
            ''', (user_id, service_name, price, charge_day))
            
            conn.commit()
            conn.close()
            return True, "Подписка успешно добавлена"
            
        except Exception as e:
            print(f"❌ Ошибка добавления подписки: {e}")
            return False, "Ошибка при добавлении подписки"
    
    def get_user_subscriptions(self, user_id):
        """Получение всех подписок пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT service_name, price, charge_day 
                FROM subscriptions 
                WHERE user_id = ? AND is_active = TRUE
                ORDER BY service_name
            ''', (user_id,))
            
            subscriptions = cursor.fetchall()
            conn.close()
            return subscriptions
            
        except Exception as e:
            print(f"❌ Ошибка получения подписок: {e}")
            return []
    
    def delete_subscription(self, user_id, service_name):
        """Удаление подписки (мягкое удаление)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE subscriptions 
                SET is_active = FALSE 
                WHERE user_id = ? AND service_name = ? AND is_active = TRUE
            ''', (user_id, service_name))
            
            conn.commit()
            conn.close()
            return True, "Подписка удалена"
            
        except Exception as e:
            print(f"❌ Ошибка удаления подписки: {e}")
            return False, "Ошибка при удалении подписки"

class BotHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.db = DatabaseManager()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write('Bot is running with database!'.encode('utf-8'))
    
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            update = json.loads(post_data)
            
            if 'message' in update:
                chat_id = update['message']['chat']['id']
                text = update['message'].get('text', '').strip()
                
                response = self.process_message(chat_id, text)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return
                
        except Exception as e:
            print(f'Error: {e}')
        
        self.send_response(200)
        self.end_headers()
    
    def process_message(self, chat_id, text):
        # Популярные подписки с ценами
        popular_subscriptions = {
            'Яндекс Плюс': 399,
            'СберПрайм': 299,
            'Ozon Premium': 199,
            'ВБ Клуб': 199,
            'VK Музыка': 199,
            'Сотовые услуги': 300
        }
        
        if text == '/start':
            keyboard = [
                [{'text': 'Управление подписками'}],
                [{'text': 'О законе'}, {'text': 'Помощь'}]
            ]
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': 'Добро пожаловать! Используйте кнопки для управления подписками.',
                'reply_markup': {
                    'keyboard': keyboard,
                    'resize_keyboard': True
                }
            }
        
        elif text == 'Управление подписками' or text == '/subs':
            keyboard = [
                [{'text': 'Яндекс Плюс'}, {'text': 'СберПрайм'}],
                [{'text': 'Ozon Premium'}, {'text': 'ВБ Клуб'}],
                [{'text': 'VK Музыка'}, {'text': 'Сотовые услуги'}],
                [{'text': 'Добавить свою подписку'}, {'text': 'Мои подписки'}],
                [{'text': 'Удалить подписку'}, {'text': 'Главное меню'}]
            ]
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': 'Управление подписками:',
                'reply_markup': {
                    'keyboard': keyboard,
                    'resize_keyboard': True
                }
            }
        
        elif text == 'Мои подписки':
            subscriptions = self.db.get_user_subscriptions(chat_id)
            
            if subscriptions:
                total = sum(price for _, price, _ in subscriptions)
                sub_list = "\n".join([
                    f"• {name}: {price} руб (списание {day} числа)"
                    for name, price, day in subscriptions
                ])
                
                message = f"📊 Ваши подписки:\n\n{sub_list}\n\n💎 Итого в месяц: {total} руб"
            else:
                message = "У вас пока нет активных подписок."
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': message
            }
        
        elif text == 'Добавить свою подписку':
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': 'Введите данные в формате: Название - Цена - Дата\n\nПример:\nNetflix - 599 - 15\nСпортзал - 2000 - 1'
            }
        
        elif text in popular_subscriptions:
            # Показываем информацию о подписке и предлагаем добавить
            keyboard = [
                [{'text': f'Добавить {text}'}],
                [{'text': 'Назад к подпискам'}]
            ]
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': f'{text}\nЦена: {popular_subscriptions[text]} руб/мес\n\nДобавить для отслеживания?',
                'reply_markup': {
                    'keyboard': keyboard,
                    'resize_keyboard': True
                }
            }
        
        elif text.startswith('Добавить '):
            # Обработка добавления популярной подписки
            service_name = text.replace('Добавить ', '')
            price = popular_subscriptions.get(service_name, 199)
            
            success, message = self.db.add_subscription(chat_id, service_name, price, 1)
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': message
            }
        
        elif text == 'Удалить подписку':
            subscriptions = self.db.get_user_subscriptions(chat_id)
            
            if subscriptions:
                keyboard = []
                for name, price, day in subscriptions:
                    keyboard.append([{'text': f'Удалить {name}'}])
                keyboard.append([{'text': 'Назад'}])
                
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': 'Выберите подписку для удаления:',
                    'reply_markup': {
                        'keyboard': keyboard,
                        'resize_keyboard': True
                    }
                }
            else:
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': 'У вас нет подписок для удаления.'
                }
        
        elif text.startswith('Удалить '):
            # Обработка удаления конкретной подписки
            service_name = text.replace('Удалить ', '')
            success, message = self.db.delete_subscription(chat_id, service_name)
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': message
            }
        
        elif self._is_subscription_format(text):
            # Обработка пользовательской подписки
            return self._handle_custom_subscription(chat_id, text)
        
        elif text in ['Главное меню', 'Назад', 'Назад к подпискам']:
            return self.process_message(chat_id, '/start')
        
        elif text == 'О законе' or text == '/laws':
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': 'Федеральный закон № 376-ФЗ защищает права потребителей с 15.10.2025'
            }
        
        elif text == 'Помощь' or text == '/help':
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': 'Для помощи опишите вашу проблему'
            }
        
        else:
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': 'Используйте команды из меню или /start для начала работы'
            }
    
    def _is_subscription_format(self, text):
        """Проверка формата пользовательской подписки"""
        pattern = r'^[^-]+ - \d+ - (?:[1-9]|[12][0-9]|3[01])$'
        return bool(re.match(pattern, text))
    
    def _handle_custom_subscription(self, chat_id, text):
        """Обработка пользовательской подписки"""
        try:
            name, price, day = [part.strip() for part in text.split(' - ')]
            price_val = float(price)
            day_val = int(day)
            
            if not (1 <= day_val <= 31):
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': 'Ошибка: дата должна быть от 1 до 31'
                }
            
            success, message = self.db.add_subscription(chat_id, name, price_val, day_val)
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': message
            }
            
        except ValueError:
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': 'Неверный формат. Пример: Netflix - 599 - 15'
            }
        except Exception as e:
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': f'Ошибка: {str(e)}'
            }

handler = BotHandler
