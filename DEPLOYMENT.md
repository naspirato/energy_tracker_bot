# 🚀 Деплой Telegram бота

## Подготовка к деплою

### 1. Подготовьте Google Credentials
1. Откройте файл `creds.json`
2. Скопируйте весь JSON в одну строку
3. Сохраните для использования в переменных окружения

### 2. Получите токен бота
- Убедитесь, что у вас есть токен бота от @BotFather

## 🎯 Railway (Рекомендуется)

### Шаги деплоя:
1. **Создайте аккаунт** на [railway.app](https://railway.app)
2. **Подключите GitHub репозиторий**
3. **Создайте новый проект** → "Deploy from GitHub repo"
4. **Выберите репозиторий** с ботом
5. **Настройте переменные окружения:**
   ```
   BOT_TOKEN=ваш_токен_бота
   GOOGLE_CREDS_JSON={"type":"service_account",...}
   ```
6. **Деплой автоматически запустится**

### Преимущества Railway:
- ✅ Автоматический деплой из GitHub
- ✅ Простая настройка переменных окружения
- ✅ Бесплатный тариф $5/месяц
- ✅ Автоматические обновления

## 🌐 Render

### Шаги деплоя:
1. **Создайте аккаунт** на [render.com](https://render.com)
2. **Создайте новый Web Service**
3. **Подключите GitHub репозиторий**
4. **Настройте:**
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
5. **Добавьте переменные окружения**
6. **Нажмите "Create Web Service"**

## ☁️ Heroku

### Шаги деплоя:
1. **Установите Heroku CLI**
2. **Создайте приложение:**
   ```bash
   heroku create your-bot-name
   ```
3. **Добавьте переменные окружения:**
   ```bash
   heroku config:set BOT_TOKEN=ваш_токен_бота
   heroku config:set GOOGLE_CREDS_JSON='{"type":"service_account",...}'
   ```
4. **Деплой:**
   ```bash
   git push heroku main
   ```

## 🔧 Переменные окружения

### Обязательные:
- `BOT_TOKEN` - токен вашего Telegram бота

### Опциональные:
- `GOOGLE_CREDS_JSON` - JSON с Google Service Account credentials

## 📝 Пример настройки переменных

### BOT_TOKEN:
```
ваш_токен_бота_от_botfather
```

### GOOGLE_CREDS_JSON:
```json
{"type":"service_account","project_id":"psycho-bot-466516","private_key_id":"...","private_key":"-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n","client_email":"psycho-bot-sa@psycho-bot-466516.iam.gserviceaccount.com","client_id":"...","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"https://www.googleapis.com/robot/v1/metadata/x509/psycho-bot-sa%40psycho-bot-466516.iam.gserviceaccount.com"}
```

## 🚨 Важные моменты

1. **Никогда не коммитьте** `creds.json` в репозиторий
2. **Используйте переменные окружения** для чувствительных данных
3. **Проверьте логи** после деплоя
4. **Убедитесь, что Google APIs включены** в проекте

## 🔍 Проверка деплоя

После деплоя:
1. Отправьте боту `/start`
2. Проверьте логи в панели управления
3. Попробуйте подключить Google таблицу
4. Запишите тестовые данные

## 💰 Стоимость

- **Railway:** $5/месяц (бесплатный тариф)
- **Render:** Бесплатно (750 часов/месяц)
- **Heroku:** $7/месяц (базовый план)
- **DigitalOcean:** $5/месяц 