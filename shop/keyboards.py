from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    ReplyKeyboardRemove
)

# ===== РЕПЛИКЛАВИАТУРЫ =====
def get_main_keyboard():
    """Основная клавиатура"""
    buttons = [
        [KeyboardButton(text="🛍️ Каталог"), KeyboardButton(text="🔍 Поиск товаров")],
        [KeyboardButton(text="🛒 Мои покупки"), KeyboardButton(text="💰 Баланс")],
        [KeyboardButton(text="📞 Поддержка"), KeyboardButton(text="⚙️ Настройки")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_admin_keyboard():
    """Клавиатура администратора"""
    buttons = [
        [KeyboardButton(text="📦 Добавить товар"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="📢 Рассылка"), KeyboardButton(text="👥 Пользователи")],
        [KeyboardButton(text="📈 Отчеты"), KeyboardButton(text="🔙 В меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_cancel_keyboard():
    """Клавиатура отмены"""
    buttons = [[KeyboardButton(text="❌ Отмена")]]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def remove_keyboard():
    """Удаление клавиатуры"""
    return ReplyKeyboardRemove()

# ===== ИНЛАЙН КЛАВИАТУРЫ =====
def get_categories_keyboard(categories, show_all=True):
    """Клавиатура категорий"""
    buttons = []
    row = []
    
    for i, category in enumerate(categories):
        row.append(InlineKeyboardButton(text=category, callback_data=f"cat:{category}"))
        if len(row) == 2 or i == len(categories) - 1:
            buttons.append(row)
            row = []
    
    if show_all:
        buttons.append([InlineKeyboardButton(text="📋 Все товары", callback_data="cat:all")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_products_keyboard(products, page=0, per_page=5, has_next=False):
    """Клавиатура товаров"""
    buttons = []
    
    # Кнопки товаров
    for product in products:
        buttons.append([
            InlineKeyboardButton(
                text=f"📦 {product['name'][:20]} - {product['price']}₽",
                callback_data=f"prod:{product['id']}"
            )
        ])
    
    # Кнопки навигации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"page:{page-1}"))
    
    if has_next:
        nav_buttons.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"page:{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_product_keyboard(product_id, price, in_stock=True):
    """Клавиатура для просмотра товара"""
    buttons = []
    
    if in_stock:
        buttons.append([
            InlineKeyboardButton(text=f"🛒 Купить за {price}₽", callback_data=f"buy:{product_id}")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="❌ Нет в наличии", callback_data="no_stock")
        ])
    
    buttons.append([
        InlineKeyboardButton(text="🔙 Назад к каталогу", callback_data="back_to_catalog"),
        InlineKeyboardButton(text="🔍 Похожие товары", callback_data=f"similar:{product_id}")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_buy_confirmation_keyboard(product_id, quantity=1):
    """Клавиатура подтверждения покупки"""
    buttons = [
        [
            InlineKeyboardButton(text="➖", callback_data=f"dec_qty:{product_id}"),
            InlineKeyboardButton(text=f"Кол-во: {quantity}", callback_data="noop"),
            InlineKeyboardButton(text="➕", callback_data=f"inc_qty:{product_id}")
        ],
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_buy:{product_id}:{quantity}"),
            InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_buy")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_payment_methods_keyboard(amount):
    """Клавиатура выбора способа оплаты"""
    buttons = [
        [
            InlineKeyboardButton(text="💳 Банковская карта", callback_data=f"pay_card:{amount}"),
            InlineKeyboardButton(text="🪙 Криптовалюта", callback_data=f"pay_crypto:{amount}")
        ],
        [
            InlineKeyboardButton(text="📱 ЮMoney", callback_data=f"pay_yoomoney:{amount}"),
            InlineKeyboardButton(text="🤝 P2P перевод", callback_data=f"pay_p2p:{amount}")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_balance")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_balance_keyboard():
    """Клавиатура для работы с балансом"""
    buttons = [
        [
            InlineKeyboardButton(text="+100₽", callback_data="deposit:100"),
            InlineKeyboardButton(text="+500₽", callback_data="deposit:500"),
            InlineKeyboardButton(text="+1000₽", callback_data="deposit:1000")
        ],
        [
            InlineKeyboardButton(text="+2000₽", callback_data="deposit:2000"),
            InlineKeyboardButton(text="+5000₽", callback_data="deposit:5000"),
            InlineKeyboardButton(text="Другая сумма", callback_data="deposit:custom")
        ],
        [
            InlineKeyboardButton(text="📜 История пополнений", callback_data="payment_history"),
            InlineKeyboardButton(text="💸 Вывод средств", callback_data="withdraw")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_search_options_keyboard():
    """Клавиатура опций поиска"""
    buttons = [
        [
            InlineKeyboardButton(text="🔍 По названию", callback_data="search_by_name"),
            InlineKeyboardButton(text="🏷️ По категории", callback_data="search_by_category")
        ],
        [
            InlineKeyboardButton(text="💰 Дешевые товары", callback_data="search_cheap"),
            InlineKeyboardButton(text="💎 Дорогие товары", callback_data="search_expensive")
        ],
        [
            InlineKeyboardButton(text="⭐ Новинки", callback_data="search_new"),
            InlineKeyboardButton(text="🔥 Популярные", callback_data="search_popular")
        ],
        [
            InlineKeyboardButton(text="🔙 В меню", callback_data="back_to_menu")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_search_filters_keyboard():
    """Клавиатура фильтров поиска"""
    buttons = [
        [
            InlineKeyboardButton(text="💵 По цене", callback_data="filter_price"),
            InlineKeyboardButton(text="📂 По категории", callback_data="filter_category")
        ],
        [
            InlineKeyboardButton(text="🏷️ По тегам", callback_data="filter_tags"),
            InlineKeyboardButton(text="📊 По наличию", callback_data="filter_stock")
        ],
        [
            InlineKeyboardButton(text="🔍 Начать поиск", callback_data="start_search"),
            InlineKeyboardButton(text="🗑️ Сбросить фильтры", callback_data="reset_filters")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_price_filters_keyboard():
    """Клавиатура фильтров по цене"""
    buttons = [
        [
            InlineKeyboardButton(text="💰 До 100₽", callback_data="price_0_100"),
            InlineKeyboardButton(text="💰 100-500₽", callback_data="price_100_500")
        ],
        [
            InlineKeyboardButton(text="💰 500-1000₽", callback_data="price_500_1000"),
            InlineKeyboardButton(text="💰 1000-5000₽", callback_data="price_1000_5000")
        ],
        [
            InlineKeyboardButton(text="💰 От 5000₽", callback_data="price_5000_up"),
            InlineKeyboardButton(text="💰 Любая цена", callback_data="price_any")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_support_keyboard():
    """Клавиатура поддержки"""
    buttons = [
        [
            InlineKeyboardButton(text="📞 Связаться с поддержкой", url="https://t.me/username"),
            InlineKeyboardButton(text="📚 Частые вопросы", callback_data="faq")
        ],
        [
            InlineKeyboardButton(text="📋 Правила магазина", callback_data="rules"),
            InlineKeyboardButton(text="⚖️ Гарантии", callback_data="guarantees")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_settings_keyboard():
    """Клавиатура настроек"""
    buttons = [
        [
            InlineKeyboardButton(text="🔔 Уведомления", callback_data="settings_notifications"),
            InlineKeyboardButton(text="🌐 Язык", callback_data="settings_language")
        ],
        [
            InlineKeyboardButton(text="🔐 Безопасность", callback_data="settings_security"),
            InlineKeyboardButton(text="📱 Тема", callback_data="settings_theme")
        ],
        [
            InlineKeyboardButton(text="🗑️ Удалить историю", callback_data="clear_history"),
            InlineKeyboardButton(text="📤 Экспорт данных", callback_data="export_data")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_back_keyboard(text="🔙 Назад", callback_data="back"):
    """Универсальная кнопка назад"""
    buttons = [[InlineKeyboardButton(text=text, callback_data=callback_data)]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)