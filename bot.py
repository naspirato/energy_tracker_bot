from aiogram import Bot, Dispatcher, types, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import datetime
import asyncio
import logging
import os
from database import db

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Telegram токен
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не установлен в переменных окружения!")
    logger.error("💡 Установите переменную окружения BOT_TOKEN")
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

logger.info(f"Инициализация бота с токеном: {BOT_TOKEN[:10]}...")

bot = Bot(token=BOT_TOKEN, session_name="psycho_bot_session")
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

logger.info("Бот инициализирован успешно")

# Функция для создания Google таблицы
async def create_user_sheet(user_id: str, username: str) -> str:
    """Создает новую Google таблицу для пользователя"""
    try:
        # Создаем название таблицы с именем пользователя и датой
        from datetime import datetime
        current_date = datetime.now().strftime("%Y-%m-%d")
        sheet_name = f"Energy Tracker - {username} ({current_date})"
        
        # Создаем новую таблицу
        sheet = client.create(sheet_name)
        sheet_id = sheet.id
        
        # Настраиваем заголовки
        worksheet = sheet.sheet1
        headers = [
            "Дата и время",
            "Усталость (0-10)",
            "Настроение (0-10)", 
            "Сон",
            "Физическая нагрузка (0-10)",
            "Умственная нагрузка (0-10)",
            "Симптомы",
            "Заметки"
        ]
        worksheet.append_row(headers)
        
        # Форматируем заголовки (жирный шрифт)
        worksheet.format('A1:H1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
        })
        
        # Настраиваем ширину колонок
        worksheet.set_column_width(1, 150)  # Дата и время
        worksheet.set_column_width(2, 120)  # Усталость
        worksheet.set_column_width(3, 120)  # Настроение
        worksheet.set_column_width(4, 100)  # Сон
        worksheet.set_column_width(5, 150)  # Физическая нагрузка
        worksheet.set_column_width(6, 150)  # Умственная нагрузка
        worksheet.set_column_width(7, 200)  # Симптомы
        worksheet.set_column_width(8, 250)  # Заметки
        
        logger.info(f"✅ Создана таблица {sheet_id} для пользователя {username}")
        return sheet_id
        
    except Exception as e:
        logger.error(f"❌ Ошибка при создании таблицы для пользователя {username}: {e}")
        raise

async def add_column_to_sheet(sheet_id: str, column_name: str) -> bool:
    """Добавляет новый столбец в таблицу"""
    try:
        sheet = client.open_by_key(sheet_id).sheet1
        all_values = sheet.get_all_values()
        
        if not all_values:
            return False
        
        # Получаем последний столбец (A=1, B=2, etc.)
        last_column = len(all_values[0])
        new_column_letter = chr(ord('A') + last_column)
        
        # Добавляем заголовок в первую строку
        sheet.update(f'{new_column_letter}1', column_name)
        
        # Форматируем заголовок
        sheet.format(f'{new_column_letter}1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
        })
        
        logger.info(f"✅ Добавлен столбец '{column_name}' в таблицу {sheet_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка при добавлении столбца в таблицу {sheet_id}: {e}")
        return False

# Функции для создания кнопок
def get_main_keyboard() -> InlineKeyboardMarkup:
    """Создает основную клавиатуру с кнопками"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Записать данные", callback_data="track_data"),
            InlineKeyboardButton(text="📈 Статус", callback_data="check_status")
        ],
        [
            InlineKeyboardButton(text="➕ Создать таблицу", callback_data="create_sheet"),
            InlineKeyboardButton(text="🔗 Подключить таблицу", callback_data="connect_sheet")
        ],
        [
            InlineKeyboardButton(text="📋 Измерения", callback_data="manage_measurements"),
            InlineKeyboardButton(text="❓ Помощь", callback_data="show_help")
        ]
    ])
    return keyboard

def get_track_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для отслеживания"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Записать данные", callback_data="track_data")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
        ]
    ])
    return keyboard

# Словарь user_id -> Google Sheet ID (загружается из БД при старте)
user_sheets = {}

# FSM
class Form(StatesGroup):
    fatigue = State()
    mood = State()
    sleep = State()
    physical_load = State()
    mental_load = State()
    symptoms = State()
    notes = State()
    custom_measurement = State()  # Для пользовательских измерений

# FSM для создания измерений
class MeasurementForm(StatesGroup):
    measurement_name = State()
    measurement_type = State()
    min_value = State()
    max_value = State()

# Google API - optional
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Проверяем переменную окружения для Google credentials
    google_creds_json = os.getenv('GOOGLE_CREDS_JSON')
    if google_creds_json:
        # Используем credentials из переменной окружения
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            json.loads(google_creds_json), scope
        )
        client = gspread.authorize(creds)
        google_sheets_available = True
        logger.info("Google Sheets API подключен через переменную окружения")
    else:
        # Пробуем файл creds.json (для локальной разработки)
        creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
        client = gspread.authorize(creds)
        google_sheets_available = True
        logger.info("Google Sheets API подключен через файл creds.json")
        
except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
    logger.warning(f"Google Sheets не настроен: {e}")
    google_sheets_available = False
    client = None

# Команды
@router.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    logger.info(f"Команда /start от пользователя {username} (ID: {user_id})")
    
    response = f"""Привет, {username}! 👋 Я бот для отслеживания психологического состояния.

📋 Что я умею:
• Записывать данные о вашем состоянии в Google таблицы
• Отслеживать усталость, настроение и качество сна
• Создавать новые таблицы автоматически

🚀 Выберите действие:
➕ Создать новую таблицу (рекомендуется)
🔗 Подключить существующую таблицу"""
    
    await message.reply(response, reply_markup=get_main_keyboard())
    logger.info(f"Отправлен ответ пользователю {username}")

@router.message(Command("help"))
async def help_command(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    logger.info(f"Команда /help от пользователя {username} (ID: {user_id})")
    
    help_text = """📚 Доступные команды:

➕ /createsheet - Создать новую Google таблицу (рекомендуется)
🔗 /setsheet <ссылка> - Подключить существующую таблицу
   Пример: /setsheet https://docs.google.com/spreadsheets/d/...

📊 /track - Начать запись данных о состоянии
   Бот спросит: усталость (0-10), настроение (0-10), качество сна

📈 /status - Проверить подключенную таблицу

➕ /addmeasurement - Добавить новое измерение
📋 /measurements - Показать все измерения

❓ /help - Показать это сообщение

💡 Рекомендуем создать новую таблицу через /createsheet!"""
    
    await message.reply(help_text)
    logger.info(f"Отправлена справка пользователю {username}")

@router.message(Command("addmeasurement"))
async def add_measurement(message: Message, state: FSMContext):
    """Начинает процесс добавления нового измерения"""
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    logger.info(f"Команда /addmeasurement от пользователя {username} (ID: {user_id})")
    
    user_id_str = str(user_id)
    if user_id_str not in user_sheets:
        await message.reply("❌ Сначала подключите таблицу через /createsheet или /setsheet")
        return
    
    await message.reply("📝 Введите название нового измерения:")
    await state.set_state(MeasurementForm.measurement_name)
    logger.info(f"Начато создание измерения для пользователя {username}")

@router.message(Command("measurements"))
async def show_measurements(message: Message):
    """Показывает все пользовательские измерения"""
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    logger.info(f"Команда /measurements от пользователя {username} (ID: {user_id})")
    
    user_id_str = str(user_id)
    measurements = await db.get_custom_measurements(user_id_str)
    
    if not measurements:
        await message.reply("📋 У вас пока нет пользовательских измерений.\n\nИспользуйте /addmeasurement для добавления нового измерения.")
        return
    
    measurements_text = "📋 Ваши измерения:\n\n"
    for i, measurement in enumerate(measurements, 1):
        if measurement['type'] == 'numeric':
            measurements_text += f"{i}. {measurement['name']} (0-{measurement['max_value']})\n"
        else:
            measurements_text += f"{i}. {measurement['name']} (текст)\n"
    
    measurements_text += "\n💡 Используйте /addmeasurement для добавления нового измерения"
    
    await message.reply(measurements_text)
    logger.info(f"Показаны измерения пользователю {username}")

@router.message(Command("createsheet"))
async def create_sheet(message: Message):
    """Создает новую Google таблицу для пользователя"""
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    logger.info(f"Команда /createsheet от пользователя {username} (ID: {user_id})")
    
    if not google_sheets_available:
        logger.warning(f"Google Sheets недоступен для пользователя {username}")
        await message.reply("Google Sheets не настроен. Добавьте файл creds.json для работы с таблицами.")
        return
    
    try:
        # Создаем новую таблицу
        await message.reply("🔄 Создаю новую таблицу для вас...")
        sheet_id = await create_user_sheet(str(user_id), username)
        
        # Сохраняем в базу данных
        try:
            success = await db.set_user_sheet(str(user_id), sheet_id)
            if success:
                # Обновляем локальный словарь
                user_sheets[str(user_id)] = sheet_id
                
                sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
                logger.info(f"Таблица {sheet_id} создана и подключена для пользователя {username}")
                await message.reply(
                    f"✅ Таблица создана и подключена!\n\n"
                    f"🔗 [Открыть таблицу]({sheet_url})\n\n"
                    f"📊 Теперь вы можете записывать данные о вашем состоянии.",
                    reply_markup=get_track_keyboard(),
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )
            else:
                logger.error(f"Не удалось сохранить таблицу в БД для пользователя {username}")
                await message.reply("❌ Ошибка при сохранении таблицы. Попробуйте еще раз.")
        except Exception as e:
            logger.error(f"Ошибка при сохранении в БД: {e}")
            # Сохраняем только в локальный словарь как fallback
            user_sheets[str(user_id)] = sheet_id
            sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
            logger.warning(f"Сохранено только в локальный словарь для пользователя {username}")
            await message.reply(
                f"✅ Таблица создана! (временное сохранение)\n\n"
                f"🔗 [Открыть таблицу]({sheet_url})\n\n"
                f"📊 Теперь вы можете записывать данные о вашем состоянии.",
                reply_markup=get_track_keyboard(),
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
    except Exception as e:
        logger.error(f"Ошибка при создании таблицы для пользователя {username}: {str(e)}")
        await message.reply(f"❌ Ошибка при создании таблицы: {str(e)}")

@router.message(Command("setsheet"))
async def set_sheet(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    logger.info(f"Команда /setsheet от пользователя {username} (ID: {user_id})")
    
    if not google_sheets_available:
        logger.warning(f"Google Sheets недоступен для пользователя {username}")
        await message.reply("Google Sheets не настроен. Добавьте файл creds.json для работы с таблицами.")
        return
    
    try:
        url = message.text.split(' ')[1]
        sheet_id = url.split('/d/')[1].split('/')[0]
        logger.info(f"Извлечен ID таблицы: {sheet_id}")
        
        # Сохраняем в базу данных
        try:
            success = await db.set_user_sheet(str(user_id), sheet_id)
            if success:
                # Обновляем локальный словарь
                user_sheets[str(user_id)] = sheet_id
                
                logger.info(f"Таблица {sheet_id} подключена для пользователя {username}")
                await message.reply(
                    "✅ Таблица подключена!\n\n📊 Теперь вы можете записывать данные о вашем состоянии.",
                    reply_markup=get_track_keyboard()
                )
            else:
                logger.error(f"Не удалось сохранить таблицу в БД для пользователя {username}")
                await message.reply("❌ Ошибка при сохранении таблицы. Попробуйте еще раз.")
        except Exception as e:
            logger.error(f"Ошибка при сохранении в БД: {e}")
            # Сохраняем только в локальный словарь как fallback
            user_sheets[str(user_id)] = sheet_id
            logger.warning(f"Сохранено только в локальный словарь для пользователя {username}")
            await message.reply(
                "✅ Таблица подключена! (временное сохранение)\n\n📊 Теперь вы можете записывать данные о вашем состоянии.",
                reply_markup=get_track_keyboard()
            )
    except IndexError:
        logger.warning(f"Пользователь {username} не указал ссылку на таблицу")
        await message.reply("Пожалуйста, укажите ссылку на таблицу: /setsheet <ссылка>")
    except Exception as e:
        logger.error(f"Ошибка при подключении таблицы для пользователя {username}: {str(e)}")
        await message.reply(f"Ошибка при подключении таблицы: {str(e)}")

@router.message(Command("track"))
async def track(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    logger.info(f"Команда /track от пользователя {username} (ID: {user_id})")
    
    if not google_sheets_available:
        logger.warning(f"Google Sheets недоступен для пользователя {username}")
        await message.reply("Google Sheets не настроен. Добавьте файл creds.json для работы с таблицами.")
        return
    
    user_id_str = str(user_id)
    if user_id_str not in user_sheets:
        logger.warning(f"Пользователь {username} не подключил таблицу")
        await message.reply("Сначала отправь ссылку на таблицу через /setsheet")
        return
    
    logger.info(f"Начинаем отслеживание для пользователя {username}")
    await message.reply("Усталость (0–10)?")
    await state.set_state(Form.fatigue)

@router.message(Command("status"))
async def status_command(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    logger.info(f"Команда /status от пользователя {username} (ID: {user_id})")
    
    user_id_str = str(user_id)
    if user_id_str not in user_sheets:
        status_text = "❌ Таблица не подключена\n\n🔗 Используйте /setsheet <ссылка> для подключения таблицы"
        await message.reply(status_text)
        logger.info(f"Отправлен статус пользователю {username}")
        return
    
    try:
        sheet_id = user_sheets[user_id_str]
        sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
        
        # Получаем данные из таблицы
        if google_sheets_available and client:
            sheet = client.open_by_key(sheet_id).sheet1
            all_values = sheet.get_all_values()
            
            if len(all_values) <= 1:  # Только заголовки или пустая таблица
                status_text = f"✅ Таблица подключена\n🔗 [Открыть таблицу]({sheet_url})\n\n📊 Записей: 0\n📝 Используйте /track для первой записи"
            else:
                # Подсчитываем количество записей (исключая заголовок)
                total_records = len(all_values) - 1
                
                # Получаем последнюю запись
                last_record = all_values[-1]
                last_date = last_record[0] if last_record else "Неизвестно"
                
                status_text = f"✅ Таблица подключена\n🔗 [Открыть таблицу]({sheet_url})\n\n📊 Всего записей: {total_records}\n📅 Последняя запись: {last_date}\n\n📝 Используйте /track для новой записи"
        else:
            status_text = f"✅ Таблица подключена\n🔗 [Открыть таблицу]({sheet_url})\n\n⚠️ Google Sheets API недоступен\n📝 Используйте /track для записи данных"
            
    except Exception as e:
        logger.error(f"Ошибка при получении статуса для пользователя {username}: {str(e)}")
        status_text = f"✅ Таблица подключена\n🔗 [Открыть таблицу]({sheet_url})\n\n❌ Ошибка при чтении данных: {str(e)}\n📝 Используйте /track для записи данных"
    
    await message.reply(status_text, parse_mode="Markdown", disable_web_page_preview=True)
    logger.info(f"Отправлен статус пользователю {username}")

# Обработчики кнопок
@router.callback_query()
async def handle_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    username = callback.from_user.username or "Unknown"
    data = callback.data
    
    logger.info(f"Нажата кнопка {data} пользователем {username}")
    
    if data == "track_data":
        # Проверяем, подключена ли таблица
        user_id_str = str(user_id)
        if user_id_str not in user_sheets:
            await callback.answer("❌ Сначала подключите таблицу!", show_alert=True)
            await callback.message.edit_text(
                "❌ Таблица не подключена\n\n🔗 Используйте /setsheet <ссылка> для подключения таблицы",
                reply_markup=get_main_keyboard()
            )
            return
        
        await callback.answer("📊 Начинаем запись данных...")
        await callback.message.edit_text("Усталость (0–10)?")
        await state.set_state(Form.fatigue)
        
    elif data == "check_status":
        user_id_str = str(user_id)
        if user_id_str not in user_sheets:
            status_text = "❌ Таблица не подключена\n\n🔗 Используйте /setsheet <ссылка> для подключения таблицы"
            await callback.message.edit_text(status_text, reply_markup=get_main_keyboard())
            return
        
        try:
            sheet_id = user_sheets[user_id_str]
            sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
            
            # Получаем данные из таблицы
            if google_sheets_available and client:
                sheet = client.open_by_key(sheet_id).sheet1
                all_values = sheet.get_all_values()
                
                if len(all_values) <= 1:  # Только заголовки или пустая таблица
                    status_text = f"✅ Таблица подключена\n🔗 [Открыть таблицу]({sheet_url})\n\n📊 Записей: 0\n📝 Используйте кнопку 'Записать данные' для первой записи"
                else:
                    # Подсчитываем количество записей (исключая заголовок)
                    total_records = len(all_values) - 1
                    
                    # Получаем последнюю запись
                    last_record = all_values[-1]
                    last_date = last_record[0] if last_record else "Неизвестно"
                    
                    status_text = f"✅ Таблица подключена\n🔗 [Открыть таблицу]({sheet_url})\n\n📊 Всего записей: {total_records}\n📅 Последняя запись: {last_date}\n\n📝 Используйте кнопку 'Записать данные' для новой записи"
            else:
                status_text = f"✅ Таблица подключена\n🔗 [Открыть таблицу]({sheet_url})\n\n⚠️ Google Sheets API недоступен\n📝 Используйте кнопку 'Записать данные'"
                
        except Exception as e:
            logger.error(f"Ошибка при получении статуса для пользователя {username}: {str(e)}")
            status_text = f"✅ Таблица подключена\n🔗 [Открыть таблицу]({sheet_url})\n\n❌ Ошибка при чтении данных: {str(e)}\n📝 Используйте кнопку 'Записать данные'"
        
        await callback.message.edit_text(status_text, reply_markup=get_main_keyboard(), parse_mode="Markdown", disable_web_page_preview=True)
        
    elif data == "create_sheet":
        if not google_sheets_available:
            await callback.answer("❌ Google Sheets недоступен!", show_alert=True)
            return
        
        await callback.answer("🔄 Создаю таблицу...")
        try:
            sheet_id = await create_user_sheet(str(user_id), username)
            
            # Сохраняем в базу данных
            success = await db.set_user_sheet(str(user_id), sheet_id)
            if success:
                user_sheets[str(user_id)] = sheet_id
                sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
                
                await callback.message.edit_text(
                    f"✅ Таблица создана и подключена!\n\n"
                    f"🔗 [Открыть таблицу]({sheet_url})\n\n"
                    f"📊 Теперь вы можете записывать данные о вашем состоянии.",
                    reply_markup=get_main_keyboard(),
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )
            else:
                await callback.message.edit_text(
                    "❌ Ошибка при сохранении таблицы. Попробуйте еще раз.",
                    reply_markup=get_main_keyboard()
                )
        except Exception as e:
            logger.error(f"Ошибка при создании таблицы: {e}")
            await callback.message.edit_text(
                f"❌ Ошибка при создании таблицы: {str(e)}",
                reply_markup=get_main_keyboard()
            )
    
    elif data == "connect_sheet":
        await callback.message.edit_text(
            "🔗 Отправьте ссылку на Google таблицу:\n\n"
            "Или используйте команду:\n"
            "/setsheet <ссылка_на_таблицу>",
            reply_markup=get_main_keyboard()
        )
    
    elif data == "manage_measurements":
        user_id_str = str(user_id)
        measurements = await db.get_custom_measurements(user_id_str)
        
        if not measurements:
            await callback.message.edit_text(
                "📋 У вас пока нет пользовательских измерений.\n\n"
                "💡 Используйте команду /addmeasurement для добавления нового измерения.",
                reply_markup=get_main_keyboard()
            )
        else:
            measurements_text = "📋 Ваши измерения:\n\n"
            for i, measurement in enumerate(measurements, 1):
                if measurement['type'] == 'numeric':
                    measurements_text += f"{i}. {measurement['name']} (0-{measurement['max_value']})\n"
                else:
                    measurements_text += f"{i}. {measurement['name']} (текст)\n"
            
            measurements_text += "\n💡 Используйте /addmeasurement для добавления нового измерения"
            
            await callback.message.edit_text(
                measurements_text,
                reply_markup=get_main_keyboard()
            )
        
    elif data == "show_help":
        help_text = """📚 Доступные команды:

➕ /createsheet - Создать новую Google таблицу (рекомендуется)
🔗 /setsheet <ссылка> - Подключить существующую таблицу
📊 /track - Начать запись данных о состоянии
📈 /status - Проверить подключенную таблицу
➕ /addmeasurement - Добавить новое измерение
📋 /measurements - Показать все измерения
❓ /help - Показать это сообщение

💡 Используйте кнопки для быстрого доступа!"""
        
        await callback.message.edit_text(help_text, reply_markup=get_main_keyboard())
        
    elif data == "main_menu":
        await callback.message.edit_text(
            "🏠 Главное меню\n\nВыберите действие:",
            reply_markup=get_main_keyboard()
        )

@router.message(Form.fatigue)
async def get_fatigue(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    fatigue = message.text
    logger.info(f"Получена усталость от {username}: {fatigue}")
    
    await state.update_data(fatigue=fatigue)
    await message.reply("Настроение (0–10)?")
    await state.set_state(Form.mood)
    logger.info(f"Переход к состоянию mood для пользователя {username}")

@router.message(Form.mood)
async def get_mood(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    mood = message.text
    logger.info(f"Получено настроение от {username}: {mood}")
    
    await state.update_data(mood=mood)
    await message.reply("Как спал?")
    await state.set_state(Form.sleep)
    logger.info(f"Переход к состоянию sleep для пользователя {username}")

@router.message(Form.sleep)
async def get_sleep(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    sleep = message.text
    logger.info(f"Получен сон от {username}: {sleep}")
    
    await state.update_data(sleep=sleep)
    await message.reply("Физическая нагрузка (0–10)?")
    await state.set_state(Form.physical_load)
    logger.info(f"Переход к состоянию physical_load для пользователя {username}")

@router.message(Form.physical_load)
async def get_physical_load(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    physical_load = message.text
    logger.info(f"Получена физическая нагрузка от {username}: {physical_load}")
    
    await state.update_data(physical_load=physical_load)
    await message.reply("Умственная нагрузка (0–10)?")
    await state.set_state(Form.mental_load)
    logger.info(f"Переход к состоянию mental_load для пользователя {username}")

@router.message(Form.mental_load)
async def get_mental_load(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    mental_load = message.text
    logger.info(f"Получена умственная нагрузка от {username}: {mental_load}")
    
    await state.update_data(mental_load=mental_load)
    await message.reply("Симптомы (если есть)?")
    await state.set_state(Form.symptoms)
    logger.info(f"Переход к состоянию symptoms для пользователя {username}")

@router.message(Form.symptoms)
async def get_symptoms(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    symptoms = message.text
    logger.info(f"Получены симптомы от {username}: {symptoms}")
    
    await state.update_data(symptoms=symptoms)
    await message.reply("Заметки/комментарии?")
    await state.set_state(Form.notes)
    logger.info(f"Переход к состоянию notes для пользователя {username}")

@router.message(Form.notes)
async def get_notes(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    notes = message.text
    logger.info(f"Получены заметки от {username}: {notes}")
    
    await state.update_data(notes=notes)
    user_id_str = str(user_id)
    
    # Проверяем, есть ли пользовательские измерения
    custom_measurements = await db.get_custom_measurements(user_id_str)
    
    if custom_measurements:
        # Есть пользовательские измерения, начинаем их сбор
        await state.update_data(custom_measurements=custom_measurements, current_measurement_index=0)
        await ask_next_custom_measurement(message, state)
    else:
        # Нет пользовательских измерений, записываем стандартные данные
        await save_complete_data(message, state)

async def ask_next_custom_measurement(message: Message, state: FSMContext):
    """Спрашивает следующее пользовательское измерение"""
    data = await state.get_data()
    custom_measurements = data.get('custom_measurements', [])
    current_index = data.get('current_measurement_index', 0)
    
    if current_index >= len(custom_measurements):
        # Все измерения собраны, сохраняем данные
        await save_complete_data(message, state)
        return
    
    measurement = custom_measurements[current_index]
    measurement_name = measurement['name']
    measurement_type = measurement['type']
    
    if measurement_type == 'numeric':
        max_value = measurement['max_value']
        await message.reply(f"{measurement_name} (0-{max_value})?")
    else:
        await message.reply(f"{measurement_name} (текст)?")
    
    await state.update_data(current_measurement=measurement)
    await state.set_state(Form.custom_measurement)
    logger.info(f"Спрашиваем измерение: {measurement_name}")

@router.message(Form.custom_measurement)
async def get_custom_measurement(message: Message, state: FSMContext):
    """Обрабатывает ответ на пользовательское измерение"""
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    value = message.text
    
    data = await state.get_data()
    current_measurement = data.get('current_measurement')
    current_index = data.get('current_measurement_index', 0)
    custom_measurements = data.get('custom_measurements', [])
    
    # Валидация для цифровых измерений
    if current_measurement['type'] == 'numeric':
        try:
            num_value = int(value)
            max_value = current_measurement['max_value']
            if num_value < 0 or num_value > max_value:
                await message.reply(f"❌ Значение должно быть от 0 до {max_value}. Попробуйте еще раз:")
                return
        except ValueError:
            await message.reply("❌ Пожалуйста, введите число:")
            return
    
    # Сохраняем значение
    measurement_name = current_measurement['name']
    custom_values = data.get('custom_values', {})
    custom_values[measurement_name] = value
    await state.update_data(custom_values=custom_values)
    
    # Переходим к следующему измерению
    next_index = current_index + 1
    await state.update_data(current_measurement_index=next_index)
    
    if next_index < len(custom_measurements):
        await ask_next_custom_measurement(message, state)
    else:
        # Все измерения собраны, сохраняем данные
        await save_complete_data(message, state)
    
    logger.info(f"Получено значение для {measurement_name}: {value}")

async def save_complete_data(message: Message, state: FSMContext):
    """Сохраняет полные данные в таблицу"""
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    data = await state.get_data()
    user_id_str = str(user_id)
    
    logger.info(f"Данные для записи от {username}: fatigue={data.get('fatigue')}, mood={data.get('mood')}, sleep={data.get('sleep')}, physical_load={data.get('physical_load')}, mental_load={data.get('mental_load')}, symptoms={data.get('symptoms')}, notes={data.get('notes')}, custom_values={data.get('custom_values', {})}")

    if user_id_str not in user_sheets:
        logger.error(f"Пользователь {username} не подключил таблицу")
        await message.reply("Сначала отправь ссылку на таблицу через /setsheet")
        return

    try:
        logger.info(f"Попытка записи в таблицу для пользователя {username}")
        sheet = client.open_by_key(user_sheets[user_id_str]).sheet1
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Базовые данные
        row_data = [
            now, 
            data.get('fatigue', ''), 
            data.get('mood', ''), 
            data.get('sleep', ''),
            data.get('physical_load', ''),
            data.get('mental_load', ''),
            data.get('symptoms', ''),
            data.get('notes', '')
        ]
        
        # Добавляем пользовательские измерения
        custom_measurements = data.get('custom_measurements', [])
        custom_values = data.get('custom_values', {})
        
        for measurement in custom_measurements:
            measurement_name = measurement['name']
            value = custom_values.get(measurement_name, '')
            row_data.append(value)
        
        logger.info(f"Записываем строку: {row_data}")
        
        sheet.append_row(row_data)
        logger.info(f"✅ Данные успешно записаны в таблицу для пользователя {username}")
        
        await message.reply(
            "✅ Записал! 🙌\n\n📊 Все данные сохранены в таблицу.\n\nХотите записать еще одну запись?",
            reply_markup=get_track_keyboard()
        )
    except Exception as e:
        logger.error(f"❌ Ошибка при записи в таблицу для пользователя {username}: {str(e)}")
        logger.error(f"Тип ошибки: {type(e).__name__}")
        await message.reply(f"❌ Ошибка при записи в таблицу: {str(e)}")
    
    await state.clear()
    logger.info(f"Состояние очищено для пользователя {username}")

# Обработчики для создания измерений
@router.message(MeasurementForm.measurement_name)
async def get_measurement_name(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    measurement_name = message.text.strip()
    
    if len(measurement_name) > 50:
        await message.reply("❌ Название слишком длинное. Максимум 50 символов.")
        return
    
    await state.update_data(measurement_name=measurement_name)
    await message.reply(
        f"📝 Название: {measurement_name}\n\n"
        f"Выберите тип измерения:\n"
        f"1️⃣ Цифровой (0-10)\n"
        f"2️⃣ Текстовый\n\n"
        f"Отправьте 1 или 2:"
    )
    await state.set_state(MeasurementForm.measurement_type)
    logger.info(f"Получено название измерения от {username}: {measurement_name}")

@router.message(MeasurementForm.measurement_type)
async def get_measurement_type(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    measurement_type = message.text.strip()
    
    if measurement_type not in ['1', '2']:
        await message.reply("❌ Пожалуйста, отправьте 1 или 2:")
        return
    
    measurement_type = 'numeric' if measurement_type == '1' else 'text'
    await state.update_data(measurement_type=measurement_type)
    
    if measurement_type == 'numeric':
        await message.reply(
            f"📊 Тип: Цифровой\n\n"
            f"Введите максимальное значение (по умолчанию 10):"
        )
        await state.set_state(MeasurementForm.max_value)
    else:
        # Для текстового типа сразу сохраняем
        data = await state.get_data()
        await save_measurement(message, state, data)
    
    logger.info(f"Получен тип измерения от {username}: {measurement_type}")

@router.message(MeasurementForm.max_value)
async def get_max_value(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    max_value_text = message.text.strip()
    
    try:
        max_value = int(max_value_text)
        if max_value < 1 or max_value > 100:
            await message.reply("❌ Максимальное значение должно быть от 1 до 100:")
            return
    except ValueError:
        await message.reply("❌ Пожалуйста, введите число:")
        return
    
    await state.update_data(max_value=max_value)
    data = await state.get_data()
    await save_measurement(message, state, data)
    logger.info(f"Получено максимальное значение от {username}: {max_value}")

async def save_measurement(message: Message, state: FSMContext, data: dict):
    """Сохраняет новое измерение"""
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    user_id_str = str(user_id)
    
    measurement_name = data.get('measurement_name')
    measurement_type = data.get('measurement_type')
    max_value = data.get('max_value', 10)
    
    # Сохраняем в базу данных
    success = await db.add_custom_measurement(
        user_id_str, 
        measurement_name, 
        measurement_type, 
        0, 
        max_value
    )
    
    if success:
        # Добавляем столбец в таблицу
        sheet_id = user_sheets[user_id_str]
        column_added = await add_column_to_sheet(sheet_id, measurement_name)
        
        if column_added:
            await message.reply(
                f"✅ Измерение '{measurement_name}' добавлено!\n\n"
                f"📊 Тип: {'Цифровой (0-' + str(max_value) + ')' if measurement_type == 'numeric' else 'Текстовый'}\n"
                f"📝 Столбец добавлен в таблицу\n\n"
                f"💡 Теперь при записи данных бот спросит это значение.",
                reply_markup=get_main_keyboard()
            )
        else:
            await message.reply(
                f"✅ Измерение '{measurement_name}' добавлено в базу!\n\n"
                f"⚠️ Не удалось добавить столбец в таблицу. Попробуйте еще раз.",
                reply_markup=get_main_keyboard()
            )
    else:
        await message.reply(
            "❌ Ошибка при сохранении измерения. Попробуйте еще раз.",
            reply_markup=get_main_keyboard()
        )
    
    await state.clear()
    logger.info(f"Измерение сохранено для пользователя {username}: {measurement_name}")

async def main():
    logger.info("🚀 Запуск бота...")
    
    try:
        # Инициализируем базу данных
        logger.info("🗄️ Инициализация базы данных...")
        try:
            await db.init()
            logger.info("✅ База данных инициализирована успешно")
        except Exception as e:
            logger.error(f"❌ Ошибка при инициализации БД: {e}")
            logger.warning("⚠️ Продолжаем работу без базы данных")
        
        # Загружаем данные пользователей из БД
        logger.info("📥 Загрузка данных пользователей из БД...")
        global user_sheets
        try:
            user_sheets = await db.get_all_user_sheets()
            logger.info(f"✅ Загружено {len(user_sheets)} привязок пользователей к таблицам")
        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке данных из БД: {e}")
            user_sheets = {}
            logger.warning("⚠️ Используем пустой словарь пользователей")
        
        # Удаляем webhook перед запуском polling
        logger.info("📡 Удаление webhook...")
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook удален успешно")
        
        logger.info("🔄 Начинаем polling...")
        # Запускаем с минимальными настройками
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {str(e)}")
        raise

if __name__ == '__main__':
    asyncio.run(main())
