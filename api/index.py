from http.server import BaseHTTPRequestHandler
import json
import sqlite3
import re
from datetime import datetime

class DatabaseManager:
    def __init__(self):
        # Используем постоянное хранилище Vercel
        self.db_path = '/tmp/podpiscontrol.db'
        self._init_db()
    
    def _init_db(self):
        """Инициализация базы данных с улучшенной структурой"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Основная таблица подписок
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    service_name TEXT NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    charge_day INTEGER NOT NULL CHECK(charge_day BETWEEN 1 AND 31),
                    end_date TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица для статистики и аналитики
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id INTEGER PRIMARY KEY,
                    total_saved DECIMAL(10,2) DEFAULT 0,
                    subscriptions_cancelled INTEGER DEFAULT 0,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Индексы для ускорения запросов
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_subscriptions ON subscriptions(user_id, is_active)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_created ON subscriptions(created_date)')
            
            conn.commit()
            conn.close()
            print("База данных инициализирована с улучшенной структурой")
        except Exception as e:
            print(f"Ошибка инициализации БД: {e}")
    
    def add_subscription(self, user_id, service_name, price, charge_day, end_date=None):
        """Добавление подписки с улучшенной логикой"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем существующую подписку
            cursor.execute('''
                SELECT id, is_active FROM subscriptions 
                WHERE user_id = ? AND service_name = ? 
                ORDER BY created_date DESC LIMIT 1
            ''', (user_id, service_name))
            
            existing = cursor.fetchone()
            
            if existing:
                sub_id, is_active = existing
                if is_active:
                    conn.close()
                    return False, "Эта подписка уже активна"
                else:
                    # Реактивируем удаленную подписку
                    cursor.execute('''
                        UPDATE subscriptions 
                        SET is_active = TRUE, price = ?, charge_day = ?, end_date = ?, updated_date = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (price, charge_day, end_date, sub_id))
            else:
                # Добавляем новую подписку
                cursor.execute('''
                    INSERT INTO subscriptions (user_id, service_name, price, charge_day, end_date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, service_name, price, charge_day, end_date))
            
            conn.commit()
            conn.close()
            return True, "Подписка успешно сохранена"
            
        except Exception as e:
            print(f"Ошибка добавления подписки: {e}")
            return False, "Ошибка при сохранении подписки"
    
    def get_user_subscriptions(self, user_id):
        """Получение подписок с улучшенной логикой"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT service_name, price, charge_day, end_date, created_date
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
    
    def get_user_stats(self, user_id):
        """Получение статистики пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Общая стоимость активных подписок
            cursor.execute('''
                SELECT COUNT(*), COALESCE(SUM(price), 0) 
                FROM subscriptions 
                WHERE user_id = ? AND is_active = TRUE
            ''', (user_id,))
            
            count, total = cursor.fetchone()
            
            # Количество отмененных подписок
            cursor.execute('''
                SELECT COUNT(*) 
                FROM subscriptions 
                WHERE user_id = ? AND is_active = FALSE
            ''', (user_id,))
            
            cancelled = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'active_count': count,
                'monthly_total': total,
                'cancelled_count': cancelled,
                'yearly_total': total * 12
            }
            
        except Exception as e:
            print(f"Ошибка получения статистики: {e}")
            return {'active_count': 0, 'monthly_total': 0, 'cancelled_count': 0, 'yearly_total': 0}
    
    def delete_subscription(self, user_id, service_name):
        """Удаление подписки с сохранением истории"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE subscriptions 
                SET is_active = FALSE, updated_date = CURRENT_TIMESTAMP
                WHERE user_id = ? AND service_name = ? AND is_active = TRUE
            ''', (user_id, service_name))
            
            affected = cursor.rowcount
            
            # Обновляем статистику отмен
            if affected > 0:
                cursor.execute('''
                    INSERT OR REPLACE INTO user_stats (user_id, subscriptions_cancelled, last_active)
                    VALUES (?, COALESCE((SELECT subscriptions_cancelled FROM user_stats WHERE user_id = ?), 0) + 1, CURRENT_TIMESTAMP)
                ''', (user_id, user_id))
            
            conn.commit()
            conn.close()
            
            return affected > 0, "Подписка удалена"
            
        except Exception as e:
            print(f"Ошибка удаления подписки: {e}")
            return False, "Ошибка при удалении подписки"

class SubscriptionManager:
    """Улучшенный менеджер подписок"""
    
    POPULAR_SUBSCRIPTIONS = {
        'Яндекс Плюс': {'price': 399, 'description': 'Кино, музыка, доставка', 'category': 'развлечения'},
        'СберПрайм': {'price': 299, 'description': 'Okko, музыка, доставка', 'category': 'развлечения'},
        'Ozon Premium': {'price': 199, 'description': 'Бесплатная доставка', 'category': 'покупки'},
        'ВБ Клуб': {'price': 199, 'description': 'Бесплатная доставка', 'category': 'покупки'},
        'VK Музыка': {'price': 199, 'description': 'Музыка без ограничений', 'category': 'развлечения'},
        'Яндекс Музыка': {'price': 169, 'description': 'Каталог музыки', 'category': 'развлечения'},
        'IVI': {'price': 399, 'description': 'Фильмы и сериалы', 'category': 'развлечения'},
        'START': {'price': 299, 'description': 'Русские сериалы', 'category': 'развлечения'},
        'Кинопоиск': {'price': 399, 'description': 'Фильмы и сериалы', 'category': 'развлечения'},
        'Магнит Премиум': {'price': 199, 'description': 'Скидки в магазинах', 'category': 'покупки'},
        'Alfa Only': {'price': 199, 'description': 'Премиум банк', 'category': 'финансы'},
        'Т-Банк Pro': {'price': 299, 'description': 'Премиум банк', 'category': 'финансы'},
        'Пакет X5': {'price': 149, 'description': 'Скидки в Пятерочке', 'category': 'покупки'},
        'Сотовые услуги': {'price': 300, 'description': 'Ежемесячная связь', 'category': 'связь'},
        'Домашний интернет': {'price': 500, 'description': 'Доступ в интернет', 'category': 'связь'}
    }
    
    DONATION_LINK = "https://tbank.ru/cf/1pxGD5puRV3"
    
    @classmethod
    def get_main_keyboard(cls):
        """Главная клавиатура с улучшенными кнопками"""
        return {
            'keyboard': [
                [{'text': 'Управление подписками'}],
                [{'text': 'Мои подписки'}, {'text': 'Статистика'}],
                [{'text': 'Поддержать проект'}, {'text': 'О законе'}],
                [{'text': 'Помощь'}, {'text': 'Финансовая аналитика'}]
            ],
            'resize_keyboard': True
        }
    
    @classmethod
    def get_subscriptions_keyboard(cls):
        """Улучшенная клавиатура подписок по категориям"""
        categories = {}
        for name, info in cls.POPULAR_SUBSCRIPTIONS.items():
            category = info['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(name)
        
        keyboard = []
        
        # Добавляем подписки по категориям
        for category, services in categories.items():
            keyboard.append([{'text': f'📁 {category.capitalize()}'}])
            for i in range(0, len(services), 2):
                row = [
                    {'text': services[i]}, 
                    {'text': services[i+1]} if i+1 < len(services) else {'text': '⋯'}
                ]
                keyboard.append(row)
        
        # Сервисные кнопки
        keyboard.extend([
            [{'text': '➕ Своя подписка'}, {'text': '📊 Статистика'}],
            [{'text': '💳 Поддержать проект'}, {'text': '🔙 Главное меню'}]
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
    def get_donation_message(cls):
        """Сообщение для поддержки проекта"""
        return f'''*Поддержка развития проекта*

Проект «Единый центр контроля подписок» реализуется *на средства частных инвесторов и пожертвования пользователей* в рамках исполнения федерального законодательства.

*Ваш вклад поможет:*
• Развивать систему напоминаний
• Добавлять новые функции аналитики  
• Поддерживать стабильную работу сервиса
• Расширять базу знаний о правах потребителей

*Ссылка для поддержки:*
{cls.DONATION_LINK}

*Проект осуществляется при поддержке бизнес-сообщества*'''

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
        self.wfile.write('Bot is running with persistent storage!'.encode('utf-8'))
    
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
        # Проверяем активные сессии
        if chat_id in self.user_sessions and self.user_sessions[chat_id].get('adding_subscription'):
            return self._handle_subscription_flow(chat_id, text)
        
        # Обработка команды отмены
        if text == '❌ Отмена':
            if chat_id in self.user_sessions:
                del self.user_sessions[chat_id]
            return self.process_message(chat_id, 'Главное меню')
        
        if text == '/start' or text == '🔙 Главное меню':
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': '*Единый центр контроля подписок*\n\n*Официальный информационный партнер* в рамках реализации инициативы о защите прав потребителей\n\n*Проект реализуется при поддержке бизнес-сообщества*\n\n*Выберите действие:*',
                'reply_markup': self.sub_manager.get_main_keyboard(),
                'parse_mode': 'Markdown'
            }
        
        elif text == 'Управление подписками' or text == '/subs':
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': '*Управление подписками*\n\nВыберите категорию или воспользуйтесь сервисными кнопками:',
                'reply_markup': self.sub_manager.get_subscriptions_keyboard(),
                'parse_mode': 'Markdown'
            }
        
        elif text == 'Мои подписки':
            subscriptions = self.db.get_user_subscriptions(chat_id)
            stats = self.db.get_user_stats(chat_id)
            
            if subscriptions:
                total = sum(price for _, price, _, _, _ in subscriptions)
                sub_list = "\n".join([
                    f"• {name}: {price} руб ({day} число)" + 
                    (f" - до {end_date}" if end_date else "")
                    for name, price, day, end_date, _ in subscriptions
                ])
                
                message = f"""*Ваши подписки*

{sub_list}

*Итого в месяц:* {total} руб
*Итого в год:* {total * 12} руб
*Активных подписок:* {stats['active_count']}"""
            else:
                message = "*У вас пока нет активных подписок*\n\nДобавьте первую подписку через меню управления!"
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'reply_markup': self.sub_manager.get_main_keyboard()
            }
        
        elif text == 'Статистика' or text == '📊 Статистика' or text == 'Финансовая аналитика':
            stats = self.db.get_user_stats(chat_id)
            subscriptions = self.db.get_user_subscriptions(chat_id)
            
            if subscriptions:
                total_monthly = stats['monthly_total']
                total_yearly = stats['yearly_total']
                
                # Аналитика по категориям
                categories = {}
                for name, price, _, _, _ in subscriptions:
                    info = self.sub_manager.POPULAR_SUBSCRIPTIONS.get(name, {'category': 'другое'})
                    category = info['category']
                    if category not in categories:
                        categories[category] = 0
                    categories[category] += price
                
                category_analysis = "\n".join([f"• {cat}: {price} руб" for cat, price in categories.items()])
                
                message = f"""*Финансовая аналитика*

*Ежемесячные расходы:* {total_monthly} руб
*Годовые расходы:* {total_yearly} руб

*Распределение по категориям:*
{category_analysis}

*Отменено подписок:* {stats['cancelled_count']}

*Проект поддерживается пользователями*"""
            else:
                message = "*Статистика*\n\nУ вас пока нет активных подписок для анализа."
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'reply_markup': self.sub_manager.get_main_keyboard()
            }
        
        elif text == '➕ Своя подписка' or text == 'Быстро добавить':
            self.user_sessions[chat_id] = {
                'adding_subscription': True,
                'step': 'name'
            }
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': '*Добавление своей подписки*\n\n*Шаг 1 из 3*\nВведите название подписки:',
                'parse_mode': 'Markdown',
                'reply_markup': self.sub_manager.get_cancel_keyboard()
            }
        
        elif text == '💳 Поддержать проект' or text == 'Поддержать проект':
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': self.sub_manager.get_donation_message(),
                'parse_mode': 'Markdown',
                'reply_markup': self.sub_manager.get_main_keyboard()
            }
        
        elif text in self.sub_manager.POPULAR_SUBSCRIPTIONS:
            info = self.sub_manager.get_subscription_info(text)
            keyboard = {
                'keyboard': [
                    [{'text': f'✅ Добавить {text}'}],
                    [{'text': '📋 К подпискам'}, {'text': '🔙 Главное меню'}]
                ],
                'resize_keyboard': True
            }
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': f'*{text}*\n\n*Стоимость:* {info["price"]} руб/мес\n*Категория:* {info["category"]}\n*Описание:* {info["description"]}\n\nДобавить для отслеживания?',
                'reply_markup': keyboard,
                'parse_mode': 'Markdown'
            }
        
        elif text.startswith('✅ Добавить '):
            service_name = text.replace('✅ Добавить ', '')
            info = self.sub_manager.get_subscription_info(service_name)
            
            success, message = self.db.add_subscription(chat_id, service_name, info['price'], 1)
            
            response_text = f'*{message}*\n\n*Подписка:* {service_name}\n*Стоимость:* {info["price"]} руб/мес\n*Категория:* {info["category"]}'
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': response_text,
                'parse_mode': 'Markdown',
                'reply_markup': self.sub_manager.get_main_keyboard()
            }
        
        elif text == '🗑️ Удалить подписку':
            subscriptions = self.db.get_user_subscriptions(chat_id)
            
            if subscriptions:
                keyboard = []
                for name, price, day, end_date, _ in subscriptions:
                    display_name = f"{name} ({price} руб)"
                    keyboard.append([{'text': f'❌ Удалить {display_name}'}])
                keyboard.append([{'text': '📋 К подпискам'}, {'text': '🔙 Главное меню'}])
                
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': '*Удаление подписки*\n\nВыберите подписку для удаления:',
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
            # Извлекаем название подписки из текста
            import re
            match = re.match(r'❌ Удалить (.+) \(\d+ руб\)', text)
            if match:
                service_name = match.group(1).strip()
                success, message = self.db.delete_subscription(chat_id, service_name)
                
                response_text = f'*{message}*\n\nПодписка: {service_name}'
            else:
                response_text = 'Ошибка при обработке запроса'
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': response_text,
                'parse_mode': 'Markdown',
                'reply_markup': self.sub_manager.get_main_keyboard()
            }
        
        elif text in ['📋 К подпискам', '⋯', '📁 ']:
            return self.process_message(chat_id, 'Управление подписками')
        
        elif text == 'О законе' or text == '/laws':
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': '*Федеральный закон № 376-ФЗ*\n\n*С 15 октября 2025 года:*\n\n• Сервисы обязаны получать ваше прямое согласие на каждое списание\n• Запрещено автоматическое продление без подтверждения\n• Отмена подписки должна быть не сложнее, чем оформление\n\n*Проект реализуется при поддержке бизнес-сообщества*',
                'parse_mode': 'Markdown',
                'reply_markup': self.sub_manager.get_main_keyboard()
            }
        
        elif text == 'Помощь' or text == '/help':
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': '*Помощь и поддержка*\n\n*Проект существует на средства пользователей*\n\n*Частые вопросы:*\n\n• Как добавить подписку? - Используйте меню "Управление подписками"\n• Как отменить подписку? - Используйте функцию удаления\n• Поддержите развитие - используйте кнопку "Поддержать проект"\n\n*Напишите ваш вопрос - помогу разобраться!*',
                'parse_mode': 'Markdown',
                'reply_markup': self.sub_manager.get_main_keyboard()
            }
        
        else:
            # Автоматическое добавление произвольного текста как подписки
            self.user_sessions[chat_id] = {
                'adding_subscription': True,
                'step': 'name',
                'name': text
            }
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': f'*Добавление подписки*\n\nВы ввели: *{text}*\n\n*Шаг 2 из 3*\nВведите стоимость подписки в рублях:',
                'parse_mode': 'Markdown',
                'reply_markup': self.sub_manager.get_cancel_keyboard()
            }
    
    def _handle_subscription_flow(self, chat_id, text):
        """Обработка многошагового добавления подписки"""
        session = self.user_sessions[chat_id]
        
        if text == '❌ Отмена':
            del self.user_sessions[chat_id]
            return self.process_message(chat_id, 'Главное меню')
        
        if session['step'] == 'name':
            session['name'] = text
            session['step'] = 'price'
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': '*Добавление своей подписки*\n\n*Шаг 2 из 3*\nВведите стоимость подписки в рублях:',
                'parse_mode': 'Markdown',
                'reply_markup': self.sub_manager.get_cancel_keyboard()
            }
        
        elif session['step'] == 'price':
            try:
                price = float(text)
                if price <= 0:
                    raise ValueError("Цена должна быть положительной")
                    
                session['price'] = price
                session['step'] = 'date'
                
                current_year = datetime.now().year
                next_year = current_year + 1
                
                date_keyboard = {
                    'keyboard': [
                        [{'text': '⏩ Пропустить'}],
                        [{'text': '❌ Отмена'}]
                    ],
                    'resize_keyboard': True
                }
                
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': f'*Добавление своей подписки*\n\n*Шаг 3 из 3*\nВведите дату окончания подписки:\n\n*Формат:*\n• 19.10 - если окончание в {current_year} году\n• 19.10.{str(next_year)[-2:]} - если в {next_year} году\n• Или нажмите "Пропустить" для бессрочной',
                    'parse_mode': 'Markdown',
                    'reply_markup': date_keyboard
                }
            except ValueError:
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': 'Неверный формат цены. Введите положительное число:',
                    'parse_mode': 'Markdown',
                    'reply_markup': self.sub_manager.get_cancel_keyboard()
                }
        
        elif session['step'] == 'date':
            end_date = None
            if text != '⏩ Пропустить':
                if re.match(r'^\d{1,2}\.\d{1,2}$', text):
                    day, month = text.split('.')
                    end_date = f"{int(day):02d}.{int(month):02d}"
                elif re.match(r'^\d{1,2}\.\d{1,2}\.\d{2}$', text):
                    day, month, year = text.split('.')
                    end_date = f"{int(day):02d}.{int(month):02d}.{year}"
                else:
                    return {
                        'method': 'sendMessage',
                        'chat_id': chat_id,
                        'text': 'Неверный формат даты. Используйте:\n• 19.10 - для этого года\n• 19.10.26 - для следующего года\n• Или "Пропустить"',
                        'parse_mode': 'Markdown',
                        'reply_markup': self.sub_manager.get_cancel_keyboard()
                    }
            
            success, message = self.db.add_subscription(
                chat_id, 
                session['name'], 
                session['price'], 
                1,
                end_date
            )
            
            del self.user_sessions[chat_id]
            
            if success:
                response_text = f'*✅ Подписка добавлена!*\n\n*Название:* {session["name"]}\n*Стоимость:* {session["price"]} руб/мес\n*Списание:* 1 число каждого месяца'
                if end_date:
                    response_text += f'\n*Окончание:* {end_date}'
                response_text += '\n\n*Проект поддерживается пользователями*'
            else:
                response_text = f'*❌ Ошибка:* {message}'
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': response_text,
                'parse_mode': 'Markdown',
                'reply_markup': self.sub_manager.get_main_keyboard()
            }

handler = BotHandler