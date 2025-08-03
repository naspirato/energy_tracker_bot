import aiosqlite
import os
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = None):
        if db_path is None:
            # В Railway используем переменную окружения или постоянную директорию
            db_path = os.getenv('DATABASE_PATH', '/app/data/bot_data.db')
        self.db_path = db_path
    
    async def init(self):
        """Инициализация базы данных"""
        # Создаем директорию для базы данных, если она не существует
        db_dir = os.path.dirname(self.db_path)
        if not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"Создана директория для базы данных: {db_dir}")
            except Exception as e:
                logger.error(f"Ошибка при создании директории {db_dir}: {e}")
        
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица для привязок пользователей к таблицам
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_sheets (
                    user_id TEXT PRIMARY KEY,
                    sheet_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица для пользовательских измерений
            await db.execute("""
                CREATE TABLE IF NOT EXISTS custom_measurements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    measurement_type TEXT NOT NULL CHECK(measurement_type IN ('numeric', 'text')),
                    min_value INTEGER DEFAULT 0,
                    max_value INTEGER DEFAULT 10,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user_sheets (user_id) ON DELETE CASCADE
                )
            """)
            
            await db.commit()
            logger.info(f"База данных инициализирована: {self.db_path}")
    
    async def set_user_sheet(self, user_id: str, sheet_id: str) -> bool:
        """Установить таблицу для пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO user_sheets (user_id, sheet_id, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (user_id, sheet_id))
                await db.commit()
                logger.info(f"Таблица {sheet_id} установлена для пользователя {user_id}")
                return True
        except Exception as e:
            logger.error(f"Ошибка при установке таблицы для пользователя {user_id}: {e}")
            return False
    
    async def get_user_sheet(self, user_id: str) -> Optional[str]:
        """Получить ID таблицы пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT sheet_id FROM user_sheets WHERE user_id = ?", 
                    (user_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row else None
        except Exception as e:
            logger.error(f"Ошибка при получении таблицы пользователя {user_id}: {e}")
            return None
    
    async def get_all_user_sheets(self) -> Dict[str, str]:
        """Получить все привязки пользователей к таблицам"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT user_id, sheet_id FROM user_sheets") as cursor:
                    rows = await cursor.fetchall()
                    return {row[0]: row[1] for row in rows}
        except Exception as e:
            logger.error(f"Ошибка при получении всех привязок: {e}")
            return {}
    
    async def remove_user_sheet(self, user_id: str) -> bool:
        """Удалить привязку таблицы пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM user_sheets WHERE user_id = ?", (user_id,))
                await db.commit()
                logger.info(f"Привязка таблицы удалена для пользователя {user_id}")
                return True
        except Exception as e:
            logger.error(f"Ошибка при удалении привязки таблицы для пользователя {user_id}: {e}")
            return False
    
    # Методы для работы с пользовательскими измерениями
    async def add_custom_measurement(self, user_id: str, name: str, measurement_type: str, min_value: int = 0, max_value: int = 10) -> bool:
        """Добавить пользовательское измерение"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO custom_measurements (user_id, name, measurement_type, min_value, max_value)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, name, measurement_type, min_value, max_value))
                await db.commit()
                logger.info(f"Добавлено измерение '{name}' для пользователя {user_id}")
                return True
        except Exception as e:
            logger.error(f"Ошибка при добавлении измерения для пользователя {user_id}: {e}")
            return False
    
    async def get_custom_measurements(self, user_id: str) -> list:
        """Получить все пользовательские измерения пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT id, name, measurement_type, min_value, max_value 
                    FROM custom_measurements 
                    WHERE user_id = ? 
                    ORDER BY created_at
                """, (user_id,)) as cursor:
                    rows = await cursor.fetchall()
                    return [
                        {
                            'id': row[0],
                            'name': row[1],
                            'type': row[2],
                            'min_value': row[3],
                            'max_value': row[4]
                        }
                        for row in rows
                    ]
        except Exception as e:
            logger.error(f"Ошибка при получении измерений для пользователя {user_id}: {e}")
            return []
    
    async def remove_custom_measurement(self, user_id: str, measurement_id: int) -> bool:
        """Удалить пользовательское измерение"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    DELETE FROM custom_measurements 
                    WHERE id = ? AND user_id = ?
                """, (measurement_id, user_id))
                await db.commit()
                logger.info(f"Удалено измерение {measurement_id} для пользователя {user_id}")
                return True
        except Exception as e:
            logger.error(f"Ошибка при удалении измерения для пользователя {user_id}: {e}")
            return False

# Глобальный экземпляр базы данных
db = Database() 