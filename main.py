import logging
import os
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)

# Состояния
MENU, HEIGHT, WEIGHT, AGE, GENDER, ACTIVITY, VIDEO = range(7)

# Ссылки на видео дня
VIDEOS = {
    "1": "https://vm.tiktok.com/ZMBaR1Vs1/",
    "2": "https://vm.tiktok.com/ZMBaRR3UG/",
    "3": "https://vm.tiktok.com/ZMBaRFVUd/",
    "4": "https://vm.tiktok.com/ZMBaR8BCM/",
    "5": "https://vm.tiktok.com/ZMBaR1WXU/"
}

BACK_TO_MENU = "В меню"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def main_menu_keyboard():
    return ReplyKeyboardMarkup([["Рассчитать калории"], ["Видео дня"]], one_time_keyboard=True, resize_keyboard=True)

async def check_back_to_menu(text: str, update: Update):
    """Проверяет, ввёл ли пользователь команду 'В меню'. Если да – возвращает главное меню."""
    if text.strip().lower() == BACK_TO_MENU.lower():
        await update.message.reply_text(
            "Вы вернулись в главное меню. Что хотите сделать?",
            reply_markup=main_menu_keyboard()
        )
        return True
    return False

# Старт: приветствие и показ главного меню
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()  # очищаем данные, если они были
    await update.message.reply_text(
        "Привет! Что вы хотите сделать?",
        reply_markup=main_menu_keyboard()
    )
    return MENU

# Главное меню: выбор между расчётом калорий и видео дня
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    if "калори" in text:
        await update.message.reply_text(
            "Введите ваш рост в сантиметрах:",
            reply_markup=ReplyKeyboardMarkup([[BACK_TO_MENU]], resize_keyboard=True)
        )
        return HEIGHT
    elif "видео" in text:
        await update.message.reply_text(
            "Выберите число от 1 до 5:",
            reply_markup=ReplyKeyboardMarkup([["1", "2", "3"], ["4", "5"], [BACK_TO_MENU]], resize_keyboard=True)
        )
        return VIDEO
    else:
        await update.message.reply_text("Пожалуйста, выберите действие из меню.", reply_markup=main_menu_keyboard())
        return MENU

# Видео дня: выбор и вывод ссылки
async def video_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if await check_back_to_menu(text, update):
        return MENU

    if text not in VIDEOS:
        await update.message.reply_text("Пожалуйста, выберите цифру от 1 до 5 или нажмите 'В меню'.")
        return VIDEO

    link = VIDEOS[text]
    message = (
        f"Ваше видео дня:\n{link}\n\n"
        "Если у вас нет доступа к TikTok/Instagram, отправьте эту ссылку боту "
        "@SaveAsBot, и он пришлёт вам видео прямо здесь."
    )
    await update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup([[BACK_TO_MENU]], resize_keyboard=True))
    return MENU

# Рост: ввод и проверка
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

# Вес: ввод и проверка
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

# Возраст: ввод и проверка
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

# Пол: выбор
async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if await check_back_to_menu(text, update):
        return MENU

    if text.lower() not in ["мужчина", "женщина"]:
        await update.message.reply_text("Пожалуйста, выберите 'Мужчина' или 'Женщина'.",
                                          reply_markup=ReplyKeyboardMarkup([["Мужчина", "Женщина"], [BACK_TO_MENU]], resize_keyboard=True))
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

# Активность: ввод, расчёт и вывод результата
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
        await update.message.reply_text("Некоторые данные отсутствуют. Пожалуйста, начните заново с /start.")
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

    await update.message.reply_text(f"{rec}\n\nСпасибо за использование бота!",
                                    reply_markup=ReplyKeyboardMarkup([[BACK_TO_MENU]], resize_keyboard=True))
    return MENU

# Отмена диалога
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог отменён. Введите /start чтобы начать заново.")
    return ConversationHandler.END

def main():
    load_dotenv()
    TOKEN = os.getenv("TOKEN")
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
            VIDEO: [MessageHandler(filters.TEXT & ~filters.COMMAND, video_day)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv_handler)
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()