import aiosqlite
import os
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = None):
        if db_path is None:
            # В Railway используем переменную окружения или временную директорию
            db_path = os.getenv('DATABASE_PATH', '/tmp/bot_data.db')
        self.db_path = db_path
    
    async def init(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_sheets (
                    user_id TEXT PRIMARY KEY,
                    sheet_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
            logger.info("База данных инициализирована")
    
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

# Глобальный экземпляр базы данных
db = Database() 