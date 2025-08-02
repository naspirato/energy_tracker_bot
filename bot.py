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

❓ /help - Показать это сообщение

💡 Рекомендуем создать новую таблицу через /createsheet!"""
    
    await message.reply(help_text)
    logger.info(f"Отправлена справка пользователю {username}")

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
        
    elif data == "show_help":
        help_text = """📚 Доступные команды:

➕ /createsheet - Создать новую Google таблицу
🔗 /setsheet <ссылка> - Подключить существующую таблицу
📊 /track - Начать запись данных о состоянии
📈 /status - Проверить подключенную таблицу
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
    data = await state.get_data()
    user_id_str = str(user_id)
    
    logger.info(f"Данные для записи от {username}: fatigue={data.get('fatigue')}, mood={data.get('mood')}, sleep={data.get('sleep')}, physical_load={data.get('physical_load')}, mental_load={data.get('mental_load')}, symptoms={data.get('symptoms')}, notes={data.get('notes')}")

    if user_id_str not in user_sheets:
        logger.error(f"Пользователь {username} не подключил таблицу")
        await message.reply("Сначала отправь ссылку на таблицу через /setsheet")
        return

    try:
        logger.info(f"Попытка записи в таблицу для пользователя {username}")
        sheet = client.open_by_key(user_sheets[user_id_str]).sheet1
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
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
