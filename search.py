import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SearchManager:
    def __init__(self, db):
        self.db = db
        self.search_cache = {}
        self.cache_ttl = 300  # 5 минут
    
    def search_products(self, user_id: int, query: str, filters: Optional[Dict] = None, 
                       page: int = 0, per_page: int = 10) -> Tuple[List[Dict], int, Dict]:
        """
        Поиск товаров с фильтрами и пагинацией
        
        Args:
            user_id: ID пользователя
            query: Поисковый запрос
            filters: Фильтры поиска
            page: Номер страницы
            per_page: Количество на странице
            
        Returns:
            Кортеж: (результаты, общее количество, метаданные)
        """
        try:
            # Нормализация запроса
            query = query.strip().lower()
            
            # Проверка кэша
            cache_key = f"{user_id}:{query}:{page}:{str(filters)}"
            if cache_key in self.search_cache:
                cached_time, cached_data = self.search_cache[cache_key]
                if datetime.now() - cached_time < timedelta(seconds=self.cache_ttl):
                    logger.info(f"Используем кэшированные результаты для {query}")
                    return cached_data
            
            # Базовые параметры
            offset = page * per_page
            filters = filters or {}
            
            # Поиск в базе данных
            results = self.db.search_products(
                query=query,
                category=filters.get('category'),
                min_price=filters.get('min_price'),
                max_price=filters.get('max_price'),
                limit=per_page,
                offset=offset
            )
            
            # Преобразуем в словари
            products = []
            for row in results:
                product = dict(row)
                # Добавляем дополнительные поля для отображения
                product['formatted_price'] = f"{product['price']}₽"
                product['short_description'] = product['description'][:100] + "..." if len(product['description']) > 100 else product['description']
                products.append(product)
            
            # Получаем общее количество (для пагинации)
            total_count = len(self.db.search_products(
                query=query,
                category=filters.get('category'),
                min_price=filters.get('min_price'),
                max_price=filters.get('max_price'),
                limit=1000  # Максимум 1000 товаров в поиске
            ))
            
            # Метаданные поиска
            metadata = {
                'query': query,
                'page': page,
                'total_pages': (total_count + per_page - 1) // per_page,
                'total_results': total_count,
                'has_next': (page + 1) * per_page < total_count,
                'has_prev': page > 0,
                'filters_applied': bool(filters)
            }
            
            # Сохраняем запрос в историю
            if query and total_count > 0:
                self.db.save_search_query(user_id, query, total_count)
            
            # Кэшируем результаты
            self.search_cache[cache_key] = (datetime.now(), (products, total_count, metadata))
            
            return products, total_count, metadata
            
        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
            return [], 0, {}
    
    def search_by_category(self, category: str, sort_by: str = 'name', 
                          page: int = 0, per_page: int = 10) -> Tuple[List[Dict], Dict]:
        """
        Поиск товаров по категории
        
        Args:
            category: Категория товаров
            sort_by: Поле для сортировки
            page: Номер страницы
            per_page: Количество на странице
            
        Returns:
            Кортеж: (результаты, метаданные)
        """
        try:
            # Получаем товары категории
            products_data = self.db.get_all_products(category=category)
            
            # Сортируем
            if sort_by == 'price_asc':
                products_data.sort(key=lambda x: x['price'])
            elif sort_by == 'price_desc':
                products_data.sort(key=lambda x: x['price'], reverse=True)
            elif sort_by == 'newest':
                products_data.sort(key=lambda x: x['created_at'], reverse=True)
            elif sort_by == 'popular':
                # Здесь можно добавить логику популярности
                pass
            
            # Пагинация
            offset = page * per_page
            products = products_data[offset:offset + per_page]
            
            metadata = {
                'category': category,
                'page': page,
                'total_pages': (len(products_data) + per_page - 1) // per_page,
                'total_results': len(products_data),
                'has_next': (page + 1) * per_page < len(products_data),
                'has_prev': page > 0,
                'sort_by': sort_by
            }
            
            return products, metadata
            
        except Exception as e:
            logger.error(f"Ошибка поиска по категории: {e}")
            return [], {}
    
    def search_cheap_products(self, max_price: float = 500, limit: int = 20) -> List[Dict]:
        """
        Поиск дешевых товаров
        
        Args:
            max_price: Максимальная цена
            limit: Лимит результатов
            
        Returns:
            Список товаров
        """
        try:
            results = self.db.search_products(
                query='',
                min_price=0,
                max_price=max_price,
                limit=limit
            )
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Ошибка поиска дешевых товаров: {e}")
            return []
    
    def search_new_products(self, days: int = 7, limit: int = 20) -> List[Dict]:
        """
        Поиск новых товаров
        
        Args:
            days: За последние N дней
            limit: Лимит результатов
            
        Returns:
            Список товаров
        """
        try:
            # Здесь нужно расширить базу данных или использовать кэш
            # Для простоты вернем все товары
            products = self.db.get_all_products(limit=limit)
            return [dict(row) for row in products]
            
        except Exception as e:
            logger.error(f"Ошибка поиска новых товаров: {e}")
            return []
    
    def get_search_suggestions(self, query: str, limit: int = 5) -> List[str]:
        """
        Получение подсказок для поиска
        
        Args:
            query: Часть запроса
            limit: Лимит подсказок
            
        Returns:
            Список подсказок
        """
        try:
            query = query.strip().lower()
            if len(query) < 2:
                return []
            
            # Получаем популярные поисковые запросы
            # Здесь можно реализовать более сложную логику
            
            suggestions = []
            
            # Поиск по началу названий товаров
            products = self.db.search_products(query=query, limit=10)
            for product in products:
                name = product['name'].lower()
                if name.startswith(query) and name not in suggestions:
                    suggestions.append(name)
                    if len(suggestions) >= limit:
                        break
            
            # Добавляем популярные запросы
            popular_queries = ['игры', 'ключи', 'программы', 'курсы', 'книги']
            for popular in popular_queries:
                if query in popular and popular not in suggestions:
                    suggestions.append(popular)
                    if len(suggestions) >= limit:
                        break
            
            return suggestions[:limit]
            
        except Exception as e:
            logger.error(f"Ошибка получения подсказок: {e}")
            return []
    
    def get_popular_searches(self, limit: int = 10) -> List[Dict]:
        """
        Получение популярных поисковых запросов
        
        Args:
            limit: Лимит запросов
            
        Returns:
            Список популярных запросов
        """
        try:
            # Здесь можно реализовать логику сбора статистики
            # Для простоты вернем фиктивные данные
            return [
                {'query': 'игры', 'count': 150},
                {'query': 'steam', 'count': 120},
                {'query': 'курсы', 'count': 95},
                {'query': 'программы', 'count': 80},
                {'query': 'windows', 'count': 70},
                {'query': 'книги', 'count': 65},
                {'query': 'антивирус', 'count': 50},
                {'query': 'онлайн', 'count': 45},
                {'query': 'обучение', 'count': 40},
                {'query': 'софт', 'count': 35}
            ][:limit]
            
        except Exception as e:
            logger.error(f"Ошибка получения популярных поисков: {e}")
            return []
    
    def clear_search_cache(self):
        """Очистка кэша поиска"""
        self.search_cache.clear()
        logger.info("Кэш поиска очищен")
    
    def get_search_filters(self) -> Dict:
        """
        Получение доступных фильтров поиска
        
        Returns:
            Словарь с фильтрами
        """
        return {
            'price_ranges': [
                {'id': '0_100', 'name': 'До 100₽', 'min': 0, 'max': 100},
                {'id': '100_500', 'name': '100-500₽', 'min': 100, 'max': 500},
                {'id': '500_1000', 'name': '500-1000₽', 'min': 500, 'max': 1000},
                {'id': '1000_5000', 'name': '1000-5000₽', 'min': 1000, 'max': 5000},
                {'id': '5000_up', 'name': 'От 5000₽', 'min': 5000, 'max': None}
            ],
            'categories': self.db.get_categories(),
            'sort_options': [
                {'id': 'relevance', 'name': 'По релевантности'},
                {'id': 'price_asc', 'name': 'Сначала дешевые'},
                {'id': 'price_desc', 'name': 'Сначала дорогие'},
                {'id': 'newest', 'name': 'Сначала новые'},
                {'id': 'popular', 'name': 'По популярности'}
            ],
            'stock_options': [
                {'id': 'any', 'name': 'Любое наличие'},
                {'id': 'in_stock', 'name': 'В наличии'},
                {'id': 'out_of_stock', 'name': 'Нет в наличии'}
            ]
        }
    
    def parse_price_filter(self, filter_id: str) -> Tuple[Optional[float], Optional[float]]:
        """
        Парсинг фильтра по цене
        
        Args:
            filter_id: ID фильтра
            
        Returns:
            Кортеж (min_price, max_price)
        """
        price_filters = {
            '0_100': (0, 100),
            '100_500': (100, 500),
            '500_1000': (500, 1000),
            '1000_5000': (1000, 5000),
            '5000_up': (5000, None),
            'price_any': (None, None)
        }
        
        return price_filters.get(filter_id, (None, None))