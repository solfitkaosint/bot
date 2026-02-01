import uuid
import logging
from typing import Optional, Dict, Any
import asyncio

from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PaymentManager:
    def __init__(self, db):
        self.db = db
        self.payment_enabled = False
        
        # Проверяем наличие настроек ЮKassa
        if YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY:
            try:
                from yookassa import Configuration
                Configuration.account_id = YOOKASSA_SHOP_ID
                Configuration.secret_key = YOOKASSA_SECRET_KEY
                self.payment_enabled = True
                logger.info("ЮKassa настроен успешно")
            except ImportError:
                logger.warning("Библиотека yookassa не установлена")
        else:
            logger.warning("Настройки ЮKassa не заданы! Оплата будет доступна только через внутренний баланс.")
        
        # Кэш платежей
        self.pending_payments = {}
    
    async def create_payment(self, user_id: int, amount: float, description: str = "Пополнение баланса") -> Optional[Dict]:
        """
        Создание платежа через ЮKassa
        
        Args:
            user_id: ID пользователя
            amount: Сумма платежа
            description: Описание платежа
            
        Returns:
            Dict с данными платежа или None при ошибке
        """
        if not self.payment_enabled:
            logger.error("Платежи через ЮKassa отключены")
            return self._create_mock_payment(user_id, amount, description)
        
        try:
            from yookassa import Payment
            from yookassa.domain.models import Currency, ConfirmationType
            
            # Генерируем уникальный ключ
            idempotence_key = str(uuid.uuid4())
            
            # Создаем данные для платежа
            payment_data = {
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": Currency.RUB
                },
                "confirmation": {
                    "type": ConfirmationType.REDIRECT,
                    "return_url": "https://t.me/"
                },
                "capture": True,
                "description": description,
                "metadata": {
                    "user_id": str(user_id)
                }
            }
            
            # Создаем платеж
            payment = Payment.create(payment_data, idempotence_key)
            
            # Сохраняем в БД
            payment_id = str(uuid.uuid4())
            self.db.create_payment(
                user_id=user_id,
                amount=amount,
                payment_id=payment_id,
                yookassa_payment_id=payment.id
            )
            
            # Сохраняем в кэш
            self.pending_payments[payment.id] = {
                'user_id': user_id,
                'amount': amount,
                'payment_id': payment_id,
                'status': 'pending'
            }
            
            return {
                'id': payment.id,
                'status': payment.status,
                'confirmation_url': payment.confirmation.confirmation_url,
                'amount': amount,
                'description': description
            }
            
        except Exception as e:
            logger.error(f"Ошибка создания платежа через ЮKassa: {e}")
            return self._create_mock_payment(user_id, amount, description)
    
    def _create_mock_payment(self, user_id: int, amount: float, description: str) -> Dict:
        """
        Создание мок-платежа (для тестирования без ЮKassa)
        """
        payment_id = str(uuid.uuid4())
        
        # Сохраняем в БД
        self.db.create_payment(
            user_id=user_id,
            amount=amount,
            payment_id=payment_id
        )
        
        return {
            'id': payment_id,
            'status': 'mock',
            'confirmation_url': f"https://example.com/payment/{payment_id}",
            'amount': amount,
            'description': f"{description} (тестовый платеж)",
            'is_mock': True
        }
    
    def check_payment_status(self, payment_id: str) -> Optional[str]:
        """
        Проверка статуса платежа
        
        Args:
            payment_id: ID платежа
            
        Returns:
            Статус платежа или None при ошибке
        """
        if not self.payment_enabled:
            return 'succeeded'  # Для тестов всегда успешно
        
        try:
            from yookassa import Payment
            payment = Payment.find_one(payment_id)
            return payment.status
        except Exception as e:
            logger.error(f"Ошибка проверки статуса платежа: {e}")
            return None
    
    async def process_direct_payment(self, user_id: int, product_id: int, amount: float) -> Dict:
        """
        Прямой платеж за товар (списание с баланса)
        
        Args:
            user_id: ID пользователя
            product_id: ID товара
            amount: Сумма платежа
            
        Returns:
            Результат платежа
        """
        try:
            # Проверяем баланс
            user = self.db.get_user(user_id)
            if not user:
                return {'success': False, 'error': 'Пользователь не найден'}
            
            balance = user['balance']
            
            if balance < amount:
                return {
                    'success': False, 
                    'error': 'Недостаточно средств',
                    'needed': amount - balance
                }
            
            # Списываем средства
            self.db.update_user_balance(user_id, -amount)
            
            # Создаем заказ
            order_id = self.db.create_order(user_id, product_id, 1, amount)
            self.db.update_order_status(order_id, 'completed')
            
            return {
                'success': True,
                'order_id': order_id,
                'amount': amount,
                'new_balance': balance - amount
            }
            
        except Exception as e:
            logger.error(f"Ошибка прямого платежа: {e}")
            return {'success': False, 'error': str(e)}
    
    def update_payment_status(self, payment_id: str, status: str, yookassa_payment_id: Optional[str] = None):
        """Обновление статуса платежа в БД"""
        self.db.update_payment_status(payment_id, status, yookassa_payment_id)
        
        # Если платеж успешен, пополняем баланс
        if status == 'succeeded':
            payment_info = None
            for pid, info in self.pending_payments.items():
                if pid == payment_id or info.get('payment_id') == payment_id:
                    payment_info = info
                    break
            
            if payment_info:
                user_id = payment_info['user_id']
                amount = payment_info['amount']
                self.db.update_user_balance(user_id, amount)
                logger.info(f"Баланс пользователя {user_id} пополнен на {amount} руб.")
    
    def get_payment_methods(self):
        """
        Получение доступных методов оплаты
        """
        methods = [
            {
                'id': 'balance',
                'name': '💰 Баланс',
                'description': 'Оплата с внутреннего баланса',
                'fee': 0,
                'min_amount': 10,
                'max_amount': 50000
            }
        ]
        
        if self.payment_enabled:
            methods.append({
                'id': 'yookassa',
                'name': '💳 ЮKassa',
                'description': 'Карты, ЮMoney, СБП',
                'fee': 0,
                'min_amount': 10,
                'max_amount': 150000
            })
        
        return methods
    
    async def simulate_payment_webhook(self, payment_id: str):
        """
        Симуляция вебхука платежа (для тестирования)
        """
        await asyncio.sleep(2)  # Имитация задержки
        
        if payment_id in self.pending_payments:
            payment_info = self.pending_payments[payment_id]
            
            # Обновляем статус
            self.update_payment_status(payment_id, 'succeeded')
            
            # Удаляем из ожидания
            del self.pending_payments[payment_id]
            
            return True
        
        return False