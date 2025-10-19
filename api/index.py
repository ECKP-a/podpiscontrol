from http.server import BaseHTTPRequestHandler
import json
import sqlite3
import re
from datetime import datetime
from typing import Optional, Dict, List, Tuple

# ==================== КОНФИГУРАЦИЯ ====================
class Config:
    """Конфигурация приложения"""
    DB_PATH = '/tmp/subscriptions.db'
    DEFAULT_REMINDER_DAYS = 3

# ==================== МОДЕЛИ ДАННЫХ ====================
class SubscriptionService:
    """Сервис для работы с подписками"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Инициализация базы данных"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица подписок
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    service_name TEXT NOT NULL,
                    price DECIMAL(10, 2) NOT NULL,
                    charge_day INTEGER NOT NULL CHECK(charge_day BETWEEN 1 AND 31),
                    currency TEXT DEFAULT 'RUB',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    UNIQUE(user_id, service_name)
                )
            ''')
            
            # Таблица напоминаний
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subscription_id INTEGER,
                    reminder_date DATE NOT NULL,
                    is_sent BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (subscription_id) REFERENCES subscriptions (id)
                )
            ''')
            
            conn.commit()
    
    def add_user(self, user_id: int, username: str, first_name: str) -> bool:
        """Добавление/обновление пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO users (user_id, username, first_name)
                    VALUES (?, ?, ?)
                ''', (user_id, username, first_name))
                return True
        except Exception as e:
            print(f"Error adding user: {e}")
            return False
    
    def add_subscription(self, user_id: int, service_name: str, price: float, 
                        charge_day: int, currency: str = 'RUB') -> bool:
        """Добавление подписки"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO subscriptions (user_id, service_name, price, charge_day, currency)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, service_name, price, charge_day, currency))
                return True
        except Exception as e:
            print(f"Error adding subscription: {e}")
            return False
    
    def get_user_subscriptions(self, user_id: int) -> List[Tuple]:
        """Получение подписок пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT service_name, price, charge_day, currency 
                    FROM subscriptions 
                    WHERE user_id = ? AND is_active = TRUE
                    ORDER BY service_name
                ''', (user_id,))
                return cursor.fetchall()
        except Exception as e:
            print(f"Error getting subscriptions: {e}")
            return []
    
    def delete_subscription(self, user_id: int, service_name: str) -> bool:
        """Удаление подписки"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE subscriptions 
                    SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND service_name = ?
                ''', (user_id, service_name))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting subscription: {e}")
            return False

# ==================== СЕРВИС ПОДПИСОК ====================
class SubscriptionManager:
    """Менеджер подписок с готовыми шаблонами"""
    
    POPULAR_SUBSCRIPTIONS = {
        '🛍️ Яндекс Плюс': {'price': 399, 'description': 'Кинопоиск, музыка, доставка'},
        '📺 СберПрайм': {'price': 299, 'description': 'Okko, музыка, доставка'},
        '🎬 Ozon Premium': {'price': 199, 'description': 'Бесплатная доставка + Kion'},
        '🛒 ВБ Клуб': {'price': 199, 'description': 'Бесплатная доставка Wildberries'},
        '📱 Сотовые услуги': {'price': 300, 'description': 'Ежемесячная связь'},
        '🎵 VK Музыка': {'price': 199, 'description': 'Музыка без ограничений'},
        '💳 Alfa Only': {'price': 199, 'description': 'Премиум-подписка Альфа-Банка'},
        '🏦 ВТБ Плюс': {'price': 199, 'description': 'Подписка ВТБ'},
        '📀 МТС Premium': {'price': 299, 'description': 'Кино, музыка, скидки'},
        '⛽ Газпром Бонус': {'price': 299, 'description': 'Топливо, подписки, скидки'}
    }
    
    @classmethod
    def get_popular_subscriptions_keyboard(cls) -> List[List[Dict]]:
        """Клавиатура популярных подписок"""
        subscriptions = list(cls.POPULAR_SUBSCRIPTIONS.keys())
        keyboard = []
        
        # Группируем по 2 кнопки в ряду
        for i in range(0, len(subscriptions), 2):
            row = [{"text": sub} for sub in subscriptions[i:i+2]]
            keyboard.append(row)
        
        # Добавляем служебные кнопки
        keyboard.extend([
            [{"text": "➕ Добавить свою подписку"}],
            [{"text": "📊 Мои подписки"}, {"text": "🗑️ Удалить подписку"}],
            [{"text": "🔙 Главное меню"}]
        ])
        
        return keyboard
    
    @classmethod
    def get_subscription_info(cls, service_name: str) -> Optional[Dict]:
        """Информация о подписке"""
        return cls.POPULAR_SUBSCRIPTIONS.get(service_name)

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
class CommandHandler:
    """Обработчик команд бота"""
    
    def __init__(self, subscription_service: SubscriptionService):
        self.service = subscription_service
    
    def handle_start(self, chat_id: int, user_data: Dict) -> Dict:
        """Обработка команды /start"""
        # Сохраняем пользователя
        self.service.add_user(
            user_id=chat_id,
            username=user_data.get('username', ''),
            first_name=user_data.get('first_name', '')
        )
        
        text = """🎯 *Единый Центр Контроля Подписок*

*Ваш персональный помощник в управлении подписками*

📊 **Возможности:**
• Учет всех подписок в одном месте
• Напоминания о списаниях  
• Анализ расходов
• Помощь в отмене подписок

*Используйте команды ниже ↓*"""
        
        keyboard = [
            [{"text": "📋 Управление подписками"}],
            [{"text": "⚖️ О законе"}, {"text": "❓ Помощь"}]
        ]
        
        return {
            'text': text,
            'reply_markup': {
                'keyboard': keyboard,
                'resize_keyboard': True,
                'one_time_keyboard': False
            },
            'parse_mode': 'Markdown'
        }
    
    def handle_subs(self, chat_id: int) -> Dict:
        """Обработка команды управления подписками"""
        text = "📋 *Управление подписками*\n\nВыберите действие:"
        
        return {
            'text': text,
            'reply_markup': {
                'keyboard': SubscriptionManager.get_popular_subscriptions_keyboard(),
                'resize_keyboard': True
            },
            'parse_mode': 'Markdown'
        }
    
    def handle_subscription_info(self, service_name: str) -> Dict:
        """Информация о конкретной подписке"""
        info = SubscriptionManager.get_subscription_info(service_name)
        
        if info:
            text = f"""🔍 *{service_name}*

*Стоимость:* {info['price']}₽/мес
*Описание:* {info['description']}

Добавить эту подписку для отслеживания?"""
            
            keyboard = [
                [{"text": f"✅ Добавить {service_name}"}],
                [{"text": "🔙 К подпискам"}]
            ]
        else:
            text = "❌ Подписка не найдена"
            keyboard = [[{"text": "🔙 К подпискам"}]]
        
        return {
            'text': text,
            'reply_markup': {'keyboard': keyboard, 'resize_keyboard': True},
            'parse_mode': 'Markdown'
        }
    
    def handle_my_subscriptions(self, chat_id: int) -> Dict:
        """Показать подписки пользователя"""
        subscriptions = self.service.get_user_subscriptions(chat_id)
        
        if subscriptions:
            total = sum(price for _, price, _, _ in subscriptions)
            sub_list = "\n".join(
                f"• {name}: {price}₽ (списание {day} числа)"
                for name, price, day, _ in subscriptions
            )
            
            text = f"""📊 *Ваши подписки*

{sub_list}

*Итого в месяц:* {total}₽
*Всего подписок:* {len(subscriptions)}"""
        else:
            text = """📊 *У вас пока нет подписок*

Добавьте первую подписку через меню «Управление подписками»"""
        
        keyboard = [
            [{"text": "📋 Управление подписками"}],
            [{"text": "🔙 Главное меню"}]
        ]
        
        return {
            'text': text,
            'reply_markup': {'keyboard': keyboard, 'resize_keyboard': True},
            'parse_mode': 'Markdown'
        }

# ==================== ОСНОВНОЙ ОБРАБОТЧИК ====================
class BotHandler(BaseHTTPRequestHandler):
    """Основной обработчик бота"""
    
    def __init__(self, *args, **kwargs):
        self.subscription_service = SubscriptionService(Config.DB_PATH)
        self.command_handler = CommandHandler(self.subscription_service)
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Обработка GET запросов"""
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write('🚀 Bot is running with advanced logic!'.encode())
    
    def do_POST(self):
        """Обработка POST запросов от Telegram"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            update = json.loads(post_data)
            
            print(f"📨 Update: {update}")
            
            if 'message' in update:
                self._handle_message(update['message'])
                return
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            print(f"📋 Traceback: {traceback.format_exc()}")
        
        self._send_response(200)
    
    def _handle_message(self, message: Dict):
        """Обработка сообщения"""
        chat_id = message['chat']['id']
        text = message.get('text', '').strip()
        user_data = {
            'username': message['chat'].get('username'),
            'first_name': message['chat'].get('first_name', '')
        }
        
        print(f"💬 Processing: '{text}' from {chat_id}")
        
        # Обработка команд
        response_data = self._process_command(chat_id, text, user_data)
        
        # Отправка ответа
        if response_data:
            self._send_telegram_response(chat_id, response_data)
    
    def _process_command(self, chat_id: int, text: str, user_data: Dict) -> Optional[Dict]:
        """Обработка команд и текста"""
        
        # Основные команды
        if text == '/start' or text == '🔙 Главное меню':
            return self.command_handler.handle_start(chat_id, user_data)
        
        elif text == '/subs' or text == '📋 Управление подписками':
            return self.command_handler.handle_subs(chat_id)
        
        elif text == '📊 Мои подписки':
            return self.command_handler.handle_my_subscriptions(chat_id)
        
        elif text in SubscriptionManager.POPULAR_SUBSCRIPTIONS:
            return self.command_handler.handle_subscription_info(text)
        
        elif text == '➕ Добавить свою подписку':
            return {
                'text': """➕ *Добавление своей подписки*

Введите данные в формате:
`Название - Стоимость - Дата списания`

*Примеры:*
• `Netflix - 599 - 15`
• `Спортзал - 2000 - 1`
• `Apple Music - 169 - 10`

*Примечание:* Дата - число месяца (1-31)""",
                'parse_mode': 'Markdown'
            }
        
        elif text == '/laws' or text == '⚖️ О законе':
            return {
                'text': """⚖️ *Федеральный закон № 376-ФЗ*

*С 15 октября 2025 года:*

✅ Сервисы обязаны получать ваше *прямое согласие* на каждое списание
✅ *Запрещено* автоматическое продление без подтверждения  
✅ Отмена подписки должна быть *не сложнее*, чем оформление

*Ваши права защищены!*""",
                'parse_mode': 'Markdown'
            }
        
        elif text == '/help' or text == '❓ Помощь':
            return {
                'text': """❓ *Помощь*

*Частые вопросы:*

• *Как добавить подписку?* - Используйте меню «Управление подписками»
• *Как отменить подписку?* - Напишите «Отмена подписки [название]»
• *Не приходят напоминания?* - Функция в разработке

*Напишите ваш вопрос - помогу!*""",
                'parse_mode': 'Markdown'
            }
        
        elif text == '🔙 К подпискам':
            return self.command_handler.handle_subs(chat_id)
        
        # Обработка пользовательского ввода подписки
        elif self._is_subscription_format(text):
            return self._handle_custom_subscription(chat_id, text)
        
        else:
            return {
                'text': "🤔 Не понял команду. Используйте кнопки меню или /start",
                'parse_mode': 'Markdown'
            }
    
    def _is_subscription_format(self, text: str) -> bool:
        """Проверка формата пользовательской подписки"""
        pattern = r'^[^-]+ - \d+ - (?:[1-9]|[12][0-9]|3[01])$'
        return bool(re.match(pattern, text))
    
    def _handle_custom_subscription(self, chat_id: int, text: str) -> Dict:
        """Обработка пользовательской подписки"""
        try:
            name, price, day = [part.strip() for part in text.split(' - ')]
            price_val = float(price)
            day_val = int(day)
            
            if not (1 <= day_val <= 31):
                return {'text': "❌ Дата должна быть от 1 до 31"}
            
            success = self.subscription_service.add_subscription(
                chat_id, name, price_val, day_val
            )
            
            if success:
                return {
                    'text': f"""✅ *Подписка добавлена!*

*Название:* {name}
*Стоимость:* {price_val}₽
*Списание:* {day_val} число

Теперь вы можете видеть её в «Мои подписки»""",
                    'parse_mode': 'Markdown'
                }
            else:
                return {'text': "❌ Ошибка при добавлении подписки"}
                
        except ValueError:
            return {'text': "❌ Неверный формат. Пример: `Netflix - 599 - 15`", 'parse_mode': 'Markdown'}
        except Exception as e:
            return {'text': f"❌ Ошибка: {str(e)}"}
    
    def _send_telegram_response(self, chat_id: int, response_data: Dict):
        """Отправка ответа в Telegram"""
        response_payload = {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': response_data['text']
        }
        
        # Добавляем дополнительные параметры если есть
        if 'reply_markup' in response_data:
            response_payload['reply_markup'] = response_data['reply_markup']
        if 'parse_mode' in response_data:
            response_payload['parse_mode'] = response_data['parse_mode']
        
        self._send_response(200, response_payload)
    
    def _send_response(self, status_code: int, body: Dict = None):
        """Отправка HTTP ответа"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        if body:
            self.wfile.write(json.dumps(body).encode())
        else:
            self.wfile.write(json.dumps({'status': 'ok'}).encode())

def main(request):
    """Точка входа для Vercel"""
    return BotHandler
