# Telegram Psychology Bot

Этот Telegram бот помогает отслеживать психологическое состояние, записывая данные в Google Таблицы.

## Установка

1. Клонируйте репозиторий
2. Создайте виртуальное окружение:
   ```bash
   python -m venv venv
   source venv/bin/activate  # На macOS/Linux
   # или
   venv\Scripts\activate  # На Windows
   ```
3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

## Настройка

### 1. Telegram Bot Token
Получите токен бота у [@BotFather](https://t.me/BotFather) и создайте файл `.env`:

```bash
BOT_TOKEN=ваш_токен_бота_от_botfather
```

### 2. Google Sheets API (опционально)
Для работы с Google Таблицами:

1. Создайте проект в [Google Cloud Console](https://console.cloud.google.com/)
2. Включите Google Sheets API
3. Создайте Service Account и скачайте JSON файл с ключами
4. Переименуйте файл в `creds.json` и поместите в корневую папку проекта

## Использование

### Быстрый запуск (рекомендуется)
```bash
chmod +x manage.sh       # Сделать скрипт исполняемым (один раз)
./manage.sh start        # Запустить бота
./manage.sh stop         # Остановить бота
./manage.sh restart      # Перезапустить бота
./manage.sh status       # Проверить статус
./manage.sh logs         # Показать логи в реальном времени
```

### Ручной запуск
```bash
source venv/bin/activate
python run_local.py  # Рекомендуется (проверяет переменные окружения)
# или
python bot.py        # Альтернативно
```

### Команды бота
В Telegram отправьте боту:
- `/start` - приветствие и главное меню с кнопками
- `/help` - показать все доступные команды
- `/setsheet <ссылка на Google таблицу>` - подключить таблицу
- `/track` - начать запись данных о состоянии
- `/status` - проверить подключенную таблицу

### 🎛️ Кнопки интерфейса
Бот поддерживает удобные кнопки:
- **📊 Записать данные** - начать запись состояния
- **📈 Статус** - проверить подключенную таблицу
- **❓ Помощь** - показать справку
- **🔗 Изменить таблицу** - подключить новую таблицу

## Команды

- `/start` - Начать работу с ботом
- `/setsheet <ссылка>` - Подключить Google таблицу
- `/track` - Записать данные о состоянии (усталость, настроение, сон)

## Структура данных

Бот записывает в таблицу следующие данные:
- Дата и время
- Усталость (0-10)
- Настроение (0-10)  
- Качество сна (текст)

## Примечания

- Если файл `creds.json` отсутствует, бот будет работать без Google Sheets функциональности
- Данные пользователей сохраняются в файле `usersheets.json`
- Бот использует aiogram v3 для работы с Telegram API

## Устранение проблем

### Ошибка TelegramConflictError
Если получаете ошибку "can't use getUpdates method while webhook is active":
1. Бот автоматически удаляет webhook при запуске
2. Если проблема повторяется, запустите: `python delete_webhook.py`
3. Или используйте BotFather для удаления webhook: `/setwebhook` → пустая ссылка

### Ошибка "terminated by other getUpdates request"
Если получаете ошибку "terminated by other getUpdates request":
1. Используйте `./manage_bot.sh status` для проверки запущенных процессов
2. Используйте `./manage_bot.sh stop` для остановки всех процессов
3. Или найдите и остановите процессы вручную: `ps aux | grep "python.*bot"` 