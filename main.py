from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)
import os
import requests
from dotenv import load_dotenv

# Состояния
MENU, HEIGHT, WEIGHT, AGE, GENDER, ACTIVITY = range(6)

user_data = {}

supported = {
    supported = {
    "москва": "Moscow,ru",
    "московская область": "Moscow,ru",
    "подольск": "Podolsk,ru",
    "луганск": "Luhansk,ua"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Рассчитать калории", "Посмотреть погоду"]]
    await update.message.reply_text(
        "Привет! Что вы хотите сделать?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return MENU

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if text == "рассчитать калории":
        await update.message.reply_text("Введите свой рост в сантиметрах:")
        return HEIGHT
    elif text == "посмотреть погоду":
        await update.message.reply_text("Введите название города (Москва, Подольск, Московская область или Луганск):")
        return "WEATHER"
    else:
        await update.message.reply_text("Пожалуйста, выберите действие из меню.")
        return MENU

async def get_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text.lower()
    if city not in supported:
        await update.message.reply_text("Извините, этот город не поддерживается. Доступны: Москва, Подольск, Московская область и Луганск.")
        return MENU

    api_key = os.getenv("WEATHER_API")
    url = f"http://api.openweathermap.org/data/2.5/weather?q={supported[city]}&appid={api_key}&units=metric&lang=ru"
    response = requests.get(url).json()

    if response.get("main"):
        temp = response["main"]["temp"]
        desc = response["weather"][0]["description"]
        await update.message.reply_text(f"Погода в {update.message.text.title()}: {temp}°C, {desc}")
    else:
        await update.message.reply_text("Ошибка при получении погоды. Попробуйте позже.")
    return MENU

async def get_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_chat.id] = {"height": float(update.message.text)}
    await update.message.reply_text("Теперь введите свой вес в кг:")
    return WEIGHT

async def get_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_chat.id]["weight"] = float(update.message.text)
    await update.message.reply_text("Введите свой возраст:")
    return AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_chat.id]["age"] = float(update.message.text)
    keyboard = [["Мужчина", "Женщина"]]
    await update.message.reply_text(
        "Укажите ваш пол:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )
    return GENDER

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_chat.id]["gender"] = update.message.text
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

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог отменён. Введите /start чтобы начать заново.")
    return ConversationHandler.END

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
            "WEATHER": [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weather)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv_handler)
    print("Бот запущен...")
    app.run_polling()