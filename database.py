import sqlite3
import logging
import json
from datetime import datetime
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name="shop.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self.init_database()
    
    def connect(self):
        """Подключение к базе данных"""
        self.conn = sqlite3.connect(self.db_name)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
    
    def close(self):
        """Закрытие соединения с БД"""
        if self.conn:
            self.conn.close()
    
    def commit(self):
        """Сохранение изменений"""
        if self.conn:
            self.conn.commit()
    
    def init_database(self):
        """Инициализация базы данных"""
        self.connect()
        
        # Таблица пользователей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language_code TEXT,
                is_admin BOOLEAN DEFAULT 0,
                balance REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица товаров
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                image_path TEXT,
                file_path TEXT,
                category TEXT,
                tags TEXT,
                is_active BOOLEAN DEFAULT 1,
                stock INTEGER DEFAULT -1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица заказов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                total_price REAL NOT NULL,
                payment_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        
        # Таблица платежей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                payment_id TEXT UNIQUE,
                amount REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                yookassa_payment_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица поисковых запросов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                query TEXT NOT NULL,
                results_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        self.commit()
        logger.info("База данных инициализирована")
    
    # === Методы для работы с пользователями ===
    def add_or_update_user(self, user_id, username, first_name, last_name, language_code):
        """Добавление или обновление пользователя"""
        self.connect()
        try:
            self.cursor.execute('''
                INSERT INTO users (user_id, username, first_name, last_name, language_code, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_name = excluded.last_name,
                    language_code = excluded.language_code,
                    updated_at = CURRENT_TIMESTAMP
            ''', (user_id, username, first_name, last_name, language_code))
            self.commit()
        except Exception as e:
            logger.error(f"Ошибка добавления пользователя: {e}")
            raise
    
    def get_user(self, user_id):
        """Получение пользователя"""
        self.connect()
        try:
            self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            result = self.cursor.fetchone()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Ошибка получения пользователя: {e}")
            return None
    
    def update_user_balance(self, user_id, amount):
        """Обновление баланса пользователя"""
        self.connect()
        try:
            self.cursor.execute('''
                UPDATE users 
                SET balance = balance + ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (amount, user_id))
            self.commit()
        except Exception as e:
            logger.error(f"Ошибка обновления баланса: {e}")
            raise
    
    # === Методы для работы с товарами ===
    def add_product(self, name, description, price, image_path, file_path, category, tags=None, stock=-1):
        """Добавление товара"""
        self.connect()
        try:
            tags_json = json.dumps(tags) if tags else '[]'
            self.cursor.execute('''
                INSERT INTO products (name, description, price, image_path, file_path, category, tags, stock)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, description, price, image_path, file_path, category, tags_json, stock))
            self.commit()
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Ошибка добавления товара: {e}")
            raise
    
    def get_product(self, product_id):
        """Получение товара по ID"""
        self.connect()
        try:
            self.cursor.execute('SELECT * FROM products WHERE id = ? AND is_active = 1', (product_id,))
            result = self.cursor.fetchone()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Ошибка получения товара: {e}")
            return None
    
    def get_all_products(self, category=None, limit=50, offset=0):
        """Получение всех товаров"""
        self.connect()
        try:
            if category:
                self.cursor.execute('''
                    SELECT * FROM products 
                    WHERE is_active = 1 AND category = ?
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                ''', (category, limit, offset))
            else:
                self.cursor.execute('''
                    SELECT * FROM products 
                    WHERE is_active = 1 
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                ''', (limit, offset))
            results = self.cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Ошибка получения товаров: {e}")
            return []
    
    def get_categories(self):
        """Получение всех категорий"""
        self.connect()
        try:
            self.cursor.execute('''
                SELECT DISTINCT category 
                FROM products 
                WHERE is_active = 1 AND category IS NOT NULL AND category != ''
                ORDER BY category
            ''')
            results = self.cursor.fetchall()
            return [row['category'] for row in results if row['category']]
        except Exception as e:
            logger.error(f"Ошибка получения категорий: {e}")
            return []
    
    # === Методы для поиска товаров ===
    def search_products(self, query, category=None, min_price=None, max_price=None, limit=20, offset=0):
        """Поиск товаров по запросу"""
        self.connect()
        try:
            # Базовый запрос
            sql = '''
                SELECT * FROM products 
                WHERE is_active = 1 
                AND (name LIKE ? OR description LIKE ? OR tags LIKE ?)
            '''
            params = [f'%{query}%', f'%{query}%', f'%{query}%']
            
            # Добавляем фильтры
            if category:
                sql += ' AND category = ?'
                params.append(category)
            
            if min_price is not None:
                sql += ' AND price >= ?'
                params.append(min_price)
            
            if max_price is not None:
                sql += ' AND price <= ?'
                params.append(max_price)
            
            # Сортировка и лимит
            sql += ' ORDER BY name LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            self.cursor.execute(sql, params)
            results = self.cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Ошибка поиска товаров: {e}")
            return []
    
    def save_search_query(self, user_id, query, results_count):
        """Сохранение поискового запроса"""
        self.connect()
        try:
            self.cursor.execute('''
                INSERT INTO search_history (user_id, query, results_count)
                VALUES (?, ?, ?)
            ''', (user_id, query, results_count))
            self.commit()
        except Exception as e:
            logger.error(f"Ошибка сохранения поиска: {e}")
    
    # === Методы для работы с заказами ===
    def create_order(self, user_id, product_id, quantity, total_price, payment_id=None):
        """Создание заказа"""
        self.connect()
        try:
            self.cursor.execute('''
                INSERT INTO orders (user_id, product_id, quantity, total_price, payment_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, product_id, quantity, total_price, payment_id))
            self.commit()
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Ошибка создания заказа: {e}")
            raise
    
    def update_order_status(self, order_id, status):
        """Обновление статуса заказа"""
        self.connect()
        try:
            self.cursor.execute('''
                UPDATE orders 
                SET status = ?, 
                    completed_at = CASE WHEN status != 'completed' AND ? = 'completed' THEN CURRENT_TIMESTAMP ELSE completed_at END
                WHERE id = ?
            ''', (status, status, order_id))
            self.commit()
        except Exception as e:
            logger.error(f"Ошибка обновления заказа: {e}")
            raise
    
    def get_user_orders(self, user_id, limit=20):
        """Получение заказов пользователя"""
        self.connect()
        try:
            self.cursor.execute('''
                SELECT o.*, p.name as product_name, p.category
                FROM orders o
                JOIN products p ON o.product_id = p.id
                WHERE o.user_id = ?
                ORDER BY o.created_at DESC
                LIMIT ?
            ''', (user_id, limit))
            results = self.cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Ошибка получения заказов: {e}")
            return []
    
    # === Методы для работы с платежами ===
    def create_payment(self, user_id, amount, payment_id, yookassa_payment_id=None):
        """Создание записи о платеже"""
        self.connect()
        try:
            self.cursor.execute('''
                INSERT INTO payments (user_id, amount, payment_id, yookassa_payment_id)
                VALUES (?, ?, ?, ?)
            ''', (user_id, amount, payment_id, yookassa_payment_id))
            self.commit()
        except Exception as e:
            logger.error(f"Ошибка создания платежа: {e}")
            raise
    
    def update_payment_status(self, payment_id, status, yookassa_payment_id=None):
        """Обновление статуса платежа"""
        self.connect()
        try:
            self.cursor.execute('''
                UPDATE payments 
                SET status = ?, 
                    yookassa_payment_id = COALESCE(?, yookassa_payment_id),
                    updated_at = CURRENT_TIMESTAMP
                WHERE payment_id = ?
            ''', (status, yookassa_payment_id, payment_id))
            self.commit()
        except Exception as e:
            logger.error(f"Ошибка обновления платежа: {e}")
            raise
    
    def get_pending_payments(self):
        """Получение ожидающих платежей"""
        self.connect()
        try:
            self.cursor.execute('''
                SELECT * FROM payments 
                WHERE status = 'pending' 
                AND created_at > datetime('now', '-1 hour')
            ''')
            results = self.cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Ошибка получения платежей: {e}")
            return []
    
    # === Статистика ===
    def get_statistics(self):
        """Получение статистики магазина"""
        self.connect()
        try:
            stats = {}
            
            # Количество пользователей
            self.cursor.execute('SELECT COUNT(*) as count FROM users')
            result = self.cursor.fetchone()
            stats['users_count'] = result['count'] if result else 0
            
            # Количество товаров
            self.cursor.execute('SELECT COUNT(*) as count FROM products WHERE is_active = 1')
            result = self.cursor.fetchone()
            stats['products_count'] = result['count'] if result else 0
            
            # Количество заказов
            self.cursor.execute('SELECT COUNT(*) as count FROM orders')
            result = self.cursor.fetchone()
            stats['orders_count'] = result['count'] if result else 0
            
            # Выручка
            self.cursor.execute('SELECT SUM(total_price) as revenue FROM orders WHERE status = "completed"')
            result = self.cursor.fetchone()
            stats['revenue'] = float(result['revenue']) if result and result['revenue'] else 0.0
            
            return stats
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {
                'users_count': 0,
                'products_count': 0,
                'orders_count': 0,
                'revenue': 0.0
            }
    
    def __del__(self):
        """Деструктор - закрываем соединение"""
        self.close()