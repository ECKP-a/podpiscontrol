from http.server import BaseHTTPRequestHandler
import json
import sqlite3
import re
from datetime import datetime, timedelta

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
                    next_charge_date TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            print("База данных инициализирована")
        except Exception as e:
            print(f"Ошибка БД: {e}")
    
    def add_subscription(self, user_id, service_name, price, charge_day, next_charge_date):
        """Добавление подписки в базу"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id FROM subscriptions 
                WHERE user_id = ? AND service_name = ? AND is_active = TRUE
            ''', (user_id, service_name))
            
            existing = cursor.fetchone()
            if existing:
                conn.close()
                return False, "Подписка уже добавлена"
            
            cursor.execute('''
                INSERT INTO subscriptions (user_id, service_name, price, charge_day, next_charge_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, service_name, price, charge_day, next_charge_date))
            
            conn.commit()
            conn.close()
            return True, "Подписка успешно добавлена"
            
        except Exception as e:
            print(f"Ошибка добавления подписки: {e}")
            return False, "Ошибка при добавлении подписки"
    
    def get_user_subscriptions(self, user_id):
        """Получение всех подписок пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT service_name, price, charge_day, next_charge_date 
                FROM subscriptions 
                WHERE user_id = ? AND is_active = TRUE
                ORDER BY service_name
            ''', (user_id,))
            
            subscriptions = cursor.fetchall()
            conn.close()
            return subscriptions
            
        except Exception as e:
            print(f"Ошибка получения подписок: {e}")
            return []
    
    def delete_subscription(self, user_id, service_name):
        """Удаление подписки"""
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
            print(f"Ошибка удаления подписки: {e}")
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
        'Кинопоиск': {'price': 399, 'description': 'Фильмы и сериалы'},
        'МТС Premium': {'price': 299, 'description': 'Кино, музыка, скидки'}
    }
    
    @classmethod
    def get_main_keyboard(cls):
        """Главная клавиатура с 6 командами"""
        return {
            'keyboard': [
                [{'text': '/start'}, {'text': '/subs'}],
                [{'text': '/help'}, {'text': '/laws'}],
                [{'text': '/sets'}, {'text': '/unsub'}]
            ],
            'resize_keyboard': True
        }
    
    @classmethod
    def get_subscriptions_keyboard(cls):
        """Клавиатура популярных подписок"""
        subscriptions = list(cls.POPULAR_SUBSCRIPTIONS.keys())
        keyboard = []
        
        # Группируем по 2 подписки в ряд
        for i in range(0, len(subscriptions), 2):
            if i + 1 < len(subscriptions):
                keyboard.append([{'text': subscriptions[i]}, {'text': subscriptions[i+1]}])
            else:
                keyboard.append([{'text': subscriptions[i]}])
        
        keyboard.extend([
            [{'text': '➕ Своя подписка'}],
            [{'text': '🔙 Главное меню'}]
        ])
        
        return {
            'keyboard': keyboard,
            'resize_keyboard': True
        }
    
    @classmethod
    def get_cancel_keyboard(cls):
        """Клавиатура для отмены"""
        return {
            'keyboard': [[{'text': '❌ Отмена'}]],
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
        self.user_sessions = {}
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write('🎯 Единый центр контроля подписок - работает!'.encode('utf-8'))
    
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
        # Проверяем активную сессию добавления подписки
        if chat_id in self.user_sessions and self.user_sessions[chat_id].get('adding_subscription'):
            return self._handle_subscription_flow(chat_id, text)
        
        # Обработка команды отмены
        if text == '❌ Отмена' or text == '🔙 Главное меню':
            if chat_id in self.user_sessions:
                del self.user_sessions[chat_id]
            return self._show_main_menu(chat_id)
        
        # Обработка команд
        if text == '/start':
            return self._show_main_menu(chat_id)
        
        elif text == '/subs':
            return self._show_subscriptions_menu(chat_id)
        
        elif text == '/help':
            return self._show_help(chat_id)
        
        elif text == '/laws':
            return self._show_laws(chat_id)
        
        elif text == '/sets':
            return self._show_settings(chat_id)
        
        elif text == '/unsub':
            return self._show_unsubscribe(chat_id)
        
        # Обработка популярных подписок
        elif text in self.sub_manager.POPULAR_SUBSCRIPTIONS:
            return self._show_subscription_info(chat_id, text)
        
        # Обработка добавления популярной подписки
        elif text.startswith('✅ '):
            service_name = text.replace('✅ ', '')
            return self._add_popular_subscription(chat_id, service_name)
        
        # Обработка удаления подписки
        elif text.startswith('❌ '):
            service_name = text.replace('❌ ', '')
            return self._delete_subscription(chat_id, service_name)
        
        # Обработка "Своя подписка"
        elif text == '➕ Своя подписка':
            return self._start_custom_subscription(chat_id)
        
        else:
            # Неизвестная команда - показываем главное меню
            return self._show_main_menu(chat_id)
    
    def _show_main_menu(self, chat_id):
        """Главное меню с 6 командами"""
        return {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': """🎯 *Единый центр контроля подписок*

*Доступные команды:*

/start - Главное меню
/subs - Управление подписками
/help - Помощь и консультация
/laws - Правовая информация  
/sets - Настройка уведомлений
/unsub - Отмена подписок

Выберите команду:""",
            'reply_markup': self.sub_manager.get_main_keyboard(),
            'parse_mode': 'Markdown'
        }
    
    def _show_subscriptions_menu(self, chat_id):
        """Меню управления подписками"""
        return {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': '📋 *Управление подписками*\n\nВыберите популярную подписку или добавьте свою:',
            'reply_markup': self.sub_manager.get_subscriptions_keyboard(),
            'parse_mode': 'Markdown'
        }
    
    def _show_subscription_info(self, chat_id, service_name):
        """Информация о популярной подписке"""
        info = self.sub_manager.get_subscription_info(service_name)
        keyboard = {
            'keyboard': [
                [{'text': f'✅ {service_name}'}],
                [{'text': '🔙 Главное меню'}]
            ],
            'resize_keyboard': True
        }
        
        return {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': f'*{service_name}*\n\n💳 *Стоимость:* {info["price"]} руб/мес\n📝 *Описание:* {info["description"]}\n\nДобавить для отслеживания?',
            'reply_markup': keyboard,
            'parse_mode': 'Markdown'
        }
    
    def _add_popular_subscription(self, chat_id, service_name):
        """Добавление популярной подписки"""
        info = self.sub_manager.get_subscription_info(service_name)
        
        # Вычисляем дату следующего списания
        today = datetime.now()
        if today.day > 1:
            next_month = today.replace(day=1) + timedelta(days=32)
            next_charge_date = next_month.replace(day=1).strftime("%d.%m.%Y")
        else:
            next_charge_date = today.replace(day=1).strftime("%d.%m.%Y")
        
        success, message = self.db.add_subscription(
            chat_id, 
            service_name, 
            info['price'], 
            1,
            next_charge_date
        )
        
        if success:
            response_text = f'✅ *Подписка добавлена!*\n\n📺 *{service_name}*\n💳 {info["price"]} руб/мес\n📅 Следующее списание: {next_charge_date}'
        else:
            response_text = f'❌ *{message}*'
        
        return {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': response_text,
            'parse_mode': 'Markdown',
            'reply_markup': self.sub_manager.get_main_keyboard()
        }
    
    def _start_custom_subscription(self, chat_id):
        """Начало добавления своей подписки"""
        self.user_sessions[chat_id] = {
            'adding_subscription': True,
            'step': 'name'
        }
        
        return {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': '➕ *Добавление своей подписки*\n\nВведите название подписки:',
            'parse_mode': 'Markdown',
            'reply_markup': self.sub_manager.get_cancel_keyboard()
        }
    
    def _handle_subscription_flow(self, chat_id, text):
        """Обработка добавления своей подписки"""
        session = self.user_sessions[chat_id]
        
        if session['step'] == 'name':
            session['name'] = text
            session['step'] = 'price'
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': '💳 Введите стоимость подписки в рублях:',
                'parse_mode': 'Markdown',
                'reply_markup': self.sub_manager.get_cancel_keyboard()
            }
        
        elif session['step'] == 'price':
            try:
                # Очищаем текст от лишних символов
                clean_text = re.sub(r'[^\d,.]', '', text.replace(',', '.'))
                price = float(clean_text)
                
                if price <= 0:
                    raise ValueError("Цена должна быть положительной")
                
                session['price'] = price
                session['step'] = 'date'
                
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': '📅 Когда следующее списание?\n\nВведите дату (ДД.ММ.ГГГГ) или число месяца:',
                    'parse_mode': 'Markdown',
                    'reply_markup': self.sub_manager.get_cancel_keyboard()
                }
                
            except (ValueError, TypeError):
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': '❌ Неверный формат цены. Введите число:',
                    'parse_mode': 'Markdown',
                    'reply_markup': self.sub_manager.get_cancel_keyboard()
                }
        
        elif session['step'] == 'date':
            try:
                today = datetime.now()
                
                if re.match(r'^\d{1,2}\.\d{1,2}\.\d{4}$', text):
                    charge_date = datetime.strptime(text, "%d.%m.%Y")
                    next_charge_date = charge_date.strftime("%d.%m.%Y")
                    charge_day = charge_date.day
                
                elif re.match(r'^\d{1,2}$', text):
                    day = int(text)
                    if 1 <= day <= 31:
                        if today.day <= day:
                            next_date = today.replace(day=day)
                        else:
                            next_month = today.replace(day=1) + timedelta(days=32)
                            next_date = next_month.replace(day=day)
                        next_charge_date = next_date.strftime("%d.%m.%Y")
                        charge_day = day
                    else:
                        raise ValueError("День должен быть от 1 до 31")
                else:
                    raise ValueError("Неверный формат даты")
                
                # Сохраняем подписку
                success, message = self.db.add_subscription(
                    chat_id, 
                    session['name'], 
                    session['price'], 
                    charge_day,
                    next_charge_date
                )
                
                del self.user_sessions[chat_id]
                
                if success:
                    response_text = f'✅ *Подписка добавлена!*\n\n📺 *{session["name"]}*\n💳 {session["price"]} руб/мес\n📅 Следующее списание: {next_charge_date}'
                else:
                    response_text = f'❌ *{message}*'
                
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': response_text,
                    'parse_mode': 'Markdown',
                    'reply_markup': self.sub_manager.get_main_keyboard()
                }
                
            except ValueError as e:
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': '❌ Неверный формат даты. Введите ДД.ММ.ГГГГ или число:',
                    'parse_mode': 'Markdown',
                    'reply_markup': self.sub_manager.get_cancel_keyboard()
                }
    
    def _show_help(self, chat_id):
        """Помощь и консультация"""
        return {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': """❓ *Помощь и консультация*

*Частые вопросы:*

• Как добавить подписку?
Используйте команду /subs и выберите из списка или добавьте свою

• Как отменить подписку?
Используйте команду /unsub

• Что делать если списали деньги без согласия?
Обратитесь в поддержку сервиса и ссылайтесь на ФЗ-376

*Нужна дополнительная помощь?*
Опишите вашу проблему - мы поможем!""",
            'parse_mode': 'Markdown',
            'reply_markup': self.sub_manager.get_main_keyboard()
        }
    
    def _show_laws(self, chat_id):
        """Правовая информация"""
        return {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': """⚖️ *Федеральный закон № 376-ФЗ*

*Ключевые положения:*

• Запрет списаний с удаленных карт
• Обязанность приема отказа от платежных средств
• Защита прав потребителей

*Вступает в силу:* 1 марта 2026 года

*Наш сервис помогает контролировать подписки в соответствии с законодательством.*""",
            'parse_mode': 'Markdown',
            'reply_markup': self.sub_manager.get_main_keyboard()
        }
    
    def _show_settings(self, chat_id):
        """Настройка уведомлений"""
        return {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': """⚙️ *Настройка уведомлений*

*Функция в разработке*

Скоро вы сможете настроить:
• Уведомления о предстоящих списаниях
• Напоминания об отмене пробных периодов
• Ежемесячные отчеты о подписках

Следите за обновлениями!""",
            'parse_mode': 'Markdown',
            'reply_markup': self.sub_manager.get_main_keyboard()
        }
    
    def _show_unsubscribe(self, chat_id):
        """Отмена подписок"""
        subscriptions = self.db.get_user_subscriptions(chat_id)
        
        if not subscriptions:
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': 'У вас нет активных подписок.',
                'parse_mode': 'Markdown',
                'reply_markup': self.sub_manager.get_main_keyboard()
            }
        
        keyboard = []
        for name, price, day, next_date in subscriptions:
            keyboard.append([{'text': f'❌ {name}'}])
        
        keyboard.append([{'text': '🔙 Главное меню'}])
        
        return {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': '🗑️ *Отмена подписок*\n\nВыберите подписку для удаления:',
            'reply_markup': {'keyboard': keyboard, 'resize_keyboard': True},
            'parse_mode': 'Markdown'
        }
    
    def _delete_subscription(self, chat_id, service_name):
        """Удаление подписки"""
        success, message = self.db.delete_subscription(chat_id, service_name)
        
        if success:
            response_text = f'✅ *Подписка удалена:* {service_name}'
        else:
            response_text = f'❌ *Ошибка:* {message}'
        
        return {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': response_text,
            'parse_mode': 'Markdown',
            'reply_markup': self.sub_manager.get_main_keyboard()
        }

handler = BotHandler