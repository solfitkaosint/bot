import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ID администраторов
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_ID", "").split(",") if id.strip()]

# Настройки ЮKassa
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")

# Название магазина
SHOP_NAME = os.getenv("SHOP_NAME", "Digital Shop")

# Настройки базы данных
DB_NAME = "shop.db"

# Проверка обязательных переменных
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле!")

if not ADMIN_IDS:
    print("⚠️ ADMIN_ID не задан! Админские функции будут недоступны.")

if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
    print("⚠️ Настройки ЮKassa не заданы! Оплата будет недоступна.")