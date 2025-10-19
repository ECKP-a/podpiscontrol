from http.server import BaseHTTPRequestHandler
import json
import sqlite3
import re
from datetime import datetime, timedelta
import time
from urllib.request import urlopen, Request
from urllib.parse import urlencode
import ssl

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
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS support_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    user_message TEXT,
                    admin_response TEXT,
                    status TEXT DEFAULT 'new',
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
                SELECT id, service_name, price, charge_day, next_charge_date 
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
    
    def update_subscription_date(self, user_id, subscription_id, next_charge_date):
        """Обновление даты списания подписки"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE subscriptions 
                SET next_charge_date = ?
                WHERE id = ? AND user_id = ? AND is_active = TRUE
            ''', (next_charge_date, subscription_id, user_id))
            
            conn.commit()
            conn.close()
            return True, "Дата списания обновлена"
            
        except Exception as e:
            print(f"Ошибка обновления даты: {e}")
            return False, "Ошибка при обновлении даты"
    
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
    
    def add_support_request(self, user_id, message):
        """Добавление обращения в поддержку"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO support_requests (user_id, user_message)
                VALUES (?, ?)
            ''', (user_id, message))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Ошибка сохранения обращения: {e}")
            return False

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
        'ВТБ Плюс': {'price': 199, 'description': 'Премиум подписка ВТБ'},
        'МТС Premium': {'price': 299, 'description': 'Кино, музыка, скидки'}
    }
    
    @classmethod
    def get_main_keyboard(cls):
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
        subscriptions = list(cls.POPULAR_SUBSCRIPTIONS.keys())
        keyboard = []
        
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
        return {
            'keyboard': [[{'text': '❌ Отмена'}]],
            'resize_keyboard': True
        }
    
    @classmethod
    def get_notifications_keyboard(cls):
        return {
            'keyboard': [
                [{'text': '🔔 За 3 дня'}, {'text': '🔔 За 1 день'}],
                [{'text': '🔔 За 7 дней'}, {'text': '🔕 Выключить'}],
                [{'text': '🔙 Назад'}]
            ],
            'resize_keyboard': True
        }
    
    @classmethod
    def get_subscription_info(cls, service_name):
        return cls.POPULAR_SUBSCRIPTIONS.get(service_name)

class BotHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.db = DatabaseManager()
        self.sub_manager = SubscriptionManager()
        self.user_sessions = {}
        self.telegram_token = "8459093402:AAG8iTjrqDuv3OmEkF4aLpyiZzZrsOqC_4o"
        self.telegram_url = f"https://api.telegram.org/bot{self.telegram_token}/"
        super().__init__(*args, **kwargs)
    
    def _send_telegram_message(self, chat_id, text, reply_markup=None):
        """Отправка сообщения через Telegram API"""
        try:
            payload = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'Markdown'
            }
            
            if reply_markup:
                payload['reply_markup'] = json.dumps(reply_markup)
            
            data = json.dumps(payload).encode('utf-8')
            headers = {'Content-Type': 'application/json'}
            
            request = Request(
                f"{self.telegram_url}sendMessage",
                data=data,
                headers=headers
            )
            
            context = ssl._create_unverified_context()
            response = urlopen(request, context=context, timeout=10)
            response.read()
            
            print(f"✅ Сообщение отправлено пользователю {chat_id}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при отправке в Telegram: {e}")
            return False
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write('🎯 Единый центр контроля подписок - работает!'.encode('utf-8'))
    
    def do_POST(self):
        """Обработка входящих сообщений от Telegram"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            update = json.loads(post_data)
            
            print(f"📨 Получено сообщение: {update}")
            
            if 'message' in update:
                chat_id = update['message']['chat']['id']
                text = update['message'].get('text', '').strip()
                
                # Обрабатываем сообщение
                self.process_message(chat_id, text)
                
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
                
        except Exception as e:
            print(f'❌ Error processing message: {e}')
            self.send_response(200)
            self.end_headers()
    
    def process_message(self, chat_id, text):
        """Основная логика обработки сообщений"""
        print(f"🔍 Обработка сообщения от {chat_id}: '{text}'")
        
        # ВАЖНО: Сначала проверяем активные сессии
        if chat_id in self.user_sessions:
            session = self.user_sessions[chat_id]
            print(f"🎯 Активная сессия: {session}")
            
            if session.get('adding_subscription'):
                print("🔄 Обработка добавления подписки")
                self._handle_subscription_flow(chat_id, text)
                return
            elif session.get('waiting_support'):
                print("🔄 Обработка обращения в поддержку")
                self._handle_support_request(chat_id, text)
                return
            elif session.get('changing_date'):
                print("🔄 Обработка изменения даты")
                self._handle_date_change(chat_id, text)
                return
        
        # Затем обрабатываем команды
        if text in ['❌ Отмена', '🔙 Назад', '🔙 Главное меню', '/start']:
            if chat_id in self.user_sessions:
                del self.user_sessions[chat_id]
            self._show_main_menu(chat_id)
            return
        
        # Обработка команд
        if text == '/start':
            self._show_main_menu(chat_id)
        elif text == '/subs':
            self._show_subscriptions_menu(chat_id)
        elif text == '/help':
            self._start_support_request(chat_id)
        elif text == '/laws':
            self._show_laws(chat_id)
        elif text == '/sets':
            self._show_notifications_settings(chat_id)
        elif text == '/unsub':
            self._show_unsubscribe(chat_id)
        elif text == '📋 Мои подписки':
            self._show_my_subscriptions(chat_id)
        elif text == '➕ Добавить подписку':
            self._show_subscriptions_menu(chat_id)
        elif text == '🔔 Уведомления':
            self._show_notifications_settings(chat_id)
        elif text == '💰 Аналитика':
            self._show_analytics(chat_id)
        elif text == '⚖️ О законе':
            self._show_laws(chat_id)
        elif text == '✍️ Ввести свою подписку':
            self._start_custom_subscription(chat_id)
        elif text in self.sub_manager.POPULAR_SUBSCRIPTIONS:
            self._show_subscription_info(chat_id, text)
        elif text.startswith('✅ '):
            service_name = text.replace('✅ ', '')
            self._add_popular_subscription(chat_id, service_name)
        elif text.startswith('📅 Изменить дату '):
            subscription_id = text.replace('📅 Изменить дату ', '')
            self._start_date_change(chat_id, subscription_id)
        elif text.startswith('❌ Удалить '):
            service_name = text.replace('❌ Удалить ', '')
            self._delete_subscription(chat_id, service_name)
        elif text.startswith('🔔 ') or text == '🔕 Выключить':
            self._handle_notification_setting(chat_id, text)
        else:
            # Если неизвестная команда - показываем главное меню
            self._show_main_menu(chat_id)
    
    def _start_support_request(self, chat_id):
        """Начало обращения в поддержку"""
        print(f"🎯 Начало обращения в поддержку для {chat_id}")
        self.user_sessions[chat_id] = {
            'waiting_support': True
        }
        
        self._send_telegram_message(
            chat_id,
            """💬 *Обращение в поддержку*

Опишите вашу проблему или вопрос, и мы обязательно вам поможем!

Напишите ваше сообщение:""",
            self.sub_manager.get_cancel_keyboard()
        )
    
    def _handle_support_request(self, chat_id, text):
        """Обработка обращения в поддержку"""
        print(f"📝 Обработка обращения: {text}")
        
        if text == '❌ Отмена':
            del self.user_sessions[chat_id]
            self._show_main_menu(chat_id)
            return
        
        success = self.db.add_support_request(chat_id, text)
        
        del self.user_sessions[chat_id]
        
        if success:
            response_text = """✅ *Ваше обращение принято!*

Мы получили ваше сообщение и в ближайшее время с вами свяжется наш специалист.

💡 *Обычно мы отвечаем в течение 24 часов.*
📧 *Для срочных вопросов: support@podpiski-control.ru*"""
        else:
            response_text = "❌ *Произошла ошибка при отправке обращения*"
        
        self._send_telegram_message(
            chat_id,
            response_text,
            self.sub_manager.get_main_keyboard()
        )
    
    def _start_custom_subscription(self, chat_id):
        """Начало добавления своей подписки"""
        print(f"🎯 Начало добавления своей подписки для {chat_id}")
        self.user_sessions[chat_id] = {
            'adding_subscription': True,
            'step': 'name'
        }
        
        self._send_telegram_message(
            chat_id,
            '✍️ *Добавление своей подписки*\n\nВведите название подписки:',
            self.sub_manager.get_cancel_keyboard()
        )
    
    def _handle_subscription_flow(self, chat_id, text):
        """Обработка добавления своей подписки"""
        session = self.user_sessions[chat_id]
        print(f"🔄 Шаг {session['step']}: {text}")
        
        if text == '❌ Отмена':
            del self.user_sessions[chat_id]
            self._show_main_menu(chat_id)
            return
        
        if session['step'] == 'name':
            if not text or text.strip() == '':
                self._send_telegram_message(
                    chat_id,
                    '❌ Название не может быть пустым. Введите название подписки:',
                    self.sub_manager.get_cancel_keyboard()
                )
                return
            
            session['name'] = text.strip()
            session['step'] = 'price'
            
            self._send_telegram_message(
                chat_id,
                '💳 Введите стоимость подписки в рублях:',
                self.sub_manager.get_cancel_keyboard()
            )
        
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
                
                self._send_telegram_message(
                    chat_id,
                    f"""📅 *Когда следующее списание?*

*Формат ввода:*
• **ДД.ММ** - если списание в {current_year} году
• **ДД.ММ.ГГ** - если списание в следующем году

*Примеры:*
15.06 - 15 июня {current_year}
25.12.25 - 25 декабря {current_year + 1}

Введите дату следующего списания:""",
                    self.sub_manager.get_cancel_keyboard()
                )
                
            except (ValueError, TypeError):
                self._send_telegram_message(
                    chat_id,
                    '❌ Неверный формат цены. Введите число:',
                    self.sub_manager.get_cancel_keyboard()
                )
        
        elif session['step'] == 'date':
            try:
                today = datetime.now()
                current_year = today.year
                
                if re.match(r'^\d{1,2}\.\d{1,2}$', text):
                    day, month = map(int, text.split('.'))
                    charge_date = today.replace(month=month, day=day, year=current_year)
                    
                    if charge_date < today:
                        charge_date = charge_date.replace(year=current_year + 1)
                    
                    next_charge_date = charge_date.strftime("%d.%m.%Y")
                    charge_day = charge_date.day
                
                elif re.match(r'^\d{1,2}\.\d{1,2}\.\d{2}$', text):
                    day, month, year = map(int, text.split('.'))
                    full_year = 2000 + year if year < 100 else year
                    charge_date = today.replace(year=full_year, month=month, day=day)
                    next_charge_date = charge_date.strftime("%d.%m.%Y")
                    charge_day = charge_date.day
                
                else:
                    raise ValueError("Неверный формат даты")
                
                if charge_date <= today:
                    raise ValueError("Дата должна быть в будущем")
                
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

🔔 *Уведомление настроено {days_text}*

💡 *Вы можете изменить дату списания в разделе "Мои подписки"*"""
                else:
                    response_text = f'❌ *{message}*'
                
                self._send_telegram_message(
                    chat_id,
                    response_text,
                    self.sub_manager.get_main_keyboard()
                )
                
            except ValueError as e:
                current_year = datetime.now().year
                self._send_telegram_message(
                    chat_id,
                    f"""❌ Неверный формат даты

*Правильный формат:*
• **ДД.ММ** - для {current_year} года
• **ДД.ММ.ГГ** - для следующего года

*Пример:*
15.06 - 15 июня
25.12.25 - 25 декабря {current_year + 1}

Введите дату:""",
                    self.sub_manager.get_cancel_keyboard()
                )

    # Остальные методы остаются без изменений
    def _show_main_menu(self, chat_id):
        self._send_telegram_message(
            chat_id,
            """🎯 *Единый центр контроля подписок*

Выберите действие:""",
            self.sub_manager.get_main_keyboard()
        )
    
    def _show_subscriptions_menu(self, chat_id):
        self._send_telegram_message(
            chat_id,
            '📋 *Добавление подписки*\n\nВыберите популярную подписку или введите свою:',
            self.sub_manager.get_subscriptions_keyboard()
        )
    
    def _show_my_subscriptions(self, chat_id):
        subscriptions = self.db.get_user_subscriptions(chat_id)
        
        if not subscriptions:
            self._send_telegram_message(
                chat_id,
                "*📋 У вас пока нет активных подписок*\n\nНажмите '➕ Добавить подписку' чтобы добавить первую подписку!",
                self.sub_manager.get_main_keyboard()
            )
            return
        
        total = sum(price for _, _, price, _, _ in subscriptions)
        sub_list = []
        
        for sub_id, name, price, day, next_date in subscriptions:
            sub_list.append(f"• *{name}*: {price} руб\n  📅 След. списание: {next_date}")
        
        message = f"""*📋 Ваши подписки*

{"\n".join(sub_list)}

*💰 Итого в месяц:* {total} руб
*📊 Всего подписок:* {len(subscriptions)}"""
        
        keyboard = []
        for sub_id, name, price, day, next_date in subscriptions:
            keyboard.append([{'text': f'📅 Изменить дату {sub_id}'}])
            keyboard.append([{'text': f'❌ Удалить {name}'}])
        
        keyboard.append([{'text': '🔙 Главное меню'}])
        
        self._send_telegram_message(
            chat_id,
            message,
            {'keyboard': keyboard, 'resize_keyboard': True}
        )
    
    def _show_subscription_info(self, chat_id, service_name):
        info = self.sub_manager.get_subscription_info(service_name)
        keyboard = {
            'keyboard': [
                [{'text': f'✅ {service_name}'}],
                [{'text': '🔙 Назад'}]
            ],
            'resize_keyboard': True
        }
        
        self._send_telegram_message(
            chat_id,
            f'*{service_name}*\n\n💳 *Стоимость:* {info["price"]} руб/мес\n📝 *Описание:* {info["description"]}\n\nДобавить для отслеживания?',
            keyboard
        )
    
    def _add_popular_subscription(self, chat_id, service_name):
        info = self.sub_manager.get_subscription_info(service_name)
        
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
            settings = self.db.get_notification_settings(chat_id)
            days_text = "в день списания" if settings['days_before'] == 0 else f"за {settings['days_before']} дня"
            
            response_text = f"""✅ *Подписка добавлена!*

📺 *{service_name}*
💳 {info["price"]} руб/мес
📅 Следующее списание: {next_charge_date}

🔔 *Уведомление настроено {days_text}*"""
        else:
            response_text = f'❌ *{message}*'
        
        self._send_telegram_message(
            chat_id,
            response_text,
            self.sub_manager.get_main_keyboard()
        )
    
    def _start_date_change(self, chat_id, subscription_id):
        self.user_sessions[chat_id] = {
            'changing_date': True,
            'subscription_id': subscription_id
        }
        
        current_year = datetime.now().year
        
        self._send_telegram_message(
            chat_id,
            f"""📅 *Изменение даты списания*

Введите новую дату списания:""",
            self.sub_manager.get_cancel_keyboard()
        )
    
    def _handle_date_change(self, chat_id, text):
        session = self.user_sessions[chat_id]
        subscription_id = session['subscription_id']
        
        try:
            today = datetime.now()
            current_year = today.year
            
            if re.match(r'^\d{1,2}\.\d{1,2}$', text):
                day, month = map(int, text.split('.'))
                charge_date = today.replace(month=month, day=day, year=current_year)
                
                if charge_date < today:
                    charge_date = charge_date.replace(year=current_year + 1)
                
                next_charge_date = charge_date.strftime("%d.%m.%Y")
            
            elif re.match(r'^\d{1,2}\.\d{1,2}\.\d{2}$', text):
                day, month, year = map(int, text.split('.'))
                full_year = 2000 + year if year < 100 else year
                charge_date = today.replace(year=full_year, month=month, day=day)
                next_charge_date = charge_date.strftime("%d.%m.%Y")
            
            else:
                raise ValueError("Неверный формат даты")
            
            if charge_date <= today:
                raise ValueError("Дата должна быть в будущем")
            
            success, message = self.db.update_subscription_date(chat_id, subscription_id, next_charge_date)
            
            del self.user_sessions[chat_id]
            
            if success:
                response_text = f"✅ *Дата списания обновлена!*\n\nНовая дата: {next_charge_date}"
            else:
                response_text = f'❌ *{message}*'
            
            self._send_telegram_message(
                chat_id,
                response_text,
                self.sub_manager.get_main_keyboard()
            )
            
        except ValueError as e:
            self._send_telegram_message(
                chat_id,
                f"❌ {str(e)}\n\nВведите дату в формате ДД.ММ или ДД.ММ.ГГ:",
                self.sub_manager.get_cancel_keyboard()
            )
    
    def _show_notifications_settings(self, chat_id):
        settings = self.db.get_notification_settings(chat_id)
        
        status = "включены" if settings['is_active'] else "выключены"
        days_text = "в день списания" if settings['days_before'] == 0 else f"за {settings['days_before']} дня"
        
        self._send_telegram_message(
            chat_id,
            f"""🔔 *Настройка уведомлений*

Текущие настройки:
• Статус: {status}
• Время напоминания: {days_text}

Выберите новые настройки:""",
            self.sub_manager.get_notifications_keyboard()
        )
    
    def _handle_notification_setting(self, chat_id, text):
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
            self._show_notifications_settings(chat_id)
            return
        
        success = self.db.set_notification_settings(chat_id, settings)
        
        if success:
            status = "включены" if settings['is_active'] else "выключены"
            days_text = "в день списания" if settings['days_before'] == 0 else f"за {settings['days_before']} дня"
            
            response_text = f"""✅ *Настройки сохранены!*

• Статус: {status}
• Время напоминания: {days_text}"""
        else:
            response_text = '❌ *Ошибка сохранения настроек*'
        
        self._send_telegram_message(
            chat_id,
            response_text,
            self.sub_manager.get_main_keyboard()
        )
    
    def _show_analytics(self, chat_id):
        subscriptions = self.db.get_user_subscriptions(chat_id)
        
        if not subscriptions:
            self._send_telegram_message(
                chat_id,
                'У вас пока нет подписок для анализа.',
                self.sub_manager.get_main_keyboard()
            )
            return
        
        total_monthly = sum(price for _, _, price, _, _ in subscriptions)
        total_yearly = total_monthly * 12
        
        expensive_subs = sorted(subscriptions, key=lambda x: x[2], reverse=True)[:3]
        
        analytics_text = f"""💰 *Финансовая аналитика*

*Общие расходы:*
💳 В месяц: {total_monthly} руб
📈 В год: {total_yearly} руб

*Самые дорогие подписки:*
"""
        
        for i, (sub_id, name, price, day, next_date) in enumerate(expensive_subs, 1):
            analytics_text += f"{i}. {name} - {price} руб/мес\n"
        
        analytics_text += f"\n💡 *Совет:* Проверяйте подписки раз в месяц"
        
        self._send_telegram_message(
            chat_id,
            analytics_text,
            self.sub_manager.get_main_keyboard()
        )
    
    def _show_laws(self, chat_id):
        self._send_telegram_message(
            chat_id,
            """⚖️ *Федеральный закон № 376-ФЗ от 15.10.2025*

*Ключевые положения:*
• Запрет списаний с удаленных карт
• Обязанность приема отказа от платежных средств

*Вступает в силу:* 1 марта 2026 года""",
            self.sub_manager.get_main_keyboard()
        )
    
    def _show_unsubscribe(self, chat_id):
        subscriptions = self.db.get_user_subscriptions(chat_id)
        
        if not subscriptions:
            self._send_telegram_message(
                chat_id,
                'У вас нет активных подписок.',
                self.sub_manager.get_main_keyboard()
            )
            return
        
        keyboard = []
        for sub_id, name, price, day, next_date in subscriptions:
            keyboard.append([{'text': f'❌ {name}'}])
        
        keyboard.append([{'text': '🔙 Главное меню'}])
        
        self._send_telegram_message(
            chat_id,
            '🗑️ *Отмена подписок*\n\nВыберите подписку для удаления:',
            {'keyboard': keyboard, 'resize_keyboard': True}
        )
    
    def _delete_subscription(self, chat_id, service_name):
        success, message = self.db.delete_subscription(chat_id, service_name)
        
        if success:
            response_text = f'✅ *Подписка удалена:* {service_name}'
        else:
            response_text = f'❌ *Ошибка:* {message}'
        
        self._send_telegram_message(
            chat_id,
            response_text,
            self.sub_manager.get_main_keyboard()
        )

handler = BotHandler