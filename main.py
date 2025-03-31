from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)
import os
from dotenv import load_dotenv

# Состояния
MENU, HEIGHT, WEIGHT, AGE, GENDER, ACTIVITY, VIDEO = range(7)
user_data = {}

# Ссылки на видео дня
videos = {
    "1": "https://vm.tiktok.com/ZMBaR1Vs1/",
    "2": "https://vm.tiktok.com/ZMBaRR3UG/",
    "3": "https://vm.tiktok.com/ZMBaRFVUd/",
    "4": "https://vm.tiktok.com/ZMBaR8BCM/",
    "5": "https://vm.tiktok.com/ZMBaR1WXU/"
}

# Старт
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Рассчитать калории"], ["Видео дня"]]
    await update.message.reply_text(
        "Привет! Что вы хотите сделать?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return MENU

# Главное меню
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if "калори" in text:
        await update.message.reply_text("Введите ваш рост в сантиметрах:")
        return HEIGHT
    elif "видео" in text:
        await update.message.reply_text("Выберите число от 1 до 5:")
        return VIDEO
    else:
        await update.message.reply_text("Пожалуйста, выберите действие из меню.")
        return MENU

# Видео дня
async def video_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text.strip()
    if choice not in videos:
        await update.message.reply_text("Пожалуйста, выберите цифру от 1 до 5.")
        return VIDEO

    link = videos[choice]
    message = (
        f"Ваше видео дня:\n{link}\n\n"
        "Если у вас нет доступа к TikTok/Instagram, отправьте эту ссылку боту "
        "@SaveAsBot, и он пришлёт вам видео прямо здесь."
    )
    await update.message.reply_text(message)
    return MENU

# Ввод роста
async def get_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_chat.id] = {"height": float(update.message.text)}
    await update.message.reply_text("Теперь введите свой вес в кг:")
    return WEIGHT

# Ввод веса
async def get_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_chat.id]["weight"] = float(update.message.text)
    await update.message.reply_text("Введите свой возраст:")
    return AGE

# Ввод возраста
async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_chat.id]["age"] = float(update.message.text)
    reply_keyboard = [["Мужчина", "Женщина"]]
    await update.message.reply_text(
        "Укажите ваш пол:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return GENDER

# Ввод пола
async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_chat.id]["gender"] = update.message.text
    reply_keyboard = [["1", "2"], ["3", "4"], ["5"]]
    await update.message.reply_text(
        "Выберите уровень активности (1-5):\n"
        "1. Минимальный (1.2)\n"
        "2. Легкая активность (1.375)\n"
        "3. Умеренная (1.55)\n"
        "4. Высокая активность (1.725)\n"
        "5. Очень высокая (1.9)",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return ACTIVITY

# Ввод активности и расчёт
async def get_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_chat.id]["activity"] = float({
        "1": 1.2, "2": 1.375, "3": 1.55, "4": 1.725, "5": 1.9
    }[update.message.text])

    data = user_data[update.effective_chat.id]
    height = data["height"]
    weight = data["weight"]
    age = data["age"]
    gender = data["gender"]
    activity = data["activity"]

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

    await update.message.reply_text(f"{rec}\n\nСпасибо за использование бота!")
    return MENU

# Отмена
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог отменён. Введите /start чтобы начать заново.")
    return ConversationHandler.END

# Запуск бота
if __name__ == "__main__":
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
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    print("Бот запущен...")
    app.run_polling()