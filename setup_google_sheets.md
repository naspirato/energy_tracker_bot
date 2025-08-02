# Настройка Google Sheets API

## Пошаговая инструкция

### 1. Создание проекта в Google Cloud Console

1. Перейдите на [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Включите Google Sheets API:
   - Перейдите в "APIs & Services" > "Library"
   - Найдите "Google Sheets API"
   - Нажмите "Enable"

### 2. Создание Service Account

1. Перейдите в "APIs & Services" > "Credentials"
2. Нажмите "Create Credentials" > "Service Account"
3. Заполните форму:
   - Service account name: `telegram-bot`
   - Service account ID: автоматически заполнится
   - Description: `Service account for Telegram psychology bot`
4. Нажмите "Create and Continue"
5. Пропустите шаги с ролями (нажмите "Done")

### 3. Создание ключа

1. В списке Service Accounts найдите созданный аккаунт
2. Нажмите на email аккаунта
3. Перейдите на вкладку "Keys"
4. Нажмите "Add Key" > "Create new key"
5. Выберите "JSON" формат
6. Нажмите "Create"

### 4. Настройка файла

1. Скачанный JSON файл переименуйте в `creds.json`
2. Поместите файл в корневую папку проекта (рядом с `bot.py`)
3. **ВАЖНО**: Не публикуйте этот файл в репозиторий!

### 5. Настройка Google Таблицы

1. Создайте новую Google Таблицу
2. Скопируйте ссылку на таблицу
3. Отправьте боту команду: `/setsheet <ссылка на таблицу>`

### Структура таблицы

Бот автоматически создаст заголовки в первой строке:
- Дата и время
- Усталость
- Настроение  
- Сон

## Безопасность

- Никогда не публикуйте `creds.json` в публичных репозиториях
- Добавьте `creds.json` в `.gitignore`
- Регулярно обновляйте ключи доступа 