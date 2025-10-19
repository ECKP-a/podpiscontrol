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
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    days_before INTEGER DEFAULT 3,
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
    
    def get_notification_settings(self, user_id):
        """Получение настроек уведомлений"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT days_before, is_active FROM notifications 
                WHERE user_id = ?
            ''', (user_id,))
            
            settings = cursor.fetchone()
            conn.close()
            
            if settings:
                return {'days_before': settings[0], 'is_active': bool(settings[1])}
            else:
                default_settings = {'days_before': 3, 'is_active': True}
                self.set_notification_settings(user_id, default_settings)
                return default_settings
                
        except Exception as e:
            print(f"Ошибка получения настроек: {e}")
            return {'days_before': 3, 'is_active': True}
    
    def set_notification_settings(self, user_id, settings):
        """Сохранение настроек уведомлений"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO notifications (user_id, days_before, is_active)
                VALUES (?, ?, ?)
            ''', (user_id, settings['days_before'], settings['is_active']))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")
            return False

class SubscriptionManager:
    """Менеджер популярных подписок"""
    
    POPULAR_SUBSCRIPTIONS = {
        'Яндекс Плюс': 399,
        'СберПрайм': 299,
        'Ozon Premium': 199,
        'ВБ Клуб': 199,
        'VK Музыка': 199,
        'Яндекс Музыка': 169,
        'IVI': 399,
        'START': 299,
        'More.tv': 299,
        'Wink': 349,
        'ВТБ Плюс': 199,
        'МТС Premium': 299
    }
    
    @classmethod
    def get_main_keyboard(cls):
        """Главная клавиатура"""
        return {
            'keyboard': [
                [{'text': '📋 Мои подписки'}, {'text': '💰 Аналитика'}],
                [{'text': '🔔 Уведомления'}, {'text': '⚖️ О законе'}],
                [{'text': '➕ Добавить подписку'}]
            ],
            'resize_keyboard': True
        }
    
    @classmethod
    def get_subscriptions_keyboard(cls):
        """Клавиатура выбора подписок"""
        subscriptions = list(cls.POPULAR_SUBSCRIPTIONS.keys())
        keyboard = []
        
        # Группируем по 2 подписки в ряд
        for i in range(0, len(subscriptions), 2):
            if i + 1 < len(subscriptions):
                keyboard.append([{'text': subscriptions[i]}, {'text': subscriptions[i+1]}])
            else:
                keyboard.append([{'text': subscriptions[i]}])
        
        keyboard.append([{'text': '✍️ Ввести свою подписку'}])
        keyboard.append([{'text': '🔙 Главное меню'}])
        
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
    def get_notifications_keyboard(cls):
        """Клавиатура настроек уведомлений"""
        return {
            'keyboard': [
                [{'text': '🔔 За 3 дня'}, {'text': '🔔 За 1 день'}],
                [{'text': '🔔 За 7 дней'}, {'text': '🔕 Выключить'}],
                [{'text': '🔙 Назад'}]
            ],
            'resize_keyboard': True
        }
    
    @classmethod
    def get_back_keyboard(cls):
        """Клавиатура назад"""
        return {
            'keyboard': [[{'text': '🔙 Назад'}]],
            'resize_keyboard': True
        }
    
    @classmethod
    def get_subscription_price(cls, service_name):
        """Получение цены подписки"""
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
        
        # Обработка команды отмены/назад
        if text in ['❌ Отмена', '🔙 Назад', '🔙 Главное меню', '/start']:
            if chat_id in self.user_sessions:
                del self.user_sessions[chat_id]
            return self._show_main_menu(chat_id)
        
        # Обработка текстовых команд (для меню бота)
        if text == '/start':
            return self._show_main_menu(chat_id)
        
        elif text == '/subs':
            return self._show_subscriptions_menu(chat_id)
        
        elif text == '/help':
            return self._show_help(chat_id)
        
        elif text == '/laws':
            return self._show_laws(chat_id)
        
        elif text == '/sets':
            return self._show_notifications_settings(chat_id)
        
        elif text == '/unsub':
            return self._show_unsubscribe(chat_id)
        
        # Обработка кнопок главного меню
        elif text == '📋 Мои подписки':
            return self._show_my_subscriptions(chat_id)
        
        elif text == '➕ Добавить подписку':
            return self._show_subscriptions_menu(chat_id)
        
        elif text == '🔔 Уведомления':
            return self._show_notifications_settings(chat_id)
        
        elif text == '💰 Аналитика':
            return self._show_analytics(chat_id)
        
        elif text == '⚖️ О законе':
            return self._show_laws(chat_id)
        
        # Обработка меню подписок
        elif text == '✍️ Ввести свою подписку':
            return self._start_custom_subscription(chat_id)
        
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
        
        # Обработка настроек уведомлений
        elif text.startswith('🔔 ') or text == '🔕 Выключить':
            return self._handle_notification_setting(chat_id, text)
        
        else:
            # Неизвестная команда - показываем главное меню
            return self._show_main_menu(chat_id)
    
    def _show_main_menu(self, chat_id):
        """Главное меню"""
        return {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': """🎯 *Единый центр контроля подписок*

*Ваш надёжный помощник в управлении подписками*

⚖️ *Обеспечиваем соблюдение ФЗ-376 от 15.10.2025*
🔔 *Умные уведомления о списаниях*
📊 *Полная аналитика расходов*

Выберите действие:""",
            'reply_markup': self.sub_manager.get_main_keyboard(),
            'parse_mode': 'Markdown'
        }
    
    def _show_subscriptions_menu(self, chat_id):
        """Меню выбора подписок"""
        return {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': '📋 *Добавление подписки*\n\nВыберите популярную подписку или введите свою:',
            'reply_markup': self.sub_manager.get_subscriptions_keyboard(),
            'parse_mode': 'Markdown'
        }
    
    def _show_my_subscriptions(self, chat_id):
        """Показ текущих подписок пользователя"""
        subscriptions = self.db.get_user_subscriptions(chat_id)
        
        if subscriptions:
            total = sum(price for _, price, _, _ in subscriptions)
            sub_list = "\n".join([
                f"• {name}: {price} руб (списание {next_date})"
                for name, price, day, next_date in subscriptions
            ])
            
            message = f"*📋 Ваши подписки*\n\n{sub_list}\n\n*💰 Итого в месяц:* {total} руб\n*📊 Всего подписок:* {len(subscriptions)}"
        else:
            message = "*📋 У вас пока нет активных подписок*\n\nНажмите '➕ Добавить подписку' чтобы добавить первую подписку!"
        
        return {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'Markdown',
            'reply_markup': self.sub_manager.get_main_keyboard()
        }
    
    def _show_subscription_info(self, chat_id, service_name):
        """Информация о популярной подписке"""
        price = self.sub_manager.get_subscription_price(service_name)
        keyboard = {
            'keyboard': [
                [{'text': f'✅ {service_name}'}],
                [{'text': '🔙 Назад'}]
            ],
            'resize_keyboard': True
        }
        
        return {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': f'*{service_name}*\n\n💳 *Стоимость:* {price} руб/мес\n\nДобавить для отслеживания?',
            'reply_markup': keyboard,
            'parse_mode': 'Markdown'
        }
    
    def _add_popular_subscription(self, chat_id, service_name):
        """Добавление популярной подписки"""
        price = self.sub_manager.get_subscription_price(service_name)
        
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
            price, 
            1,
            next_charge_date
        )
        
        if success:
            settings = self.db.get_notification_settings(chat_id)
            days_text = "в день списания" if settings['days_before'] == 0 else f"за {settings['days_before']} дня"
            
            response_text = f"""✅ *Подписка добавлена!*

📺 *{service_name}*
💳 {price} руб/мес
📅 Следующее списание: {next_charge_date}

🔔 *Уведомление настроено {days_text}*"""
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
            'text': '✍️ *Добавление своей подписки*\n\nВведите название подписки:',
            'parse_mode': 'Markdown',
            'reply_markup': self.sub_manager.get_cancel_keyboard()
        }
    
    def _handle_subscription_flow(self, chat_id, text):
        """Обработка добавления своей подписки"""
        session = self.user_sessions[chat_id]
        
        if session['step'] == 'name':
            if not text or text.strip() == '':
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': '❌ Название не может быть пустым. Введите название подписки:',
                    'parse_mode': 'Markdown',
                    'reply_markup': self.sub_manager.get_cancel_keyboard()
                }
            
            session['name'] = text.strip()
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
                clean_text = re.sub(r'[^\d,.]', '', text.replace(',', '.'))
                if not clean_text:
                    raise ValueError("Введите стоимость")
                    
                price = float(clean_text)
                
                if price <= 0:
                    raise ValueError("Цена должна быть положительной")
                
                session['price'] = price
                session['step'] = 'date'
                
                current_year = datetime.now().year
                next_year = current_year + 1
                
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': f"""📅 *Когда следующее списание?*

*Формат ввода:*
• **ДД.ММ** - если списание в {current_year} году
• **ДД.ММ.ГГ** - если списание в {next_year} году

*Примеры:*
15.06 - 15 июня {current_year}
25.12.26 - 25 декабря {next_year}

Введите дату следующего списания:""",
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
                current_year = today.year
                
                # Обработка формата ДД.ММ (текущий год)
                if re.match(r'^\d{1,2}\.\d{1,2}$', text):
                    day, month = map(int, text.split('.'))
                    charge_date = today.replace(month=month, day=day)
                    
                    # Если дата уже прошла в этом году, берем следующий год
                    if charge_date < today:
                        charge_date = charge_date.replace(year=current_year + 1)
                    
                    next_charge_date = charge_date.strftime("%d.%m.%Y")
                    charge_day = charge_date.day
                
                # Обработка формата ДД.ММ.ГГ (с годом)
                elif re.match(r'^\d{1,2}\.\d{1,2}\.\d{2}$', text):
                    day, month, year = map(int, text.split('.'))
                    # Преобразуем год из двух цифр в четыре
                    full_year = 2000 + year if year < 100 else year
                    charge_date = today.replace(year=full_year, month=month, day=day)
                    next_charge_date = charge_date.strftime("%d.%m.%Y")
                    charge_day = charge_date.day
                
                else:
                    raise ValueError("Неверный формат даты")
                
                # Проверяем что дата в будущем
                if charge_date <= today:
                    raise ValueError("Дата должна быть в будущем")
                
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
                    settings = self.db.get_notification_settings(chat_id)
                    days_text = "в день списания" if settings['days_before'] == 0 else f"за {settings['days_before']} дня"
                    
                    response_text = f"""✅ *Подписка добавлена!*

📺 *{session["name"]}*
💳 {session["price"]} руб/мес
📅 Следующее списание: {next_charge_date}

🔔 *Уведомление настроено {days_text}*"""
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
                error_msg = str(e)
                if "Неверный формат даты" in error_msg:
                    current_year = datetime.now().year
                    return {
                        'method': 'sendMessage',
                        'chat_id': chat_id,
                        'text': f"""❌ Неверный формат даты

*Правильный формат:*
• **ДД.ММ** - для {current_year} года
• **ДД.ММ.ГГ** - для следующего года

*Пример:*
15.06 - 15 июня
25.12.26 - 25 декабря 2026

Введите дату:""",
                        'parse_mode': 'Markdown',
                        'reply_markup': self.sub_manager.get_cancel_keyboard()
                    }
                else:
                    return {
                        'method': 'sendMessage',
                        'chat_id': chat_id,
                        'text': f'❌ {error_msg}',
                        'parse_mode': 'Markdown',
                        'reply_markup': self.sub_manager.get_cancel_keyboard()
                    }
    
    def _show_notifications_settings(self, chat_id):
        """Настройка уведомлений"""
        settings = self.db.get_notification_settings(chat_id)
        
        status = "включены" if settings['is_active'] else "выключены"
        days_text = "в день списания" if settings['days_before'] == 0 else f"за {settings['days_before']} дня"
        
        return {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': f"""🔔 *Настройка уведомлений*

Текущие настройки:
• Статус: {status}
• Время напоминания: {days_text}

Выберите новые настройки:""",
            'parse_mode': 'Markdown',
            'reply_markup': self.sub_manager.get_notifications_keyboard()
        }
    
    def _handle_notification_setting(self, chat_id, text):
        """Обработка изменения настроек уведомлений"""
        settings = self.db.get_notification_settings(chat_id)
        
        if text == '🔔 За 3 дня':
            settings.update({'days_before': 3, 'is_active': True})
        elif text == '🔔 За 1 день':
            settings.update({'days_before': 1, 'is_active': True})
        elif text == '🔔 За 7 дней':
            settings.update({'days_before': 7, 'is_active': True})
        elif text == '🔕 Выключить':
            settings.update({'is_active': False})
        else:
            return self._show_notifications_settings(chat_id)
        
        success = self.db.set_notification_settings(chat_id, settings)
        
        if success:
            status = "включены" if settings['is_active'] else "выключены"
            days_text = "в день списания" if settings['days_before'] == 0 else f"за {settings['days_before']} дня"
            
            response_text = f"""✅ *Настройки сохранены!*

• Статус: {status}
• Время напоминания: {days_text}"""
        else:
            response_text = '❌ *Ошибка сохранения настроек*'
        
        return {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': response_text,
            'parse_mode': 'Markdown',
            'reply_markup': self.sub_manager.get_main_keyboard()
        }
    
    def _show_analytics(self, chat_id):
        """Показывает аналитику по подпискам"""
        subscriptions = self.db.get_user_subscriptions(chat_id)
        
        if not subscriptions:
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': 'У вас пока нет подписок для анализа.',
                'reply_markup': self.sub_manager.get_main_keyboard()
            }
        
        total_monthly = sum(price for _, price, _, _ in subscriptions)
        total_yearly = total_monthly * 12
        
        expensive_subs = sorted(subscriptions, key=lambda x: x[1], reverse=True)[:3]
        
        analytics_text = f"""💰 *Финансовая аналитика*

*Общие расходы:*
💳 В месяц: {total_monthly} руб
📈 В год: {total_yearly} руб

*Самые дорогие подписки:*
"""
        
        for i, (name, price, day, next_date) in enumerate(expensive_subs, 1):
            analytics_text += f"{i}. {name} - {price} руб/мес\n"
        
        analytics_text += f"\n💡 *Совет:* Проверяйте подписки раз в месяц"
        
        return {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': analytics_text,
            'parse_mode': 'Markdown',
            'reply_markup': self.sub_manager.get_main_keyboard()
        }
    
    def _show_help(self, chat_id):
        """Помощь и консультация"""
        return {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': """❓ *Помощь и консультация*

*Частые вопросы:*

• Как добавить подписку?
Нажмите "➕ Добавить подписку" и выберите из списка или введите свою

• Как отменить подписку?
Используйте команду /unsub в меню бота

• Что делать если списали деньги без согласия?
Обратитесь в поддержку сервиса и ссылайтесь на ФЗ-376 от 15.10.2025

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
            'text': """⚖️ *Федеральный закон № 376-ФЗ от 15.10.2025*

*Ключевые положения:*

• Запрет списаний с удаленных карт
• Обязанность приема отказа от платежных средств  
• Защита прав потребителей при онлайн-подписках

*Вступает в силу:* 1 марта 2026 года

*Наш сервис помогает контролировать подписки в соответствии с законодательством.*""",
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