from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)
import os
from dotenv import load_dotenv

HEIGHT, WEIGHT, AGE, GENDER, ACTIVITY = range(5)
user_data = {}

# Клавиатура меню
main_menu = ReplyKeyboardMarkup(
    [[KeyboardButton("/start")], [KeyboardButton("/help")]],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я помогу рассчитать твою норму калорий.\nВведите свой рост в сантиметрах:",
        reply_markup=main_menu
    )
    return HEIGHT

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Чтобы начать, нажмите /start и следуйте инструкциям.\n"
        "Если хотите прервать — /cancel"
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог отменён. Введите /start чтобы начать заново.")
    return ConversationHandler.END

async def get_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_data[update.effective_chat.id] = {"height": float(update.message.text)}
        await update.message.reply_text("Теперь введите свой вес в кг:")
        return WEIGHT
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное число (рост в см).")

async def get_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_data[update.effective_chat.id]["weight"] = float(update.message.text)
        await update.message.reply_text("Введите свой возраст:")
        return AGE
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное число (вес в кг).")

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_data[update.effective_chat.id]["age"] = float(update.message.text)
        keyboard = [["Мужчина", "Женщина"]]
        await update.message.reply_text("Укажите ваш пол:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return GENDER
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное число (возраст).")

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gender = update.message.text
    if gender not in ["Мужчина", "Женщина"]:
        await update.message.reply_text("Пожалуйста, выберите пол из предложенных вариантов.")
        return GENDER
    user_data[update.effective_chat.id]["gender"] = gender
    keyboard = [["1", "2"], ["3", "4"], ["5"]]
    await update.message.reply_text(
        "Выберите уровень активности (1-5):\n"
        "1. Минимальный (1.2)\n"
        "2. Легкая активность (1.375)\n"
        "3. Умеренная (1.55)\n"
        "4. Высокая активность (1.725)\n"
        "5. Очень высокая (1.9)",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )
    return ACTIVITY

async def get_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    activity_map = {"1": 1.2, "2": 1.375, "3": 1.55, "4": 1.725, "5": 1.9}
    choice = update.message.text
    if choice not in activity_map:
        await update.message.reply_text("Пожалуйста, выберите число от 1 до 5.")
        return ACTIVITY

    user_data[update.effective_chat.id]["activity"] = activity_map[choice]
    data = user_data[update.effective_chat.id]
    height_m = data["height"] / 100
    imt = round(data["weight"] / (height_m ** 2), 2)

    if data["gender"] == "Мужчина":
        bmr = round((10 * data["weight"]) + (6.25 * data["height"] - 5 * data["age"] + 5))
    else:
        bmr = round((10 * data["weight"]) + (6.25 * data["height"] - 5 * data["age"] - 161))

    tdee = round(bmr * data["activity"])

    if imt < 18.5:
        rec = f"Ваш ИМТ: {imt} (недостаток). Рекомендуемая калорийность: {round(tdee * 1.15)} ккал."
    elif 18.5 <= imt <= 24.9:
        rec = f"Ваш ИМТ: {imt} (норма). Для поддержания веса: {tdee} ккал."
    elif 25 <= imt <= 29.9:
        rec = f"Ваш ИМТ: {imt} (избыточный). Рекомендуемая калорийность: {round(tdee * 0.85)} ккал."
    else:
        rec = f"Ваш ИМТ: {imt} (ожирение). Рекомендуемая калорийность: {round(tdee * 0.8)} ккал или {round(tdee * 0.75)} ккал для усиленного похудения."

    await update.message.reply_text(f"{rec}\n\nСпасибо за использование бота!")
    return ConversationHandler.END

# Запуск бота
if __name__ == '__main__':
    load_dotenv()
    TOKEN = os.getenv("TOKEN")

    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_height)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weight)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)],
            ACTIVITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_activity)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))

    print("Бот запущен...")
    app.run_polling()
