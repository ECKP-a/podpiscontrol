from http.server import BaseHTTPRequestHandler
import json
import sqlite3
import re
from datetime import datetime, timedelta
import time

class DatabaseManager:
    def __init__(self):
        self.db_path = '/tmp/subscriptions.db'
        self._init_db()
    
    def _init_db(self):
        """Инициализация базы данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Основная таблица подписок
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
            
            # Таблица настроек напоминаний
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    subscription_id INTEGER,
                    days_before INTEGER DEFAULT 3,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (subscription_id) REFERENCES subscriptions (id)
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
                INSERT INTO subscriptions (user_id, service_name, price, charge_day, next_charge_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, service_name, price, charge_day, next_charge_date))
            
            subscription_id = cursor.lastrowid
            
            # Добавляем напоминание по умолчанию (за 3 дня)
            cursor.execute('''
                INSERT INTO reminders (user_id, subscription_id, days_before, is_active)
                VALUES (?, ?, ?, ?)
            ''', (user_id, subscription_id, 3, True))
            
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
                SELECT s.id, s.service_name, s.price, s.charge_day, s.next_charge_date,
                       r.days_before, r.is_active as reminder_active
                FROM subscriptions s
                LEFT JOIN reminders r ON s.id = r.subscription_id
                WHERE s.user_id = ? AND s.is_active = TRUE
                ORDER BY s.service_name
            ''', (user_id,))
            
            subscriptions = cursor.fetchall()
            conn.close()
            return subscriptions
            
        except Exception as e:
            print(f"Ошибка получения подписок: {e}")
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
            print(f"Ошибка удаления подписки: {e}")
            return False, "Ошибка при удалении подписки"
    
    def update_reminder_settings(self, user_id, subscription_id, days_before, is_active):
        """Обновление настроек напоминаний"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO reminders (user_id, subscription_id, days_before, is_active)
                VALUES (?, ?, ?, ?)
            ''', (user_id, subscription_id, days_before, is_active))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Ошибка обновления напоминаний: {e}")
            return False
    
    def get_upcoming_charges(self, days_ahead=7):
        """Получение предстоящих списаний"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Получаем подписки с предстоящими списаниями
            cursor.execute('''
                SELECT s.user_id, s.service_name, s.price, s.next_charge_date,
                       r.days_before, r.is_active
                FROM subscriptions s
                LEFT JOIN reminders r ON s.id = r.subscription_id
                WHERE s.is_active = TRUE AND r.is_active = TRUE
            ''')
            
            subscriptions = cursor.fetchall()
            conn.close()
            
            # Фильтруем по дате напоминания
            upcoming = []
            today = datetime.now().date()
            
            for sub in subscriptions:
                user_id, service_name, price, next_charge_date, days_before, is_active = sub
                
                try:
                    charge_date = datetime.strptime(next_charge_date, "%d.%m.%Y").date()
                    reminder_date = charge_date - timedelta(days=days_before)
                    
                    if today <= reminder_date <= today + timedelta(days=days_ahead):
                        upcoming.append({
                            'user_id': user_id,
                            'service_name': service_name,
                            'price': price,
                            'charge_date': next_charge_date,
                            'reminder_date': reminder_date.strftime("%d.%m.%Y"),
                            'days_before': days_before
                        })
                except ValueError:
                    continue
            
            return upcoming
            
        except Exception as e:
            print(f"Ошибка получения предстоящих списаний: {e}")
            return []

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
                [{'text': '🎯 Управление подписками'}],
                [{'text': '📚 О законе'}, {'text': '❓ Помощь'}],
                [{'text': '📋 Мои подписки'}, {'text': '⚙️ Настройки'}]
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
                {'text': subscriptions[i+1] if i+1 < len(subscriptions) else 'Еще...'}
            ]
            keyboard.append(row)
        
        # Сервисные кнопки
        keyboard.extend([
            [{'text': '➕ Своя подписка'}, {'text': '📋 Мои подписки'}],
            [{'text': '❌ Удалить подписку'}, {'text': '⚙️ Настройки напоминаний'}],
            [{'text': '🏠 Главное меню'}]
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
    def get_reminder_keyboard(cls):
        """Клавиатура настроек напоминаний"""
        return {
            'keyboard': [
                [{'text': '🔔 За 3 дня'}, {'text': '🔔 За 1 день'}],
                [{'text': '🔔 В день списания'}, {'text': '🔕 Выкл напоминания'}],
                [{'text': '🏠 Главное меню'}]
            ],
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
        # Словарь для хранения временных данных пользователей
        self.user_sessions = {}
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write('Bot is running with improved interface!'.encode('utf-8'))
    
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
        # Проверяем, есть ли активная сессия добавления подписки
        if chat_id in self.user_sessions and self.user_sessions[chat_id].get('adding_subscription'):
            return self._handle_subscription_flow(chat_id, text)
        
        # Проверяем сессию настройки напоминаний
        if chat_id in self.user_sessions and self.user_sessions[chat_id].get('setting_reminder'):
            return self._handle_reminder_setup(chat_id, text)
        
        # Обработка команды "Отмена"
        if text == '❌ Отмена':
            if chat_id in self.user_sessions:
                del self.user_sessions[chat_id]
            return self.process_message(chat_id, '🏠 Главное меню')
        
        if text == '/start' or text == '🏠 Главное меню':
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': '*🎯 Единый центр контроля подписок*\n\nВаш персональный помощник в управлении подписками\n\n*Выберите действие:*',
                'reply_markup': self.sub_manager.get_main_keyboard(),
                'parse_mode': 'Markdown'
            }
        
        elif text == '🎯 Управление подписками' or text == '/subs':
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': '*🎯 Управление подписками*\n\nВыберите популярную подписку или воспользуйтесь сервисными кнопками:',
                'reply_markup': self.sub_manager.get_subscriptions_keyboard(),
                'parse_mode': 'Markdown'
            }
        
        elif text == '📋 Мои подписки':
            subscriptions = self.db.get_user_subscriptions(chat_id)
            
            if subscriptions:
                total = sum(price for _, name, price, _, next_date, days_before, reminder_active in subscriptions)
                sub_list = []
                
                for sub_id, name, price, charge_day, next_date, days_before, reminder_active in subscriptions:
                    reminder_status = "🔔" if reminder_active else "🔕"
                    sub_list.append(f"{reminder_status} *{name}*: {price} руб\n   📅 След. списание: {next_date}")
                
                message = f"*📋 Ваши подписки*\n\n" + "\n\n".join(sub_list) + f"\n\n*💰 Итого в месяц:* {total} руб\n*📊 Всего подписок:* {len(subscriptions)}"
            else:
                message = "*📋 У вас пока нет активных подписок*\n\nДобавьте первую подписку через меню управления!"
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'reply_markup': self.sub_manager.get_main_keyboard()
            }
        
        elif text == '➕ Своя подписка':
            # Начинаем процесс добавления подписки
            self.user_sessions[chat_id] = {
                'adding_subscription': True,
                'step': 'name'
            }
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': '*➕ Добавление своей подписки*\n\n*Шаг 1 из 3*\nВведите название подписки:\n\n*Пример:*\nNetflix\nСпортзал\nЯндекс Такси',
                'parse_mode': 'Markdown',
                'reply_markup': self.sub_manager.get_cancel_keyboard()
            }
        
        elif text in self.sub_manager.POPULAR_SUBSCRIPTIONS:
            # Показываем информацию о подписке
            info = self.sub_manager.get_subscription_info(text)
            keyboard = {
                'keyboard': [
                    [{'text': f'✅ Добавить {text}'}],
                    [{'text': '🔙 К подпискам'}, {'text': '🏠 Главное меню'}]
                ],
                'resize_keyboard': True
            }
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': f'*{text}*\n\n*💰 Стоимость:* {info["price"]} руб/мес\n*📝 Описание:* {info["description"]}\n\nДобавить для отслеживания?',
                'reply_markup': keyboard,
                'parse_mode': 'Markdown'
            }
        
        elif text.startswith('✅ Добавить '):
            # Обработка добавления популярной подписки
            service_name = text.replace('✅ Добавить ', '')
            info = self.sub_manager.get_subscription_info(service_name)
            
            # Вычисляем дату следующего списания (1 число следующего месяца)
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
                1,  # Списание 1 числа
                next_charge_date
            )
            
            response_text = f'*✅ Подписка добавлена!*\n\n*📺 Название:* {service_name}\n*💰 Стоимость:* {info["price"]} руб/мес\n*📅 Следующее списание:* {next_charge_date}\n\n🔔 *Напоминание настроено за 3 дня до списания*'
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': response_text,
                'parse_mode': 'Markdown',
                'reply_markup': self.sub_manager.get_main_keyboard()
            }
        
        elif text == '❌ Удалить подписку':
            subscriptions = self.db.get_user_subscriptions(chat_id)
            
            if subscriptions:
                keyboard = []
                for sub_id, name, price, charge_day, next_date, days_before, reminder_active in subscriptions:
                    keyboard.append([{'text': f'❌ Удалить {name}'}])
                keyboard.append([{'text': '🔙 К подпискам'}, {'text': '🏠 Главное меню'}])
                
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': '*❌ Удаление подписки*\n\nВыберите подписку для удаления:',
                    'reply_markup': {'keyboard': keyboard, 'resize_keyboard': True},
                    'parse_mode': 'Markdown'
                }
            else:
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': 'У вас нет подписок для удаления.',
                    'reply_markup': self.sub_manager.get_main_keyboard()
                }
        
        elif text.startswith('❌ Удалить '):
            # Обработка удаления конкретной подписки
            service_name = text.replace('❌ Удалить ', '')
            success, message = self.db.delete_subscription(chat_id, service_name)
            
            response_text = f'*✅ {message}*\n\nПодписка: {service_name}' if success else f'*❌ {message}*'
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': response_text,
                'parse_mode': 'Markdown',
                'reply_markup': self.sub_manager.get_main_keyboard()
            }
        
        elif text == '⚙️ Настройки' or text == '⚙️ Настройки напоминаний':
            subscriptions = self.db.get_user_subscriptions(chat_id)
            
            if subscriptions:
                keyboard = []
                for sub_id, name, price, charge_day, next_date, days_before, reminder_active in subscriptions:
                    status = "🔔" if reminder_active else "🔕"
                    keyboard.append([{'text': f'⚙️ {status} {name}'}])
                keyboard.append([{'text': '🔙 Назад'}, {'text': '🏠 Главное меню'}])
                
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': '*⚙️ Настройки напоминаний*\n\nВыберите подписку для настройки напоминаний:',
                    'reply_markup': {'keyboard': keyboard, 'resize_keyboard': True},
                    'parse_mode': 'Markdown'
                }
            else:
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': 'У вас нет подписок для настройки.',
                    'reply_markup': self.sub_manager.get_main_keyboard()
                }
        
        elif text.startswith('⚙️ '):
            # Настройка напоминаний для конкретной подписки
            parts = text.split(' ', 2)
            if len(parts) >= 3:
                service_name = parts[2]
                subscriptions = self.db.get_user_subscriptions(chat_id)
                
                for sub in subscriptions:
                    if sub[1] == service_name:
                        self.user_sessions[chat_id] = {
                            'setting_reminder': True,
                            'subscription_id': sub[0],
                            'service_name': service_name,
                            'current_days_before': sub[5],
                            'current_active': sub[6]
                        }
                        
                        status = "включены" if sub[6] else "выключены"
                        return {
                            'method': 'sendMessage',
                            'chat_id': chat_id,
                            'text': f'*⚙️ Настройка напоминаний для "{service_name}"*\n\nТекущие настройки: напоминание за *{sub[5]}* дней\nСтатус: *{status}*\n\nВыберите новые настройки:',
                            'parse_mode': 'Markdown',
                            'reply_markup': self.sub_manager.get_reminder_keyboard()
                        }
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': 'Подписка не найдена.',
                'reply_markup': self.sub_manager.get_main_keyboard()
            }
        
        elif text in ['🔙 К подпискам', '🔙 Назад', 'Еще...']:
            return self.process_message(chat_id, '🎯 Управление подписками')
        
        elif text == '📚 О законе' or text == '/laws':
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': '*📚 Федеральный закон № 376-ФЗ*\n\n*С 15 октября 2025 года:*\n\n• ✅ Сервисы обязаны получать ваше прямое согласие на каждое списание\n• ❌ Запрещено автоматическое продление без подтверждения\n• 📝 Отмена подписки должна быть не сложнее, чем оформление\n\n*🛡️ Ваши права защищены!*',
                'parse_mode': 'Markdown',
                'reply_markup': self.sub_manager.get_main_keyboard()
            }
        
        elif text == '❓ Помощь' or text == '/help':
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': '*❓ Помощь и поддержка*\n\n*Частые вопросы:*\n\n• 🤔 Как добавить подписку? - Используйте меню "Управление подписками"\n• 🗑️ Как удалить подписку? - Используйте "Удалить подписку"\n• 🔔 Как настроить напоминания? - Используйте "Настройки напоминаний"\n• 📅 Как изменить дату списания? - Удалите и добавьте подписку заново\n\n*💬 Напишите ваш вопрос - помогу разобраться!*',
                'parse_mode': 'Markdown',
                'reply_markup': self.sub_manager.get_main_keyboard()
            }
        
        else:
            # Если пользователь ввел произвольный текст (например, "Спортзал")
            # Предлагаем добавить как свою подписку
            self.user_sessions[chat_id] = {
                'adding_subscription': True,
                'step': 'name',
                'name': text  # Уже введенное название
            }
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': f'*➕ Добавление подписки*\n\nВы ввели: *{text}*\n\n*Шаг 2 из 3*\nВведите стоимость подписки в рублях:\n\n*Пример:*\n599\n199\n2499',
                'parse_mode': 'Markdown',
                'reply_markup': self.sub_manager.get_cancel_keyboard()
            }
    
    def _handle_subscription_flow(self, chat_id, text):
        """Обработка многошагового добавления подписки"""
        session = self.user_sessions[chat_id]
        
        if text == '❌ Отмена':
            # Отменяем процесс добавления
            del self.user_sessions[chat_id]
            return self.process_message(chat_id, '🏠 Главное меню')
        
        if session['step'] == 'name':
            # Сохраняем название и запрашиваем стоимость
            session['name'] = text
            session['step'] = 'price'
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': '*➕ Добавление своей подписки*\n\n*Шаг 2 из 3*\nВведите стоимость подписки в рублях:\n\n*Пример:*\n599\n199\n2499',
                'parse_mode': 'Markdown',
                'reply_markup': self.sub_manager.get_cancel_keyboard()
            }
        
        elif session['step'] == 'price':
            # Сохраняем стоимость и запрашиваем дату следующего списания
            try:
                price = float(text)
                if price <= 0:
                    raise ValueError("Цена должна быть положительной")
                    
                session['price'] = price
                session['step'] = 'date'
                
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': f'*➕ Добавление своей подписки*\n\n*Шаг 3 из 3*\nКогда следующее списание?\n\nУкажите дату в формате *ДД.ММ.ГГГГ*:\n*Пример:*\n15.06.2024\n25.12.2024\n\nИли введите число месяца (1-31) для ежемесячного списания:',
                    'parse_mode': 'Markdown',
                    'reply_markup': self.sub_manager.get_cancel_keyboard()
                }
            except ValueError:
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': '❌ Неверный формат цены. Введите положительное число:\n\n*Пример:* 599',
                    'parse_mode': 'Markdown',
                    'reply_markup': self.sub_manager.get_cancel_keyboard()
                }
        
        elif session['step'] == 'date':
            # Обрабатываем дату и сохраняем подписку
            try:
                # Пытаемся распарсить дату
                if re.match(r'^\d{1,2}\.\d{1,2}\.\d{4}$', text):  # Формат 15.06.2024
                    charge_date = datetime.strptime(text, "%d.%m.%Y")
                    next_charge_date = charge_date.strftime("%d.%m.%Y")
                    charge_day = charge_date.day
                elif re.match(r'^\d{1,2}$', text):  # Просто число месяца
                    day = int(text)
                    if 1 <= day <= 31:
                        # Вычисляем дату следующего списания
                        today = datetime.now()
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
                
                # Сохраняем подписку в базу
                success, message = self.db.add_subscription(
                    chat_id, 
                    session['name'], 
                    session['price'], 
                    charge_day,
                    next_charge_date
                )
                
                # Очищаем сессию
                del self.user_sessions[chat_id]
                
                if success:
                    response_text = f'*✅ Подписка добавлена!*\n\n*📺 Название:* {session["name"]}\n*💰 Стоимость:* {session["price"]} руб/мес\n*📅 Следующее списание:* {next_charge_date}\n*🔢 День списания:* {charge_day} число\n\n🔔 *Напоминание настроено за 3 дня до списания*'
                else:
                    response_text = f'*❌ Ошибка:* {message}'
                
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
                    'text': f'❌ {str(e)}\n\nВведите дату в формате *ДД.ММ.ГГГГ* или число от 1 до 31:\n*Пример:*\n15.06.2024\n25',
                    'parse_mode': 'Markdown',
                    'reply_markup': self.sub_manager.get_cancel_keyboard()
                }
    
    def _handle_reminder_setup(self, chat_id, text):
        """Обработка настройки напоминаний"""
        session = self.user_sessions[chat_id]
        
        if text == '🔔 За 3 дня':
            days_before = 3
            is_active = True
        elif text == '🔔 За 1 день':
            days_before = 1
            is_active = True
        elif text == '🔔 В день списания':
            days_before = 0
            is_active = True
        elif text == '🔕 Выкл напоминания':
            days_before = session['current_days_before']
            is_active = False
        else:
            # Неизвестная команда - возвращаем в главное меню
            del self.user_sessions[chat_id]
            return self.process_message(chat_id, '🏠 Главное меню')
        
        # Сохраняем настройки
        success = self.db.update_reminder_settings(
            chat_id,
            session['subscription_id'],
            days_before,
            is_active
        )
        
        # Очищаем сессию
        del self.user_sessions[chat_id]
        
        if success:
            status = "включены" if is_active else "выключены"
            days_text = "в день списания" if days_before == 0 else f"за {days_before} дня"
            response_text = f'*✅ Настройки обновлены!*\n\n*📺 Подписка:* {session["service_name"]}\n*🔔 Напоминания:* {status}\n*⏰ Время:* {days_text}'
        else:
            response_text = '*❌ Ошибка при сохранении настроек*'
        
        return {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': response_text,
            'parse_mode': 'Markdown',
            'reply_markup': self.sub_manager.get_main_keyboard()
        }

# Функция для отправки напоминаний (должна запускаться отдельно по расписанию)
def send_reminders(bot_handler):
    """Функция для отправки напоминаний о предстоящих списаниях"""
    upcoming = bot_handler.db.get_upcoming_charges()
    
    for reminder in upcoming:
        message = f'🔔 *Напоминание о подписке!*\n\nЧерез {reminder["days_before"]} дня ({reminder["charge_date"]}) спишется оплата:\n*📺 {reminder["service_name"]}* - {reminder["price"]} руб\n\nНе забудьте проверить баланс! 💰'
        
        # Здесь должен быть код отправки сообщения через Telegram API
        # Для демонстрации просто выводим в консоль
        print(f"Reminder for user {reminder['user_id']}: {message}")

handler = BotHandler
