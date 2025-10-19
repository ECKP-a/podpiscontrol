'chat_id': chat_id,
            'text': 'Управление подписками\n\nВыберите действие:',
            'reply_markup': {
                'keyboard': SubscriptionManager.get_popular_subscriptions_keyboard(),
                'resize_keyboard': True
            }
        }
    
    def _handle_my_subscriptions(self, chat_id):
        subscriptions = self.db.get_user_subscriptions(chat_id)
        
        if subscriptions:
            total = sum(price for _, price, _ in subscriptions)
            sub_list = "\n".join(
                f"• {name}: {price} руб (списание {day} числа)"
                for name, price, day in subscriptions
            )
            
            text = f"""Ваши подписки:

{sub_list}

Итого в месяц: {total} руб
Всего подписок: {len(subscriptions)}"""
        else:
            text = 'У вас пока нет активных подписок.\nДобавьте первую подписку через меню!'
        
        return {'chat_id': chat_id, 'text': text}
    
    def _handle_delete_subscription(self, chat_id):
        subscriptions = self.db.get_user_subscriptions(chat_id)
        
        if subscriptions:
            keyboard = []
            for name, price, day in subscriptions:
                keyboard.append([{"text": f"Удалить {name}"}])
            keyboard.append([{"text": "Назад к подпискам"}])
            
            return {
                'chat_id': chat_id,
                'text': 'Выберите подписку для удаления:',
                'reply_markup': {
                    'keyboard': keyboard,
                    'resize_keyboard': True
                }
            }
        else:
            return {'chat_id': chat_id, 'text': 'У вас нет подписок для удаления.'}
    
    def _handle_subscription_info(self, chat_id, service_name):
        info = SubscriptionManager.get_subscription_info(service_name)
        
        if info:
            text = f"""Информация о подписке:

{service_name}
Стоимость: {info['price']} руб/мес
Описание: {info['description']}

Добавить эту подписку для отслеживания?"""
            
            keyboard = [
                [{"text": f"Добавить {service_name}"}],
                [{"text": "Назад к подпискам"}]
            ]
        else:
            text = "Подписка не найдена"
            keyboard = [[{"text": "Назад к подпискам"}]]
        
        return {
            'chat_id': chat_id,
            'text': text,
            'reply_markup': {'keyboard': keyboard, 'resize_keyboard': True}
        }
    
    def _handle_add_subscription(self, chat_id, service_name):
        info = SubscriptionManager.get_subscription_info(service_name)
        
        if info:
            success = self.db.add_subscription(chat_id, service_name, info['price'], 1)
            
            if success:
                text = f"Подписка '{service_name}' добавлена!\nСтоимость: {info['price']} руб\nСписание: 1 число каждого месяца"
            else:
                text = "Не удалось добавить подписку"
        else:
            text = "Подписка не найдена"
        
        return {'chat_id': chat_id, 'text': text}
    
    def _handle_delete_specific(self, chat_id, service_name):
        success = self.db.delete_subscription(chat_id, service_name)
        
        if success:
            text = f"Подписка '{service_name}' удалена"
        else:
            text = f"Не удалось удалить подписку '{service_name}'"
        
        return {'chat_id': chat_id, 'text': text}
    
    def _is_subscription_format(self, text):
        pattern = r'^[^-]+ - \d+ - (?:[1-9]|[12][0-9]|3[01])$'
        return bool(re.match(pattern, text))
    
    def _handle_custom_subscription(self, chat_id, text):
        try:
            name, price, day = [part.strip() for part in text.split(' - ')]
            price_val = float(price)
            day_val = int(day)
            
            if not (1 <= day_val <= 31):
                return {'chat_id': chat_id, 'text': "Дата должна быть от 1 до 31"}
            
            success = self.db.add_subscription(chat_id, name, price_val, day_val)
            
            if success:


text = f"Подписка добавлена:\nНазвание: {name}\nСтоимость: {price_val} руб\nДата списания: {day_val} число"
            else:
                text = "Ошибка при добавлении подписки"
                
        except ValueError:
            text = "Неверный формат. Пример: Netflix - 599 - 15"
        except Exception as e:
            text = f"Ошибка: {str(e)}"
        
        return {'chat_id': chat_id, 'text': text}
    
    def _send_telegram_response(self, response_data):
        payload = {
            'method': 'sendMessage',
            'chat_id': response_data['chat_id'],
            'text': response_data['text']
        }
        
        if 'reply_markup' in response_data:
            payload['reply_markup'] = response_data['reply_markup']
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode('utf-8'))

# ==================== ВАЖНО: ЭКСПОРТ ДЛЯ VERCEL ====================
handler = TelegramBotHandler
