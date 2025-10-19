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

class SubscriptionManager:
    """Менеджер популярных подписок"""
    
    POPULAR_SUBSCRIPTIONS = {
        'Яндекс Плюс': {'price': 399, 'description': 'Кино, музыка, доставка'},
        'СберПрайм': {'price': 299, 'description': 'Okko, музыка, доставка'},
        'Ozon Premium': {'price': 199, 'description': 'Бесплатная доставка'},
        'ВБ Клуб': {'price': 199, 'description': 'Бесплатная доставка'},
        'VK Музыка': {'price': 199, 'description': 'Музыка без ограничений'},
        'Яндекс Музыка': {'price': 169, 'description': 'Каталог музыки'},
        'IVI': {'price': 399, 'description': 'Фильмы и сериалы'},
        'START': {'price': 299, 'description': 'Русские сериалы'},
        'More.tv': {'price': 299, 'description': 'Эксклюзивный контент'},
        'Wink': {'price': 349, 'description': 'Ростелеком кино'},
        'PREMIER': {'price': 399, 'description': 'Эксклюзивы и шоу'},
        'Кинопоиск': {'price': 399, 'description': 'Фильмы и сериалы'},
        'Магнит Премиум': {'price': 199, 'description': 'Скидки в магазинах'},
        'Alfa Only': {'price': 199, 'description': 'Премиум банк'},
        'ВТБ Плюс': {'price': 199, 'description': 'Подписка ВТБ'},
        'МТС Premium': {'price': 299, 'description': 'Кино, музыка, скидки'},
        'Т-Банк Pro': {'price': 299, 'description': 'Премиум банк'},
        'Газпром Бонус': {'price': 299, 'description': 'Топливо и подписки'},
        'Пакет X5': {'price': 149, 'description': 'Скидки в Пятерочке'},
        'Сотовые услуги': {'price': 300, 'description': 'Ежемесячная связь'}
    }
    
    @classmethod
    def get_main_keyboard(cls):
        """Главная клавиатура"""
        return {
            'keyboard': [
                [{'text': '📋 Управление подписками'}],
                [{'text': '⚖️ О законе'}, {'text': '❓ Помощь'}],
                [{'text': '📊 Мои подписки'}, {'text': '➕ Быстро добавить'}]
            ],
            'resize_keyboard': True
        }
    
    @classmethod
    def get_subscriptions_keyboard(cls):
        """Клавиатура управления подписками"""
        subscriptions = list(cls.POPULAR_SUBSCRIPTIONS.keys())
        keyboard = []
        
        # Группируем по 2 подписки в ряд для компактности
        for i in range(0, min(12, len(subscriptions)), 2):
            row = [
                {'text': subscriptions[i]}, 
                {'text': subscriptions[i+1] if i+1 < len(subscriptions) else '📄 Ещё...'}
            ]
            keyboard.append(row)
        
        # Сервисные кнопки
        keyboard.extend([
            [{'text': '➕ Своя подписка'}, {'text': '📊 Мои подписки'}],
            [{'text': '🗑️ Удалить подписку'}, {'text': '🔙 Главное меню'}]
        ])
        
        return {
            'keyboard': keyboard,
            'resize_keyboard': True
        }
    
    @classmethod
    def get_subscription_info(cls, service_name):
        """Информация о подписке"""
        return cls.POPULAR_SUBSCRIPTIONS.get(service_name)

class BotHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.db = DatabaseManager()
        self.sub_manager = SubscriptionManager()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write('Bot is running with enhanced interface!'.encode('utf-8'))
    
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
        if text == '/start' or text == '🔙 Главное меню':
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': '🎯 *Единый Центр Контроля Подписок*\n\nВаш персональный помощник в управлении подписками\n\n*Выберите действие:*',
                'reply_markup': self.sub_manager.get_main_keyboard(),
                'parse_mode': 'Markdown'
            }
        
        elif text == '📋 Управление подписками' or text == '/subs':
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': '📋 *Управление подписками*\n\nВыберите популярную подписку или воспользуйтесь сервисными кнопками:',
                'reply_markup': self.sub_manager.get_subscriptions_keyboard(),
                'parse_mode': 'Markdown'
            }
        
        elif text == '📊 Мои подписки':
            subscriptions = self.db.get_user_subscriptions(chat_id)
            
            if subscriptions:
                total = sum(price for _, price, _ in subscriptions)
                sub_list = "\n".join([
                    f"• {name}: {price} руб (списание {day} числа)"
                    for name, price, day in subscriptions
                ])
                
                message = f"📊 *Ваши подписки*\n\n{sub_list}\n\n💎 *Итого в месяц:* {total} руб\n📈 *Всего подписок:* {len(subscriptions)}"
            else:
                message = "📊 *У вас пока нет активных подписок*\n\nДобавьте первую подписку через меню управления!"
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
        
        elif text == '➕ Быстро добавить' or text == '➕ Своя подписка':
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': '➕ *Добавление своей подписки*\n\nВведите данные в формате:\n`Название - Цена - Дата`\n\n*Примеры:*\n• Netflix - 599 - 15\n• Спортзал - 2000 - 1\n• Яндекс Такси - 500 - 10',
                'parse_mode': 'Markdown'
            }
        
        elif text in self.sub_manager.POPULAR_SUBSCRIPTIONS:
            # Показываем информацию о подписке
            info = self.sub_manager.get_subscription_info(text)
            keyboard = {
                'keyboard': [
                    [{'text': f'✅ Добавить {text}'}],
                    [{'text': '📋 К подпискам'}]
                ],
                'resize_keyboard': True
            }
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': f'🔍 *{text}*\n\n*Стоимость:* {info["price"]} руб/мес\n*Описание:* {info["description"]}\n\nДобавить для отслеживания?',
                'reply_markup': keyboard,
                'parse_mode': 'Markdown'
            }
        
        elif text.startswith('✅ Добавить '):
            # Обработка добавления популярной подписки
            service_name = text.replace('✅ Добавить ', '')
            info = self.sub_manager.get_subscription_info(service_name)
            
            success, message = self.db.add_subscription(chat_id, service_name, info['price'], 1)
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': f'*{message}*\n\n*Подписка:* {service_name}\n*Стоимость:* {info["price"]} руб/мес\n*Списание:* 1 число каждого месяца',
                'parse_mode': 'Markdown'
            }
        
        elif text == '🗑️ Удалить подписку':
            subscriptions = self.db.get_user_subscriptions(chat_id)
            
            if subscriptions:
                keyboard = []
                for name, price, day in subscriptions:
                    keyboard.append([{'text': f'❌ Удалить {name}'}])
                keyboard.append([{'text': '📋 К подпискам'}])
                
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': '🗑️ *Удаление подписки*\n\nВыберите подписку для удаления:',
                    'reply_markup': {'keyboard': keyboard, 'resize_keyboard': True},
                    'parse_mode': 'Markdown'
                }
            else:
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': 'ℹ️ У вас нет подписок для удаления.'
                }
        
        elif text.startswith('❌ Удалить '):
            # Обработка удаления конкретной подписки
            service_name = text.replace('❌ Удалить ', '')
            success, message = self.db.delete_subscription(chat_id, service_name)
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': f'*{message}*\n\nПодписка: {service_name}',
                'parse_mode': 'Markdown'
            }
        
        elif self._is_subscription_format(text):
            # Обработка пользовательской подписки
            return self._handle_custom_subscription(chat_id, text)
        
        elif text in ['📋 К подпискам', '📄 Ещё...']:
            return self.process_message(chat_id, '📋 Управление подписками')
        
        elif text == '⚖️ О законе' or text == '/laws':
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': '⚖️ *Федеральный закон № 376-ФЗ*\n\n*С 15 октября 2025 года:*\n\n✅ Сервисы обязаны получать ваше прямое согласие на каждое списание\n✅ Запрещено автоматическое продление без подтверждения\n✅ Отмена подписки должна быть не сложнее, чем оформление\n\n*Ваши права защищены!*',
                'parse_mode': 'Markdown'
            }
        
        elif text == '❓ Помощь' or text == '/help':
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': '❓ *Помощь и поддержка*\n\n*Частые вопросы:*\n\n• Как добавить подписку? - Используйте меню "Управление подписками"\n• Как отменить подписку? - Напишите "Отмена [название подписки]"\n• Не нашли свою подписку? - Используйте "Своя подписка"\n\n*Напишите ваш вопрос - помогу разобраться!*',
                'parse_mode': 'Markdown'
            }
        
        else:
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': '🤔 Не понял команду. Используйте кнопки меню или /start для начала работы'
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
                    'text': '❌ Ошибка: дата должна быть от 1 до 31'
                }
            
            success, message = self.db.add_subscription(chat_id, name, price_val, day_val)
            
            response_text = f'✅ *Подписка добавлена!*\n\n*Название:* {name}\n*Стоимость:* {price_val} руб\n*Списание:* {day_val} число\n\nТеперь вы можете видеть её в "Мои подписки"' if success else f'❌ {message}'
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': response_text,
                'parse_mode': 'Markdown'
            }
            
        except ValueError:
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': '❌ Неверный формат. Пример: `Netflix - 599 - 15`',
                'parse_mode': 'Markdown'
            }
        except Exception as e:
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': f'❌ Ошибка: {str(e)}'
            }

handler = BotHandler
