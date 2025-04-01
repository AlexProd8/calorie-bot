import logging
import os
import tempfile
import traceback
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters
)
from yt_dlp import YoutubeDL

# Если вы разворачиваете на Railway и задаёте переменные окружения там,
# можно просто получить токен через os.environ:
TOKEN = os.environ.get("TOKEN")

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния диалога
MENU, HEIGHT, WEIGHT, AGE, GENDER, ACTIVITY, VIDEO = range(7)

# Текст для возврата в меню
BACK_TO_MENU = "В меню"

# Формирование клавиатуры главного меню с тремя кнопками
def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        [["Рассчитать калории"],
         ["Видео по вашей ссылке"],
         ["Информация"]],
        one_time_keyboard=True, resize_keyboard=True
    )

# Универсальная проверка: если введён "В меню" — возвращаем главное меню
async def check_back_to_menu(text: str, update: Update):
    if text.strip().lower() == BACK_TO_MENU.lower():
        await update.message.reply_text(
            "Вы вернулись в главное меню. Что хотите сделать?",
            reply_markup=main_menu_keyboard()
        )
        return True
    return False

# Команда /start – запуск диалога
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Привет! Что вы хотите сделать?",
        reply_markup=main_menu_keyboard()
    )
    return MENU

# Обработчик главного меню
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()

    # Если пользователь выбрал "Рассчитать калории"
    if "калори" in text:
        await update.message.reply_text(
            "Введите ваш рост в сантиметрах:",
            reply_markup=ReplyKeyboardMarkup([[BACK_TO_MENU]], resize_keyboard=True)
        )
        return HEIGHT
    # Если выбрана опция "Видео по вашей ссылке"
    elif "ссыл" in text:
        await update.message.reply_text(
            "Отправьте ссылку на видео с TikTok или Instagram:",
            reply_markup=ReplyKeyboardMarkup([[BACK_TO_MENU]], resize_keyboard=True)
        )
        return VIDEO
    # Если выбрана опция "Информация"
    elif "информа" in text:
        info_text = (
            "Это бот, который умеет:\n"
            "• Рассчитывать норму калорий на основе введённых параметров (рост, вес, возраст, пол, уровень активности).\n"
            "• Загружать видео с TikTok и Instagram по вашей ссылке.\n\n"
            "Чтобы использовать бота, выберите нужную функцию в меню.\n\n"
            "Разработчик – AlexProd.\n"
            "Спасибо что используете бота."
        )
        await update.message.reply_text(info_text, reply_markup=main_menu_keyboard())
        return MENU
    else:
        await update.message.reply_text(
            "Пожалуйста, выберите действие из меню.",
            reply_markup=main_menu_keyboard()
        )
        return MENU

# Функции для расчёта калорий (без изменений)
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

# Новый режим: обработка видео по ссылке пользователя
# Режим остаётся активным до тех пор, пока пользователь не введёт "В меню"
async def video_by_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if await check_back_to_menu(text, update):
        return MENU
    # Проверяем, что ссылка начинается с "http"
    if not text.startswith("http"):
        await update.message.reply_text("Пожалуйста, отправьте корректную ссылку.")
        return VIDEO
    # Проверяем, что ссылка принадлежит TikTok или Instagram
    if "tiktok.com" not in text and "instagram.com" not in text:
        await update.message.reply_text(
            "Я могу отправлять видео только с TikTok или Instagram. Попробуйте другую ссылку."
        )
        return VIDEO
    await update.message.reply_text("Скачиваю видео, пожалуйста, подождите...")
    try:
        with tempfile.TemporaryDirectory() as tmpdirname:
            ydl_opts = {
                'outtmpl': os.path.join(tmpdirname, '%(id)s.%(ext)s'),
                'format': 'mp4',
                'quiet': True,
            }
            with YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(text, download=True)
                filename = ydl.prepare_filename(info_dict)
            with open(filename, 'rb') as video_file:
                await update.message.reply_video(video=video_file)
    except Exception:
        logger.error("Ошибка при скачивании видео:\n%s", traceback.format_exc())
        await update.message.reply_text("Не удалось скачать видео. Возможно, ссылка недоступна или некорректна.")
    await update.message.reply_text(
        "Если хотите, отправьте другую ссылку или нажмите 'В меню' для возврата в главное меню."
    )
    return VIDEO

# Обработчик отмены диалога
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог отменён. Введите /start, чтобы начать заново.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, menu)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_height)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weight)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)],
            ACTIVITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_activity)],
            VIDEO: [MessageHandler(filters.TEXT & ~filters.COMMAND, video_by_link)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(conv_handler)
    logger.info("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()