import os
import logging
import asyncio
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery, InputFile,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardRemove, FSInputFile
)
from aiogram.client.default import DefaultBotProperties
import aiofiles

from config import BOT_TOKEN, ADMIN_IDS, SHOP_NAME
from database import Database
from keyboards import *
from payment import PaymentManager
from search import SearchManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Проверка папок
for folder in ['images', 'files', 'keys', 'logs']:
    if not os.path.exists(folder):
        os.makedirs(folder)
        logger.info(f"Создана папка: {folder}")

# Инициализация бота с правильными параметрами для aiogram 3.7.0+
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Инициализация компонентов
db = Database()
payment_manager = PaymentManager(db)
search_manager = SearchManager(db)

# ===== СОСТОЯНИЯ FSM =====
class AddProductStates(StatesGroup):
    name = State()
    description = State()
    price = State()
    category = State()
    tags = State()
    stock = State()
    image = State()
    file = State()

class SearchStates(StatesGroup):
    query = State()

class DepositStates(StatesGroup):
    amount = State()

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id in ADMIN_IDS

async def send_product_card(chat_id: int, product: dict, 
                          with_keyboard: bool = True, 
                          show_full_info: bool = False):
    """Отправка карточки товара"""
    try:
        # Подготовка текста
        name = product.get('name', 'Без названия')
        price = product.get('price', 0)
        category = product.get('category', 'Без категории')
        description = product.get('description', '')
        
        text = f"""
<b>📦 {name}</b>

<b>💰 Цена:</b> {price}₽
<b>📂 Категория:</b> {category}
"""
        
        if show_full_info:
            text += f"""
<b>📝 Описание:</b>
{description}

<b>🏷️ Теги:</b> {product.get('tags', 'Нет тегов') or 'Нет тегов'}
<b>📊 Наличие:</b> {'∞' if product.get('stock', -1) == -1 else product.get('stock', 0)} шт.
"""
        else:
            # Сокращенное описание
            short_desc = description[:150] + "..." if len(description) > 150 else description
            text += f"\n<b>📝 Описание:</b>\n{short_desc}\n"
        
        # Проверяем наличие изображения
        image_path = product.get('image_path')
        
        if image_path and os.path.exists(image_path):
            # Отправляем с изображением
            photo = FSInputFile(image_path)
            if with_keyboard:
                in_stock = product.get('stock', -1) != 0
                keyboard = get_product_keyboard(product['id'], price, in_stock)
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=text,
                    reply_markup=keyboard
                )
            else:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=text
                )
        else:
            # Отправляем без изображения
            if with_keyboard:
                in_stock = product.get('stock', -1) != 0
                await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=get_product_keyboard(product['id'], price, in_stock)
                )
            else:
                await bot.send_message(
                    chat_id=chat_id,
                    text=text
                )
                
    except Exception as e:
        logger.error(f"Ошибка отправки карточки товара: {e}")
        await bot.send_message(
            chat_id=chat_id,
            text=f"📦 {product.get('name', 'Товар')}\n💰 Цена: {product.get('price', 0)}₽"
        )

# ===== ОСНОВНЫЕ КОМАНДЫ =====
@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Команда /start"""
    user = message.from_user
    user_id = user.id
    
    # Регистрация пользователя
    db.add_or_update_user(
        user_id=user_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code
    )
    
    # Приветственное сообщение
    welcome_text = f"""
<b>👋 Добро пожаловать в {SHOP_NAME}!</b>

🎮 <b>Магазин цифровых товаров:</b>
• Ключи для игр 🎯
• Лицензии ПО 💻  
• Электронные книги 📚
• Онлайн-курсы 🎓
• Подписки на сервисы 🔑

<b>🔥 Преимущества:</b>
✅ Мгновенная доставка
✅ Гарантия качества  
✅ Поддержка 24/7
✅ Безопасная оплата

<b>💡 Используйте меню ниже для навигации:</b>
"""
    
    keyboard = get_admin_keyboard() if is_admin(user_id) else get_main_keyboard()
    await message.answer(welcome_text, reply_markup=keyboard)

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help"""
    help_text = f"""
<b>🆘 Помощь по боту {SHOP_NAME}</b>

<b>📋 Основные команды:</b>
/start - Перезапустить бота
/help - Показать это сообщение
/balance - Показать баланс
/catalog - Открыть каталог
/search - Поиск товаров

<b>🛒 Как купить товар:</b>
1. Выберите товар в каталоге
2. Нажмите "Купить"
3. Подтвердите покупку
4. Получите товар мгновенно!

<b>💰 Как пополнить баланс:</b>
1. Нажмите "💰 Баланс"
2. Выберите сумму пополнения
3. Оплатите через выбранный способ
4. Баланс пополнится автоматически

<b>📞 Поддержка:</b>
Если возникли проблемы:
• Напишите нам в чат поддержки
• Укажите номер заказа или платежа
• Приложите скриншот (если нужно)

<b>⚖️ Гарантии:</b>
• Возврат средств в течение 24 часов
• Замена товара при проблемах
• Конфиденциальность данных
"""
    await message.answer(help_text)

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    """Команда /admin (только для админов)"""
    user_id = message.from_user.id
    
    if is_admin(user_id):
        admin_text = f"""
<b>👑 Панель администратора</b>

<b>📊 Статистика:</b>
• /stats - Общая статистика
• /users - Список пользователей
• /orders - Все заказы

<b>📦 Управление товарами:</b>
• /add_product - Добавить товар
• /edit_product - Редактировать товар
• /delete_product - Удалить товар

<b>📢 Рассылка:</b>
• /broadcast - Отправить рассылку
• /promotion - Создать акцию

<b>⚙️ Настройки:</b>
• /settings - Настройки бота
• /backup - Создать резервную копию
"""
        await message.answer(admin_text, reply_markup=get_admin_keyboard())
    else:
        await message.answer("❌ У вас нет доступа к админ-панели.")

@dp.message(Command("balance"))
async def cmd_balance(message: Message):
    """Команда /balance"""
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if user:
        balance = user['balance']
        await message.answer(
            f"💰 <b>Ваш баланс:</b> {balance}₽\n\n"
            f"Используйте кнопку '💰 Баланс' в меню для пополнения.",
            reply_markup=get_main_keyboard()
        )
    else:
        await message.answer("❌ Ошибка: пользователь не найден.")

# ===== ОБРАБОТЧИКИ КНОПОК ГЛАВНОГО МЕНЮ =====
@dp.message(lambda message: message.text == "🛍️ Каталог")
async def show_catalog(message: Message):
    """Показать каталог товаров"""
    categories = db.get_categories()
    
    if categories:
        text = "<b>📂 Категории товаров:</b>\n\n"
        for i, category in enumerate(categories, 1):
            # Получаем количество товаров в категории
            products = db.get_all_products(category=category, limit=1000)
            count = len(products)
            text += f"{i}. {category} ({count} товаров)\n"
        
        await message.answer(
            text + "\nВыберите категорию:",
            reply_markup=get_categories_keyboard(categories)
        )
    else:
        await message.answer(
            "📭 Каталог пуст. Товары скоро появятся!",
            reply_markup=get_back_keyboard("🔙 Назад", "back_to_menu")
        )

@dp.message(lambda message: message.text == "🔍 Поиск товаров")
async def show_search(message: Message):
    """Показать поиск товаров"""
    search_text = f"""
<b>🔍 Поиск товаров</b>

Воспользуйтесь расширенным поиском, чтобы найти нужный товар:

<b>🔎 Варианты поиска:</b>
• По названию товара
• По категории
• По цене (дешевые/дорогие)
• Новинки и популярные товары

<b>🎯 Советы по поиску:</b>
• Используйте ключевые слова
• Уточняйте категорию
• Применяйте фильтры по цене
• Смотрите похожие товары
"""
    await message.answer(
        search_text,
        reply_markup=get_search_options_keyboard()
    )

@dp.message(lambda message: message.text == "🛒 Мои покупки")
async def show_my_purchases(message: Message):
    """Показать историю покупок"""
    user_id = message.from_user.id
    orders = db.get_user_orders(user_id, limit=20)
    
    if orders:
        text = "<b>📋 История ваших покупок:</b>\n\n"
        total_spent = 0
        
        for order in orders:
            order_date = order['created_at']
            if isinstance(order_date, str):
                order_date = order_date[:10]
            
            text += f"""
<b>📦 {order['product_name']}</b>
💰 Сумма: {order['total_price']}₽
📅 Дата: {order_date}
🆔 Заказ: #{order['id']}
📊 Статус: {order['status']}
{'─' * 30}
"""
            if order['status'] == 'completed':
                total_spent += order['total_price']
        
        text += f"\n<b>💰 Всего потрачено:</b> {total_spent}₽"
        
        await message.answer(text)
    else:
        await message.answer(
            "📭 У вас пока нет покупок.\n\n"
            "Перейдите в каталог, чтобы выбрать товары!",
            reply_markup=get_back_keyboard("🛍️ В каталог", "back_to_catalog")
        )

@dp.message(lambda message: message.text == "💰 Баланс")
async def show_balance(message: Message):
    """Показать баланс"""
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if user:
        balance = user['balance']
        
        text = f"""
<b>💰 Ваш баланс</b>

<b>💳 Текущий баланс:</b> {balance}₽

<b>💸 Операции:</b>
• Пополнить баланс
• Вывести средств
• История операций

<b>🎁 Бонусы:</b>
За каждые 1000₽ покупок вы получаете 50₽ на бонусный счет!
"""
        await message.answer(
            text,
            reply_markup=get_balance_keyboard()
        )
    else:
        await message.answer("❌ Ошибка: пользователь не найден.")

@dp.message(lambda message: message.text == "📞 Поддержка")
async def show_support(message: Message):
    """Показать поддержку"""
    support_text = f"""
<b>📞 Служба поддержки {SHOP_NAME}</b>

<b>🕒 Режим работы:</b> Круглосуточно, 24/7

<b>📞 Контакты:</b>
• Техподдержка: @support_username
• Email: support@example.com
• Чат в Telegram: @support_chat

<b>🚨 Экстренная помощь:</b>
Если товар не пришел или есть другие проблемы:
1. Сохраните ID заказа
2. Сделайте скриншот платежа
3. Обратитесь к оператору

<b>📋 Что нужно указать:</b>
• ID пользователя: {message.from_user.id}
• ID заказа (если есть)
• Сумма и время платежа
• Описание проблемы

<b>⏱️ Время ответа:</b>
• Обычные вопросы: до 15 минут
• Сложные вопросы: до 1 часа
• Экстренные случаи: до 30 минут
"""
    await message.answer(support_text, reply_markup=get_support_keyboard())

@dp.message(lambda message: message.text == "⚙️ Настройки")
async def show_settings(message: Message):
    """Показать настройки"""
    settings_text = f"""
<b>⚙️ Настройки бота</b>

<b>👤 Ваш профиль:</b>
ID: {message.from_user.id}
Имя: {message.from_user.first_name}
Юзернейм: @{message.from_user.username or 'не установлен'}

<b>🔔 Уведомления:</b>
• Новые товары
• Акции и скидки
• Изменение статуса заказа
• Пополнение баланса

<b>🌐 Язык интерфейса:</b>
• Русский (по умолчанию)
• English (скоро)

<b>🔐 Безопасность:</b>
• Двухфакторная аутентификация
• История входов
• Уведомления о подозрительной активности
"""
    await message.answer(settings_text, reply_markup=get_settings_keyboard())

# ===== ИНЛАЙН КНОПКИ КАТАЛОГА =====
@dp.callback_query(lambda c: c.data and c.data.startswith('cat:'))
async def process_category(callback_query: CallbackQuery):
    """Обработка выбора категории"""
    category = callback_query.data.replace('cat:', '')
    user_id = callback_query.from_user.id
    
    await callback_query.answer()
    
    if category == 'all':
        products = db.get_all_products(limit=10)
        category_name = "Все товары"
    else:
        products = db.get_all_products(category=category, limit=10)
        category_name = category
    
    if products:
        await bot.send_message(
            user_id,
            f"📦 Товары в категории '{category_name}':"
        )
        
        for product in products:
            await send_product_card(user_id, dict(product))
        
        if len(products) == 10:
            await bot.send_message(
                user_id,
                f"📄 Показано 10 из {len(products)} товаров\n"
                f"Используйте поиск для более точных результатов.",
                reply_markup=get_back_keyboard("🔙 К категориям", "back_to_categories")
            )
    else:
        await bot.send_message(
            user_id,
            f"📭 В категории '{category_name}' пока нет товаров.",
            reply_markup=get_back_keyboard("🔙 К категориям", "back_to_categories")
        )

@dp.callback_query(lambda c: c.data and c.data.startswith('prod:'))
async def process_product(callback_query: CallbackQuery):
    """Обработка выбора товара"""
    product_id = int(callback_query.data.replace('prod:', ''))
    user_id = callback_query.from_user.id
    
    await callback_query.answer()
    
    product = db.get_product(product_id)
    
    if product:
        await send_product_card(user_id, dict(product), show_full_info=True)
    else:
        await bot.send_message(
            user_id,
            "❌ Товар не найден или был удален.",
            reply_markup=get_back_keyboard("🔙 Назад", "back_to_catalog")
        )

# ===== ИНЛАЙН КНОПКИ ПОКУПКИ =====
@dp.callback_query(lambda c: c.data and c.data.startswith('buy:'))
async def process_buy(callback_query: CallbackQuery):
    """Обработка покупки товара"""
    product_id = int(callback_query.data.replace('buy:', ''))
    user_id = callback_query.from_user.id
    
    await callback_query.answer()
    
    product = db.get_product(product_id)
    
    if not product:
        await bot.send_message(
            user_id,
            "❌ Товар не найден.",
            reply_markup=get_back_keyboard("🔙 Назад", "back_to_catalog")
        )
        return
    
    # Проверяем наличие
    if product.get('stock', -1) == 0:
        await bot.send_message(
            user_id,
            f"❌ Товар '{product['name']}' временно отсутствует.\n"
            f"Попробуйте позже или выберите другой товар.",
            reply_markup=get_back_keyboard("🔙 Назад", "back_to_catalog")
        )
        return
    
    # Проверяем баланс
    user = db.get_user(user_id)
    if not user:
        await bot.send_message(user_id, "❌ Ошибка: пользователь не найден.")
        return
    
    balance = user['balance']
    price = product['price']
    
    if balance >= price:
        # Показываем подтверждение покупки
        await bot.send_message(
            user_id,
            f"✅ Подтвердите покупку:\n\n"
            f"📦 Товар: {product['name']}\n"
            f"💰 Цена: {price}₽\n"
            f"💳 Ваш баланс: {balance}₽\n"
            f"💸 После покупки: {balance - price}₽\n\n"
            f"<b>⚠️ После подтверждения средства будут списаны!</b>",
            reply_markup=get_buy_confirmation_keyboard(product_id)
        )
    else:
        # Предлагаем пополнить баланс
        needed = price - balance
        await bot.send_message(
            user_id,
            f"❌ Недостаточно средств!\n\n"
            f"💰 Нужно: {price}₽\n"
            f"💳 У вас: {balance}₽\n"
            f"📊 Не хватает: {needed}₽\n\n"
            f"Пополните баланс для покупки.",
            reply_markup=get_balance_keyboard()
        )

@dp.callback_query(lambda c: c.data and c.data.startswith('confirm_buy:'))
async def process_confirm_buy(callback_query: CallbackQuery):
    """Подтверждение покупки"""
    data = callback_query.data.replace('confirm_buy:', '')
    parts = data.split(':')
    product_id = int(parts[0])
    quantity = int(parts[1]) if len(parts) > 1 else 1
    user_id = callback_query.from_user.id
    
    await callback_query.answer()
    
    product = db.get_product(product_id)
    
    if not product:
        await bot.send_message(user_id, "❌ Товар не найден.")
        return
    
    # Обрабатываем платеж
    amount = product['price'] * quantity
    payment_result = await payment_manager.process_direct_payment(user_id, product_id, amount)
    
    if payment_result.get('success'):
        # Отправляем товар
        file_path = product.get('file_path')
        
        if file_path and os.path.exists(file_path):
            if file_path.endswith('.txt'):
                # Текстовый товар (ключ)
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    key_content = await f.read()
                
                success_message = f"""
🎉 <b>Покупка успешна!</b>

🆔 Заказ: #{payment_result.get('order_id', 'N/A')}
📦 Товар: {product['name']}
💰 Сумма: {amount}₽
💳 Новый баланс: {payment_result.get('new_balance', 0)}₽

🔑 <b>Ваш ключ/данные:</b>
<code>{key_content}</code>

⚠️ <b>Сохраните эту информацию!</b>
• Ключ действителен один раз
• Не передавайте его третьим лицам
• В случае проблем обратитесь в поддержку
"""
                await bot.send_message(
                    user_id,
                    success_message
                )
            else:
                # Файловый товар
                file = FSInputFile(file_path)
                await bot.send_document(
                    user_id,
                    document=file,
                    caption=f"🎉 Покупка успешна! Заказ #{payment_result.get('order_id', 'N/A')}"
                )
        else:
            # Товар без файла (виртуальный)
            await bot.send_message(
                user_id,
                f"🎉 Покупка успешна! Заказ #{payment_result.get('order_id', 'N/A')}\n\n"
                f"Администратор свяжется с вами для выдачи товара."
            )
        
        # Обновляем количество товара
        if product.get('stock', -1) > 0:
            try:
                db.cursor.execute('UPDATE products SET stock = stock - ? WHERE id = ?', (quantity, product_id))
                db.conn.commit()
            except Exception as e:
                logger.error(f"Ошибка обновления количества товара: {e}")
    
    else:
        # Ошибка платежа
        error_msg = payment_result.get('error', 'Неизвестная ошибка')
        await bot.send_message(
            user_id,
            f"❌ Ошибка при покупке: {error_msg}"
        )

# ===== ИНЛАЙН КНОПКИ БАЛАНСА =====
@dp.callback_query(lambda c: c.data and c.data.startswith('deposit:'))
async def process_deposit(callback_query: CallbackQuery):
    """Обработка пополнения баланса"""
    data = callback_query.data.replace('deposit:', '')
    user_id = callback_query.from_user.id
    
    await callback_query.answer()
    
    if data == 'custom':
        # Запрос произвольной суммы
        await callback_query.message.answer(
            "💳 Введите сумму для пополнения (в рублях):\n\n"
            "Минимальная сумма: 10₽\n"
            "Максимальная сумма: 15000₽",
            reply_markup=get_cancel_keyboard()
        )
        # Устанавливаем состояние
        await dp.storage.set_state(user=user_id, state=DepositStates.amount)
        return
    
    try:
        amount = float(data)
        
        if amount < 10 or amount > 15000:
            await bot.send_message(
                user_id,
                "❌ Сумма должна быть от 10 до 15000 рублей."
            )
            return
        
        # Создаем платеж
        payment = await payment_manager.create_payment(
            user_id=user_id,
            amount=amount,
            description=f"Пополнение баланса {SHOP_NAME}"
        )
        
        if payment:
            payment_url = payment.get('confirmation_url', '')
            
            if payment.get('is_mock'):
                # Тестовый платеж
                await bot.send_message(
                    user_id,
                    f"💳 <b>Пополнение баланса (тестовый режим)</b>\n\n"
                    f"💰 Сумма: {amount}₽\n"
                    f"📊 Комиссия: 0₽\n"
                    f"💸 Итого к оплате: {amount}₽\n\n"
                    f"<b>Для пополнения баланса:</b>\n"
                    f"1. Свяжитесь с администратором @admin\n"
                    f"2. Укажите сумму: {amount}₽\n"
                    f"3. Ваш ID: {user_id}\n\n"
                    f"✅ Баланс будет пополнен после подтверждения платежа.",
                    reply_markup=get_back_keyboard("🔙 К балансу", "back_to_balance")
                )
            else:
                # Реальный платеж через ЮKassa
                await bot.send_message(
                    user_id,
                    f"💳 <b>Пополнение баланса</b>\n\n"
                    f"💰 Сумма: {amount}₽\n"
                    f"📊 Комиссия: 0₽\n"
                    f"💸 Итого к оплате: {amount}₽\n\n"
                    f"<b>Для оплаты перейдите по ссылке:</b>\n"
                    f"{payment_url}\n\n"
                    f"✅ После оплаты баланс пополнится автоматически.",
                    reply_markup=get_back_keyboard("🔙 К балансу", "back_to_balance")
                )
        else:
            await bot.send_message(
                user_id,
                "❌ Ошибка при создании платежа. Попробуйте позже."
            )
            
    except ValueError:
        await bot.send_message(user_id, "❌ Неверный формат суммы.")

@dp.message(DepositStates.amount)
async def process_deposit_amount(message: Message, state: FSMContext):
    """Обработка произвольной суммы пополнения"""
    try:
        amount = float(message.text)
        
        if amount < 10:
            await message.answer("❌ Минимальная сумма - 10 рублей.")
            await state.clear()
            return
        if amount > 15000:
            await message.answer("❌ Максимальная сумма - 15000 рублей.")
            await state.clear()
            return
        
        # Создаем платеж
        payment = await payment_manager.create_payment(
            user_id=message.from_user.id,
            amount=amount,
            description=f"Пополнение баланса {SHOP_NAME}"
        )
        
        if payment:
            if payment.get('is_mock'):
                # Тестовый платеж
                await message.answer(
                    f"💳 <b>Пополнение баланса (тестовый режим)</b>\n\n"
                    f"💰 Сумма: {amount}₽\n\n"
                    f"<b>Для пополнения баланса:</b>\n"
                    f"1. Свяжитесь с администратором @admin\n"
                    f"2. Укажите сумму: {amount}₽\n"
                    f"3. Ваш ID: {message.from_user.id}\n\n"
                    f"✅ Баланс будет пополнен после подтверждения платежа.",
                    reply_markup=get_main_keyboard()
                )
            else:
                # Реальный платеж
                await message.answer(
                    f"💳 <b>Пополнение баланса</b>\n\n"
                    f"💰 Сумма: {amount}₽\n"
                    f"📊 Комиссия: 0₽\n"
                    f"💸 Итого к оплате: {amount}₽\n\n"
                    f"<b>Для оплаты перейдите по ссылке:</b>\n"
                    f"{payment.get('confirmation_url', '')}\n\n"
                    f"✅ После оплаты баланс пополнится автоматически.",
                    reply_markup=get_main_keyboard()
                )
        else:
            await message.answer(
                "❌ Ошибка при создании платежа. Попробуйте позже.",
                reply_markup=get_main_keyboard()
            )
    
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректную сумму (число).",
            reply_markup=get_main_keyboard()
        )
    
    await state.clear()

# ===== ИНЛАЙН КНОПКИ ПОИСКА =====
@dp.callback_query(lambda c: c.data == 'search_by_name')
async def search_by_name_start(callback_query: CallbackQuery):
    """Начало поиска по названию"""
    user_id = callback_query.from_user.id
    
    await callback_query.answer()
    
    # Получаем популярные запросы
    popular = search_manager.get_popular_searches(5)
    popular_text = "\n".join([f"• {item['query']} ({item['count']})" for item in popular])
    
    await callback_query.message.answer(
        f"🔍 <b>Поиск по названию</b>\n\n"
        f"Введите название товара для поиска:\n\n"
        f"<b>🔥 Популярные запросы:</b>\n"
        f"{popular_text}\n\n"
        f"💡 <b>Советы:</b>\n"
        f"• Используйте конкретные названия\n"
        f"• Проверьте орфографию\n"
        f"• Попробуйте синонимы",
        reply_markup=get_cancel_keyboard()
    )
    
    # Устанавливаем состояние
    await dp.storage.set_state(user=user_id, state=SearchStates.query)

@dp.message(SearchStates.query)
async def process_search_query(message: Message, state: FSMContext):
    """Обработка поискового запроса"""
    query = message.text.strip()
    user_id = message.from_user.id
    
    if len(query) < 2:
        await message.answer(
            "❌ Слишком короткий запрос. Введите минимум 2 символа.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
        return
    
    # Получаем подсказки
    suggestions = search_manager.get_search_suggestions(query)
    
    if suggestions:
        suggestions_text = "\n".join([f"• {s}" for s in suggestions[:3]])
        await message.answer(
            f"💡 <b>Возможно, вы ищете:</b>\n{suggestions_text}"
        )
    
    # Выполняем поиск
    products, total_count, metadata = search_manager.search_products(
        user_id=user_id,
        query=query,
        page=0,
        per_page=5
    )
    
    if products:
        await message.answer(
            f"🔍 <b>Результаты поиска</b>\n\n"
            f"📊 Найдено товаров: {total_count}\n"
            f"🔎 Запрос: \"{query}\"\n"
            f"📄 Страница: {metadata.get('page', 0) + 1}/{metadata.get('total_pages', 1) or 1}",
            reply_markup=get_main_keyboard()
        )
        
        for product in products:
            await send_product_card(user_id, product)
        
        if metadata.get('has_next'):
            await message.answer(
                "📄 Для просмотра следующих товаров уточните запрос.",
                reply_markup=get_search_filters_keyboard()
            )
    else:
        await message.answer(
            f"❌ По запросу \"{query}\" ничего не найдено.\n\n"
            f"💡 <b>Попробуйте:</b>\n"
            f"• Изменить запрос\n"
            f"• Использовать другие ключевые слова\n"
            f"• Посмотреть все товары в каталоге",
            reply_markup=get_search_options_keyboard()
        )
    
    await state.clear()

@dp.callback_query(lambda c: c.data == 'search_by_category')
async def search_by_category(callback_query: CallbackQuery):
    """Поиск по категории"""
    user_id = callback_query.from_user.id
    
    await callback_query.answer()
    
    categories = db.get_categories()
    if categories:
        await callback_query.message.answer(
            "📂 Выберите категорию для поиска:",
            reply_markup=get_categories_keyboard(categories, show_all=False)
        )
    else:
        await callback_query.message.answer(
            "❌ Категории не найдены."
        )

@dp.callback_query(lambda c: c.data == 'search_cheap')
async def search_cheap_products(callback_query: CallbackQuery):
    """Поиск дешевых товаров"""
    user_id = callback_query.from_user.id
    
    await callback_query.answer()
    
    products = search_manager.search_cheap_products(max_price=500, limit=10)
    
    if products:
        await callback_query.message.answer(
            "💰 Дешевые товары (до 500₽):"
        )
        
        for product in products:
            await send_product_card(user_id, product)
    else:
        await callback_query.message.answer(
            "❌ Дешевые товары не найдены."
        )

# ===== АДМИН ФУНКЦИИ =====
@dp.message(lambda message: message.text == "📦 Добавить товар")
async def add_product_start(message: Message):
    """Начало добавления товара (админ)"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("❌ У вас нет доступа к этой функции.")
        return
    
    await message.answer(
        "📦 Добавление нового товара\n\n"
        "Введите название товара:",
        reply_markup=get_cancel_keyboard()
    )
    
    # Устанавливаем состояние
    await dp.storage.set_state(user=user_id, state=AddProductStates.name)

@dp.message(AddProductStates.name)
async def process_product_name(message: Message, state: FSMContext):
    """Обработка названия товара"""
    await state.update_data(name=message.text)
    await state.set_state(AddProductStates.description)
    await message.answer("Введите описание товара:")

@dp.message(AddProductStates.description)
async def process_product_description(message: Message, state: FSMContext):
    """Обработка описания товара"""
    await state.update_data(description=message.text)
    await state.set_state(AddProductStates.price)
    await message.answer("Введите цену товара (в рублях):")

@dp.message(AddProductStates.price)
async def process_product_price(message: Message, state: FSMContext):
    """Обработка цены товара"""
    try:
        price = float(message.text)
        
        if price <= 0:
            await message.answer("❌ Цена должна быть больше 0. Введите снова:")
            return
        
        await state.update_data(price=price)
        await state.set_state(AddProductStates.category)
        
        # Показываем существующие категории
        categories = db.get_categories()
        categories_text = "\n".join([f"• {cat}" for cat in categories[:10]]) if categories else "Категорий пока нет"
        
        await message.answer(
            f"Введите категорию товара:\n\n"
            f"📂 Существующие категории:\n"
            f"{categories_text}\n\n"
            f"Или введите новую категорию:"
        )
        
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректную цену (число):")

@dp.message(AddProductStates.category)
async def process_product_category(message: Message, state: FSMContext):
    """Обработка категории товара"""
    await state.update_data(category=message.text)
    await state.set_state(AddProductStates.tags)
    await message.answer(
        "Введите теги для поиска (через запятую):\n\n"
        "Пример: игра, steam, ключ, аккаунт\n"
        "Или отправьте '-', чтобы пропустить:"
    )

@dp.message(AddProductStates.tags)
async def process_product_tags(message: Message, state: FSMContext):
    """Обработка теги товара"""
    tags = message.text.strip()
    tags = tags if tags != '-' else None
    await state.update_data(tags=tags)
    await state.set_state(AddProductStates.stock)
    await message.answer(
        "Введите количество товара на складе:\n\n"
        "Введите число или '-1' для неограниченного количества:"
    )

@dp.message(AddProductStates.stock)
async def process_product_stock(message: Message, state: FSMContext):
    """Обработка количества товара"""
    try:
        stock = int(message.text)
        await state.update_data(stock=stock)
        await state.set_state(AddProductStates.image)
        await message.answer("Отправьте изображение товара:")
        
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректное число:")

@dp.message(AddProductStates.image, lambda message: message.photo)
async def process_product_image(message: Message, state: FSMContext):
    """Обработка изображения товара"""
    # Сохраняем изображение
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    
    # Создаем уникальное имя файла
    timestamp = int(datetime.now().timestamp())
    filename = f"product_{timestamp}_{photo.file_id}.jpg"
    file_path = f"images/{filename}"
    
    await bot.download_file(file.file_path, file_path)
    
    await state.update_data(image_path=file_path)
    await state.set_state(AddProductStates.file)
    await message.answer(
        "Отправьте файл товара или текст ключа:\n\n"
        "Для текстовых товаров (ключей) отправьте текст\n"
        "Для файловых товаров отправьте файл\n"
        "Для виртуальных товаров отправьте '-'"
    )

@dp.message(AddProductStates.file)
async def process_product_file(message: Message, state: FSMContext):
    """Обработка файла товара"""
    file_path = None
    
    if message.document:
        # Сохраняем файл
        file = await bot.get_file(message.document.file_id)
        
        timestamp = int(datetime.now().timestamp())
        filename = message.document.file_name
        file_path = f"files/{timestamp}_{filename}"
        
        await bot.download_file(file.file_path, file_path)
    
    elif message.text:
        text = message.text.strip()
        
        if text != '-':
            # Сохраняем текст как файл
            timestamp = int(datetime.now().timestamp())
            file_path = f"keys/product_{timestamp}.txt"
            
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(text)
    
    data = await state.get_data()
    
    # Добавляем товар в БД
    product_id = db.add_product(
        name=data['name'],
        description=data['description'],
        price=data['price'],
        image_path=data.get('image_path'),
        file_path=file_path,
        category=data['category'],
        tags=data.get('tags'),
        stock=data['stock']
    )
    
    await state.clear()
    
    # Отправляем подтверждение
    success_text = f"""
✅ <b>Товар успешно добавлен!</b>

🆔 ID товара: {product_id}
📦 Название: {data['name']}
💰 Цена: {data['price']}₽
📂 Категория: {data['category']}
📊 Наличие: {'∞' if data['stock'] == -1 else data['stock']} шт.

💡 Товар теперь доступен в каталоге!
"""
    await message.answer(success_text, reply_markup=get_admin_keyboard())

@dp.message(lambda message: message.text == "📊 Статистика")
async def show_admin_stats(message: Message):
    """Показать статистику (админ)"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("❌ У вас нет доступа к этой функции.")
        return
    
    stats = db.get_statistics()
    
    stats_text = f"""
📊 <b>Статистика магазина</b>

👥 <b>Пользователи:</b>
• Всего: {stats.get('users_count', 0)}
• Новых за сутки: (скоро)

📦 <b>Товары:</b>
• Всего: {stats.get('products_count', 0)}
• Активных: {stats.get('products_count', 0)}

🛒 <b>Заказы:</b>
• Всего: {stats.get('orders_count', 0)}
• За сутки: (скоро)

💰 <b>Финансы:</b>
• Выручка: {stats.get('revenue', 0):.2f}₽
• Средний чек: (скоро)

🔍 <b>Поиск:</b>
• Популярные запросы: (скоро)
• Конверсия: (скоро)
"""
    await message.answer(stats_text)

# ===== ОБРАБОТКА ОТМЕНЫ =====
@dp.message(lambda message: message.text == "❌ Отмена")
async def cancel_handler(message: Message, state: FSMContext):
    """Обработка отмены"""
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
    
    await message.answer(
        "Действие отменено.",
        reply_markup=get_main_keyboard()
    )

# ===== ОБРАБОТКА ВСЕХ СООБЩЕНИЙ =====
@dp.message()
async def handle_all_messages(message: Message):
    """Обработка всех сообщений"""
    user_id = message.from_user.id
    
    # Если пользователь админ и отправил команду возврата
    if message.text == "🔙 В меню" and is_admin(user_id):
        await message.answer(
            "Возврат в главное меню.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Если сообщение не распознано
    if message.text and not message.text.startswith('/'):
        await message.answer(
            "🤔 Я не понял вашу команду.\n"
            "Используйте меню ниже или команду /help",
            reply_markup=get_main_keyboard()
        )

# ===== ОБРАБОТКА ОШИБОК =====
@dp.error()
async def errors_handler(update, exception):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {exception}")
    return True

# ===== ЗАПУСК БОТА =====
async def main():
    logger.info("🚀 Бот запускается...")
    
    try:
        # Запуск поллинга
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        # Закрытие соединений
        if hasattr(db, 'conn'):
            db.conn.close()
        logger.info("Бот остановлен.")

if __name__ == '__main__':
    asyncio.run(main())