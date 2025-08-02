#!/usr/bin/env python3
"""
Скрипт для безопасного запуска бота локально
"""

import os
import sys
from dotenv import load_dotenv

def check_environment():
    """Проверяет наличие необходимых переменных окружения"""
    
    # Загружаем .env файл если он есть
    load_dotenv()
    
    print("🔍 Проверка переменных окружения...")
    
    # Проверяем токен бота
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        print("❌ BOT_TOKEN не найден!")
        print("💡 Создайте файл .env с содержимым:")
        print("BOT_TOKEN=ваш_токен_бота")
        return False
    
    print(f"✅ BOT_TOKEN: {bot_token[:10]}...")
    
    # Проверяем Google credentials
    google_creds = os.getenv('GOOGLE_CREDS_JSON')
    if google_creds:
        print("✅ GOOGLE_CREDS_JSON: установлен")
    else:
        print("⚠️  GOOGLE_CREDS_JSON: не установлен (Google Sheets будет недоступен)")
    
    return True

def run_bot():
    """Запускает бота"""
    
    if not check_environment():
        print("\n❌ Не удалось запустить бота из-за отсутствующих переменных окружения")
        sys.exit(1)
    
    print("\n🚀 Запуск бота...")
    
    try:
        # Импортируем и запускаем бота
        from bot import main
        import asyncio
        
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка при запуске бота: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_bot() 