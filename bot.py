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

# Функции для создания кнопок
def get_main_keyboard() -> InlineKeyboardMarkup:
    """Создает основную клавиатуру с кнопками"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Записать данные", callback_data="track_data"),
            InlineKeyboardButton(text="📈 Статус", callback_data="check_status")
        ],
        [
            InlineKeyboardButton(text="❓ Помощь", callback_data="show_help"),
            InlineKeyboardButton(text="🔗 Изменить таблицу", callback_data="change_sheet")
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

# Словарь user_id -> Google Sheet ID
try:
    with open("usersheets.json", "r") as f:
        user_sheets = json.load(f)
except:
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
    
    response = """Привет! 👋 Я бот для отслеживания психологического состояния.

📋 Что я умею:
• Записывать данные о вашем состоянии в Google таблицы
• Отслеживать усталость, настроение и качество сна

🚀 Используйте кнопки ниже для навигации!"""
    
    await message.reply(response, reply_markup=get_main_keyboard())
    logger.info(f"Отправлен ответ пользователю {username}")

@router.message(Command("help"))
async def help_command(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    logger.info(f"Команда /help от пользователя {username} (ID: {user_id})")
    
    help_text = """📚 Доступные команды:

🔗 /setsheet <ссылка> - Подключить Google таблицу
   Пример: /setsheet https://docs.google.com/spreadsheets/d/...

📊 /track - Начать запись данных о состоянии
   Бот спросит: усталость (0-10), настроение (0-10), качество сна

📈 /status - Проверить подключенную таблицу

❓ /help - Показать это сообщение

💡 После подключения таблицы используйте /track для записи данных!"""
    
    await message.reply(help_text)
    logger.info(f"Отправлена справка пользователю {username}")

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
        
        user_sheets[str(user_id)] = sheet_id
        with open("usersheets.json", "w") as f:
            json.dump(user_sheets, f)
        
        logger.info(f"Таблица {sheet_id} подключена для пользователя {username}")
        await message.reply(
            "✅ Таблица подключена!\n\n📊 Теперь вы можете записывать данные о вашем состоянии.",
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
    if user_id_str in user_sheets:
        sheet_id = user_sheets[user_id_str]
        status_text = f"✅ Таблица подключена\n📊 ID таблицы: {sheet_id}\n\n📝 Используйте /track для записи данных"
    else:
        status_text = "❌ Таблица не подключена\n\n🔗 Используйте /setsheet <ссылка> для подключения таблицы"
    
    await message.reply(status_text)
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
        if user_id_str in user_sheets:
            sheet_id = user_sheets[user_id_str]
            status_text = f"✅ Таблица подключена\n📊 ID таблицы: {sheet_id}\n\n📝 Используйте кнопку 'Записать данные'"
        else:
            status_text = "❌ Таблица не подключена\n\n🔗 Используйте /setsheet <ссылка> для подключения таблицы"
        
        await callback.message.edit_text(status_text, reply_markup=get_main_keyboard())
        
    elif data == "show_help":
        help_text = """📚 Доступные команды:

🔗 /setsheet <ссылка> - Подключить Google таблицу
📊 /track - Начать запись данных о состоянии
📈 /status - Проверить подключенную таблицу
❓ /help - Показать это сообщение

💡 Используйте кнопки для быстрого доступа!"""
        
        await callback.message.edit_text(help_text, reply_markup=get_main_keyboard())
        
    elif data == "change_sheet":
        await callback.message.edit_text(
            "🔗 Отправьте новую ссылку на Google таблицу:\n\n/setsheet <ссылка>",
            reply_markup=get_main_keyboard()
        )
        
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
