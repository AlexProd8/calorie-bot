import logging
import os
import datetime
import tempfile
import traceback
import requests
import mimetypes
from io import BytesIO
from telegram import Update, ReplyKeyboardMarkup, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters
)
from yt_dlp import YoutubeDL

# Получаем токен и идентификатор админ-чата (или администратора) из переменных окружения
TOKEN = os.environ.get("TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")  # Задайте этот ID в настройках Railway или GitHub

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------- Состояния диалога ----------------
# Состояния для расчёта калорий, видео и валют совпадают с прежними
MENU, HEIGHT, WEIGHT, AGE, GENDER, ACTIVITY, VIDEO = range(7)
CURRENCY_FROM, CURRENCY_TO, CURRENCY_AMOUNT, CURRENCY_RESULT = range(7, 11)
FEEDBACK = 11  # Новое состояние для ввода отзыва

BACK_TO_MENU = "В меню"
AVAILABLE_CURRENCIES = [ "RUB", "UZS", "BYN", "USD", "EUR", "CHF", "TJS", "KGS" ]
PIVOT = "USD"

# ---------------- Клавиатуры ----------------
def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["Рассчитать калории"],
            ["Видео по вашей ссылке"],
            ["Конвертация валют"],
            ["Информация"],
            ["Оставить отзыв"]  # Новая кнопка для отзывов
        ],
        one_time_keyboard=True,
        resize_keyboard=True
    )

def currency_keyboard():
    rows = []
    row = []
    for i, cur in enumerate(AVAILABLE_CURRENCIES, start=1):
        row.append(cur)
        if i % 3 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([BACK_TO_MENU])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

# ---------------- Функция логирования команд ----------------
def log_command(update: Update, command_name: str):
    user = update.effective_user
    log_message = f"{datetime.datetime.now()}: Команда {command_name} вызвана пользователем {user.id} - {user.username} - {user.first_name}"
    logger.info(log_message)
    # Записываем в файл для лога использования (можно использовать другие способы хранения)
    with open("bot_usage.log", "a", encoding="utf-8") as log_file:
        log_file.write(log_message + "\n")

# ---------------- Отслеживание пользователей ----------------
def log_user_start(update: Update):
    user = update.effective_user
    log_line = f"{datetime.datetime.now()}, {user.id}, {user.username}, {user.first_name}\n"
    with open("user_data.csv", "a", encoding="utf-8") as f:
        f.write(log_line)
    logger.info(f"Зарегистрирован пользователь: {user.id} - {user.username} - {user.first_name}")

# ---------------- Вспомогательные функции ----------------
async def check_back_to_menu(text: str, update: Update):
    if text.strip().lower() == BACK_TO_MENU.lower():
        await update.message.reply_text(
            "Вы вернулись в главное меню. Что хотите сделать?",
            reply_markup=main_menu_keyboard()
        )
        return True
    return False

def expand_url(url: str) -> str:
    try:
        r = requests.head(url, allow_redirects=True, timeout=10)
        return r.url
    except Exception:
        return url

# ---------------- Команды /start и /cancel ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_command(update, "/start")
    log_user_start(update)
    context.user_data.clear()
    await update.message.reply_text(
        "Привет! Что вы хотите сделать?",
        reply_markup=main_menu_keyboard()
    )
    return MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_command(update, "/cancel")
    await update.message.reply_text("Диалог отменён. Введите /start, чтобы начать заново.")
    return ConversationHandler.END

# ---------------- Главное меню ----------------
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    if "калори" in text:
        log_command(update, "Рассчитать калории")
        await update.message.reply_text(
            "Введите ваш рост в сантиметрах:",
            reply_markup=ReplyKeyboardMarkup([[BACK_TO_MENU]], resize_keyboard=True)
        )
        return HEIGHT
    elif "ссыл" in text:
        log_command(update, "Видео по вашей ссылке")
        await update.message.reply_text(
            "Отправьте ссылку на видео с TikTok или Instagram:",
            reply_markup=ReplyKeyboardMarkup([[BACK_TO_MENU]], resize_keyboard=True)
        )
        return VIDEO
    elif "информа" in text:
        log_command(update, "Информация")
        info_text = (
            "Это бот, который умеет:\n"
            "• Рассчитывать норму калорий на основе введённых параметров (рост, вес, возраст, пол, уровень активности).\n"
            "• Загружать видео с TikTok и Instagram.\n"
            "• Конвертировать валюты.\n\n"
            "Обратите внимание: бот пока не умеет скачивать картинки с Instagram и TikTok. "
            "Если вы отправите ссылку на изображение, бот ответит, что эта функция в разработке.\n\n"
            "Разработчик – AlexProd.\n"
            "Спасибо, что используете бота!"
        )
        await update.message.reply_text(info_text, reply_markup=main_menu_keyboard())
        return MENU
    elif "валют" in text or "конвер" in text:
        log_command(update, "Конвертация валют")
        await update.message.reply_text(
            "Выберите валюту, из которой конвертируем:",
            reply_markup=currency_keyboard()
        )
        return CURRENCY_FROM
    elif "отзыв" in text:
        log_command(update, "Оставить отзыв")
        await update.message.reply_text("Пожалуйста, введите ваш отзыв:")
        return FEEDBACK
    else:
        await update.message.reply_text(
            "Пожалуйста, выберите действие из меню.",
            reply_markup=main_menu_keyboard()
        )
        return MENU

# ---------------- Раздел отзывов ----------------
async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    feedback_text = update.message.text.strip()
    user = update.effective_user
    # Формирование сообщения с данными пользователя и текстом отзыва
    feedback_message = (
        f"Новый отзыв от {user.first_name} (ID: {user.id}, username: {user.username}):\n"
        f"{feedback_text}"
    )
    try:
        # Отправляем отзыв в админ-чат
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=feedback_message)
        logger.info(f"Отзыв от {user.id} отправлен администратору.")
    except Exception as e:
        logger.error(f"Ошибка отправки отзыва: {e}")
    await update.message.reply_text("Спасибо за ваш отзыв!")
    return MENU

# ---------------- Функции для расчёта калорий ----------------
async def get_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if await check_back_to_menu(text, update):
        return MENU
    try:
        height = float(text)
        context.user_data["height"] = height
        await update.message.reply_text(
            "Теперь введите свой вес в кг:",
            reply_markup=ReplyKeyboardMarkup([[BACK_TO_MENU]], resize_keyboard=True)
        )
        return WEIGHT
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное числовое значение для роста.")
        return HEIGHT

async def get_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if await check_back_to_menu(text, update):
        return MENU
    try:
        weight = float(text)
        context.user_data["weight"] = weight
        await update.message.reply_text(
            "Введите свой возраст:",
            reply_markup=ReplyKeyboardMarkup([[BACK_TO_MENU]], resize_keyboard=True)
        )
        return AGE
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное числовое значение для веса.")
        return WEIGHT

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if await check_back_to_menu(text, update):
        return MENU
    try:
        age = float(text)
        context.user_data["age"] = age
        keyboard = [["Мужчина", "Женщина"], [BACK_TO_MENU]]
        await update.message.reply_text("Укажите ваш пол:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return GENDER
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное числовое значение для возраста.")
        return AGE

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if await check_back_to_menu(text, update):
        return MENU
    if text.lower() not in ["мужчина", "женщина"]:
        await update.message.reply_text(
            "Пожалуйста, выберите 'Мужчина' или 'Женщина'.",
            reply_markup=ReplyKeyboardMarkup([["Мужчина", "Женщина"], [BACK_TO_MENU]], resize_keyboard=True)
        )
        return GENDER
    context.user_data["gender"] = text.title()
    keyboard = [["1", "2"], ["3", "4"], ["5"], [BACK_TO_MENU]]
    message = (
        "Выберите уровень активности (1-5):\n"
        "1. Минимальный (1.2)\n"
        "2. Лёгкая активность (1.375)\n"
        "3. Умеренная (1.55)\n"
        "4. Высокая активность (1.725)\n"
        "5. Очень высокая (1.9)"
    )
    await update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return ACTIVITY

async def get_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if await check_back_to_menu(text, update):
        return MENU

    activity_mapping = {"1": 1.2, "2": 1.375, "3": 1.55, "4": 1.725, "5": 1.9}
    if text not in activity_mapping:
        await update.message.reply_text("Пожалуйста, выберите цифру от 1 до 5 или нажмите 'В меню'.")
        return ACTIVITY
    context.user_data["activity"] = activity_mapping[text]
    try:
        height = context.user_data["height"]
        weight = context.user_data["weight"]
        age = context.user_data["age"]
        gender = context.user_data["gender"]
        activity = context.user_data["activity"]
    except KeyError:
        await update.message.reply_text("Данные введены не полностью. Попробуйте заново командой /start.")
        return ConversationHandler.END

    height_m = height / 100
    imt = round(weight / (height_m ** 2), 2)
    if gender == "Мужчина":
        bmr = round((10 * weight) + (6.25 * height - 5 * age + 5))
    else:
        bmr = round((10 * weight) + (6.25 * height - 5 * age - 161))
    tdee = round(bmr * activity)

    if imt < 18.5:
        rec = f"Ваш ИМТ: {imt} (недостаток). Рекомендуемая калорийность: {round(tdee * 1.15)} ккал."
    elif 18.5 <= imt <= 24.9:
        rec = f"Ваш ИМТ: {imt} (норма). Для поддержания веса: {tdee} ккал."
    elif 25 <= imt <= 29.9:
        rec = f"Ваш ИМТ: {imt} (избыточный). Рекомендуемая калорийность: {round(tdee * 0.85)} ккал."
    else:
        rec = f"Ваш ИМТ: {imt} (ожирение). Рекомендуемая калорийность: {round(tdee * 0.8)} ккал или {round(tdee * 0.75)} ккал для усиленного похудения."

    await update.message.reply_text(
        f"{rec}\n\nСпасибо за использование бота!",
        reply_markup=ReplyKeyboardMarkup([[BACK_TO_MENU]], resize_keyboard=True)
    )
    return MENU

# ---------------- Конвертация валют ----------------
async def currency_from(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    if await check_back_to_menu(text, update):
        return MENU

    if text not in AVAILABLE_CURRENCIES:
        await update.message.reply_text(
            "Пожалуйста, выберите одну из доступных валют или нажмите 'В меню'.",
            reply_markup=currency_keyboard()
        )
        return CURRENCY_FROM

    context.user_data["currency_from"] = text
    await update.message.reply_text(
        f"Исходная валюта: {text}\nТеперь выберите валюту, в которую переводим:",
        reply_markup=currency_keyboard()
    )
    return CURRENCY_TO

async def currency_to(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    if await check_back_to_menu(text, update):
        return MENU

    if text not in AVAILABLE_CURRENCIES:
        await update.message.reply_text(
            "Пожалуйста, выберите одну из доступных валют или нажмите 'В меню'.",
            reply_markup=currency_keyboard()
        )
        return CURRENCY_TO

    context.user_data["currency_to"] = text
    await update.message.reply_text(
        f"Целевая валюта: {text}\nВведите сумму, которую нужно конвертировать:",
        reply_markup=ReplyKeyboardMarkup([[BACK_TO_MENU]], resize_keyboard=True)
    )
    return CURRENCY_AMOUNT

async def currency_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if await check_back_to_menu(text, update):
        return MENU
    try:
        amount = float(text)
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите числовое значение суммы.")
        return CURRENCY_AMOUNT

    cur_from = context.user_data["currency_from"]
    cur_to = context.user_data["currency_to"]
    url = f"https://open.er-api.com/v6/latest/{PIVOT}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get("result") != "success" or "rates" not in data:
            raise ValueError("Невалидный ответ API.")
        rates = data["rates"]
        if cur_from not in rates or cur_to not in rates:
            raise ValueError("Одна из валют не поддерживается API.")
        rate_from = rates[cur_from]
        rate_to = rates[cur_to]
        if rate_from == 0:
            raise ZeroDivisionError("Курс для исходной валюты равен 0.")
        rate_final = rate_to / rate_from
        result = round(rate_final * amount, 2)
        message = (
            f"{amount} {cur_from} = {result} {cur_to}\n\n"
            "Хотите выбрать другие валюты или вернуться в меню?"
        )
        keyboard = [["Выбрать валюты заново"], [BACK_TO_MENU]]
        await update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    except Exception as e:
        logger.error(f"Ошибка при конвертации валют: {e}")
        await update.message.reply_text("Ошибка при получении курса валют. Попробуйте позже.")
        keyboard = [["Выбрать валюты заново"], [BACK_TO_MENU]]
        await update.message.reply_text("Хотите выбрать другие валюты или вернуться в меню?", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return CURRENCY_RESULT

async def currency_result_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    if "заново" in text or "выбрать" in text or "валют" in text:
        await update.message.reply_text(
            "Выберите валюту, из которой конвертируем:",
            reply_markup=currency_keyboard()
        )
        return CURRENCY_FROM
    else:
        await update.message.reply_text(
            "Вы вернулись в главное меню. Что хотите сделать?",
            reply_markup=main_menu_keyboard()
        )
        return MENU

# ---------------- Скачивание видео ----------------
async def video_by_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if await check_back_to_menu(text, update):
        return MENU

    if not text.startswith("http"):
        await update.message.reply_text("Пожалуйста, отправьте корректную ссылку.")
        return VIDEO

    allowed_sources = ["tiktok.com", "instagram.com"]
    if not any(domain in text for domain in allowed_sources):
        await update.message.reply_text(
            "Я могу обрабатывать только ссылки с TikTok или Instagram. Попробуйте другую ссылку."
        )
        return VIDEO

    await update.message.reply_text("Скачиваю медиа, пожалуйста, подождите...")
    expanded_url = expand_url(text)
    if "instagram.com" in expanded_url:
        referer = "https://www.instagram.com/"
    else:
        referer = "https://www.tiktok.com/"

    ydl_opts = {
        'outtmpl': '%(id)s.%(ext)s',
        'format': 'mp4',
        'quiet': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36',
            'Referer': referer
        },
        'geo_bypass': True,
        'geo_bypass_country': 'US',
        'noprogress': True
    }
    success = False
    try:
        with tempfile.TemporaryDirectory() as tmpdirname:
            ydl_opts['outtmpl'] = os.path.join(tmpdirname, '%(id)s.%(ext)s')
            with YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(expanded_url, download=True)
                filename = ydl.prepare_filename(info_dict)
            ext = os.path.splitext(filename)[1].lower()
            if ext in ['.mp4', '.mov', '.mkv', '.webm']:
                with open(filename, 'rb') as media_file:
                    await update.message.reply_video(video=media_file)
                success = True
            elif ext in ['.jpg', '.jpeg', '.png', '.webp']:
                await update.message.reply_text(
                    "Бот пока что не может скачать картинки с Instagram и TikTok, но AlexProd старается и в будущем добавит эту возможность."
                )
                success = True
            else:
                with open(filename, 'rb') as media_file:
                    await update.message.reply_document(document=media_file)
                success = True
    except Exception:
        logger.error("Ошибка при скачивании через yt-dlp:\n%s", traceback.format_exc())
    if not success:
        try:
            response = requests.get(expanded_url, timeout=15)
            response.raise_for_status()
            content_type = response.headers.get('Content-Type', '').lower()
            if 'image' in content_type:
                await update.message.reply_text(
                    "Бот пока что не может скачать картинки с Instagram и TikTok, но AlexProd старается и в будущем добавит эту возможность."
                )
                success = True
            elif 'video' in content_type:
                ext = mimetypes.guess_extension(content_type)
                if not ext:
                    ext = ".mp4"
                filename = "downloaded_file" + ext
                file_stream = BytesIO(response.content)
                file_stream.name = filename
                await update.message.reply_video(video=file_stream)
                success = True
            else:
                await update.message.reply_text(
                    "Не удалось определить тип медиа. Возможно, ссылка неправильная или недоступна."
                )
        except Exception:
            logger.error("Ошибка при скачивании напрямую:\n%s", traceback.format_exc())
    if not success:
        await update.message.reply_text(
            "Не удалось скачать медиа, Возможно, ссылка неправильная или недоступна."
        )
    await update.message.reply_text(
        "Если хотите, отправьте другую ссылку или нажмите 'В меню' для возврата в главное меню."
    )
    return VIDEO

# ---------------- Регистрация команд ----------------
async def set_bot_commands(app):
    commands = [
        BotCommand("start", "Начало работы с ботом"),
        BotCommand("cancel", "Отменить текущий диалог")
    ]
    await app.bot.set_my_commands(commands)

# --------------- Основной main ----------------
def main():
    app = ApplicationB()
    import asyncio
    asyncio.run(app.run_polling())

if __name__ == "__main__":
    print("Bot is starting...")
    main()