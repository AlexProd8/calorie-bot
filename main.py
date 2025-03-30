from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)
import os
import requests
from dotenv import load_dotenv

# Состояния
MENU, HEIGHT, WEIGHT, AGE, GENDER, ACTIVITY, WEATHER = range(7)
user_data = {}

main_menu = ReplyKeyboardMarkup(
    [[KeyboardButton("Рассчитать калории"), KeyboardButton("Посмотреть погоду")]],
    resize_keyboard=True
)

cities_supported = {
    "москва": "Moscow",
    "московская область": "Moscow",
    "подольск": "Podolsk",
    "луганск": "Luhansk"
}

API_KEY = "c5f217b58b1873233f26574264a75988"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Что вы хотите сделать?",
        reply_markup=main_menu
    )
    return MENU

async def menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text.lower()
    if "калории" in choice:
        await update.message.reply_text("Введите свой рост в сантиметрах:")
        return HEIGHT
    elif "погода" in choice:
        await update.message.reply_text("Введите город (например: Москва, Подольск, Луганск):")
        return WEATHER
    else:
        await update.message.reply_text("Пожалуйста, выберите из меню.")
        return MENU

# Погода
async def get_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city_input = update.message.text.strip().lower()
    if city_input in cities_supported:
        city = cities_supported[city_input]
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric&lang=ru"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            weather = data['weather'][0]['description'].capitalize()
            temp = data['main']['temp']
            feels = data['main']['feels_like']
            humidity = data['main']['humidity']
            await update.message.reply_text(
                f"Погода в {city_input.title()}:\n"
                f"{weather}, температура: {temp}°C\n"
                f"Ощущается как: {feels}°C\n"
                f"Влажность: {humidity}%"
            )
        else:
            await update.message.reply_text("Не удалось получить данные о погоде.")
    else:
        await update.message.reply_text("Пока поддерживаются только: Москва, Московская область, Подольск, Луганск.")
    return ConversationHandler.END

# КАЛОРИИ
async def get_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_data[update.effective_chat.id] = {"height": float(update.message.text)}
        await update.message.reply_text("Теперь введите свой вес в кг:")
        return WEIGHT
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число, например 175.")
        return HEIGHT

async def get_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_data[update.effective_chat.id]["weight"] = float(update.message.text)
        await update.message.reply_text("Введите свой возраст:")
        return AGE
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число, например 70.")
        return WEIGHT

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_data[update.effective_chat.id]["age"] = float(update.message.text)
        keyboard = [["Мужчина", "Женщина"]]
        await update.message.reply_text(
            "Укажите ваш пол:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        )
        return GENDER
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное число (возраст).")
        return AGE

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gender = update.message.text
    if gender not in ["Мужчина", "Женщина"]:
        await update.message.reply_text("Пожалуйста, выберите пол из предложенных кнопок.")
        return GENDER

    user_data[update.effective_chat.id]["gender"] = gender
    keyboard = [["1", "2"], ["3", "4"], ["5"]]
    await update.message.reply_text(
        "Выберите уровень активности (1-5):\n"
        "1. Минимальный (1.2)\n"
        "2. Лёгкая активность (1.375)\n"
        "3. Умеренная (1.55)\n"
        "4. Высокая (1.725)\n"
        "5. Очень высокая (1.9)",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )
    return ACTIVITY

async def get_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    activity_map = {
        "1": 1.2, "2": 1.375, "3": 1.55, "4": 1.725, "5": 1.9
    }
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
        rec = f"Ваш ИМТ: {imt} (ожирение). Рекомендуемая калорийность: {round(tdee * 0.8)} — {round(tdee * 0.75)} ккал."

    await update.message.reply_text(f"{rec}\n\nСпасибо за использование бота!", reply_markup=main_menu)
    return ConversationHandler.END

async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Я не понял ваше сообщение. Пожалуйста, выберите действие из меню.",
        reply_markup=main_menu
    )

if __name__ == "__main__":
    load_dotenv()
    TOKEN = os.getenv("TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, menu_choice)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_height)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weight)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)],
            ACTIVITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_activity)],
            WEATHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weather)],
        },
        fallbacks=[]
    )

    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))
    print("Бот запущен...")
    app.run_polling()