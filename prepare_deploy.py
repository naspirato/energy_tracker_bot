#!/usr/bin/env python3
"""
Скрипт для подготовки к деплою
"""

import json
import os

def prepare_google_creds():
    """Подготавливает Google credentials для деплоя"""
    
    try:
        # Читаем creds.json
        with open('creds.json', 'r') as f:
            creds_data = json.load(f)
        
        # Конвертируем в одну строку
        creds_json_string = json.dumps(creds_data)
        
        print("🔧 Подготовка Google credentials для деплоя...")
        print("\n📋 Скопируйте эту строку в переменную окружения GOOGLE_CREDS_JSON:")
        print("=" * 80)
        print(creds_json_string)
        print("=" * 80)
        
        # Сохраняем в файл для удобства
        with open('google_creds_for_deploy.txt', 'w') as f:
            f.write(creds_json_string)
        
        print(f"\n✅ Credentials сохранены в файл: google_creds_for_deploy.txt")
        print(f"📁 Размер: {len(creds_json_string)} символов")
        
    except FileNotFoundError:
        print("❌ Файл creds.json не найден!")
        print("💡 Убедитесь, что файл creds.json находится в текущей папке")
    except json.JSONDecodeError:
        print("❌ Ошибка при чтении creds.json!")
        print("💡 Проверьте, что файл содержит валидный JSON")

def show_deployment_info():
    """Показывает информацию для деплоя"""
    
    print("\n🚀 ИНФОРМАЦИЯ ДЛЯ ДЕПЛОЯ")
    print("=" * 50)
    
    # Проверяем токен бота
    bot_token = os.getenv('BOT_TOKEN')
    if bot_token:
        print(f"🤖 BOT_TOKEN: {bot_token[:10]}... (установлен)")
    else:
        print("🤖 BOT_TOKEN: НЕ УСТАНОВЛЕН!")
        print("💡 Установите переменную окружения BOT_TOKEN")
    
    print("\n📋 Переменные окружения для деплоя:")
    print("BOT_TOKEN=<ваш_токен_бота>")
    print("GOOGLE_CREDS_JSON=<скопируйте из файла выше>")
    
    print("\n🎯 Рекомендуемые платформы:")
    print("1. Railway (railway.app) - самый простой")
    print("2. Render (render.com) - бесплатный")
    print("3. Heroku (heroku.com) - надежный")
    
    print("\n📖 Подробная инструкция в файле: DEPLOYMENT.md")

if __name__ == "__main__":
    prepare_google_creds()
    show_deployment_info() 