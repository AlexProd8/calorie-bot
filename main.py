from telegram import Update, ReplyKeyboardMarkup from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters import os

Состояния диалога

HEIGHT, WEIGHT, AGE, GENDER, ACTIVITY = range(5)

Временное хранилище данных пользователя

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text("Привет! Я помогу рассчитать твою дневную норму калорий.\nВведите свой рост в сантиметрах:") return HEIGHT

async def get_height(update: Update, context: ContextTypes.DEFAULT_TYPE): user_data[update.effective_chat.id] = {"height": float(update.message.text)} await update.message.reply_text("Теперь введите свой вес в килограммах:") return WEIGHT

async def get_weight(update: Update, context: ContextTypes.DEFAULT_TYPE): user_data[update.effective_chat.id]["weight"] = float(update.message.text) await update.message.reply_text("Введите свой возраст:") return AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE): user_data[update.effective_chat.id]["age"] = float(update.message.text) reply_keyboard = [["Мужчина", "Женщина"]] await update.message.reply_text( "Укажите ваш пол:", reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True) ) return GENDER

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE): user_data[update.effective_chat.id]["gender"] = update.message.text reply_keyboard = [["1", "2"], ["3", "4"], ["5"]] await update.message.reply_text( "Выберите уровень активности:\n" "1. Минимальный (1.2)\n" "2. Лёгкая активность (1.375)\n" "3. Умеренная активность (1.55)\n" "4. Высокая активность (1.725)\n" "5. Очень высокая (1.9)", reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True) ) return ACTIVITY

async def get_activity(update: Update, context: ContextTypes.DEFAULT_TYPE): chat_id = update.effective_chat.id activity_levels = {"1": 1.2, "2": 1.375, "3": 1.55, "4": 1.725, "5": 1.9} activity = activity_levels.get(update.message.text, 1.2)

data = user_data[chat_id]
height = data["height"]
weight = data["weight"]
age = data["age"]
gender = data["gender"]
height_m = height / 100

imt = round(weight / (height_m ** 2), 2)
bmr = round((10 * weight) + (6.25 * height) - (5 * age) + (5 if gender == "Мужчина" else -161))
tdee = round(bmr * activity)

if imt < 18.5:
    rec = f"ИМТ: {imt} (ниже нормы). Рекомендуемая калорийность: {round(tdee * 1.15)} ккал в день."
elif 18.5 <= imt <= 24.9:
    rec = f"ИМТ: {imt} (норма). Для поддержания формы: {tdee} ккал в день."
elif 25 <= imt <= 29.9:
    rec = f"ИМТ: {imt} (избыточный вес). Рекомендуемая калорийность: {round(tdee * 0.85)} ккал в день."
else:
    rec = f"ИМТ: {imt} (ожирение). Рекомендуемая калорийность: {round(tdee * 0.8)} ккал, или {round(tdee * 0.75)} ккал для усиленного похудения."

await update.message.reply_text(f"Готово!\n{rec}\n\nСпасибо за использование бота!")
return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text("Диалог отменён. Введите /start чтобы начать заново.") return ConversationHandler.END

if name == 'main': import asyncio from dotenv import load_dotenv

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
print("Бот запущен...")
app.run_polling()
