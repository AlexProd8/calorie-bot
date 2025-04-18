import logging
import os
import tempfile
import traceback
from io import BytesIO
from typing import Dict, Optional
from cachetools import TTLCache
import requests
import mimetypes
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

# ----------------- Конфигурация -----------------
TOKEN = os.environ.get("TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")
PIVOT_CURRENCY = "USD"  # Опорная валюта для конвертера
MAX_VIDEO_SIZE_MB = 50  # Лимит размера скачиваемого видео

# Кэш для курсов валют (5 минут)
CACHE = TTLCache(maxsize=100, ttl=300)

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ----------------- Состояния -----------------
(MENU, HEIGHT, WEIGHT, AGE, GENDER, ACTIVITY, VIDEO, 
 CURRENCY_FROM, CURRENCY_TO, CURRENCY_AMOUNT, FEEDBACK) = range(11)

# ----------------- Константы -----------------
BACK_TO_MENU = "В меню"
ALLOWED_DOMAINS = ["tiktok.com", "instagram.com"]
CURRENCY_API_URL = "https://open.er-api.com/v6/latest/"

# Список валют с поддержкой автообновления
DEFAULT_CURRENCIES = ["RUB", "UZS", "BYN", "USD", "EUR", "CHF", "TJS", "KGS", "KZT", "UAH"]

# ----------------- Клавиатуры -----------------
def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню с основными опциями."""
    buttons = [
        ["Рассчитать калории"],
        ["Видео по вашей ссылке"],
        ["Конвертация валют"],
        ["Информация", "Оставить отзыв"]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def build_currency_keyboard(currencies: list) -> ReplyKeyboardMarkup:
    """Динамическая клавиатура для выбора валют."""
    rows = [currencies[i:i+3] for i in range(0, len(currencies), 3)]
    rows.append([BACK_TO_MENU])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

# ----------------- Вспомогательные функции -----------------
async def check_back_to_menu(text: str, update: Update) -> bool:
    """Проверяет, хочет ли пользователь вернуться в меню."""
    if text.strip().lower() == BACK_TO_MENU.lower():
        await update.message.reply_text(
            "Вы вернулись в главное меню.",
            reply_markup=main_menu_keyboard()
        )
        return True
    return False

async def get_currency_rates() -> Optional[Dict[str, float]]:
    """Получает курсы валют с кэшированием."""
    try:
        if "rates" in CACHE:
            return CACHE["rates"]
        
        response = requests.get(f"{CURRENCY_API_URL}{PIVOT_CURRENCY}", timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("result") != "success":
            raise ValueError("Invalid API response")
        
        CACHE["rates"] = data["rates"]
        return data["rates"]
    except Exception as e:
        logger.error(f"Currency API error: {e}")
        return None

async def download_media(url: str, referer: str) -> Optional[BytesIO]:
    """Скачивает медиа-контент с обработкой ошибок."""
    ydl_opts = {
        'quiet': True,
        'noplaylist': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0',
            'Referer': referer
        },
        'extract_flat': True,
        'max_filesize': MAX_VIDEO_SIZE_MB * 1024 * 1024
    }
    
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            ydl_opts['outtmpl'] = os.path.join(tmp_dir, '%(id)s.%(ext)s')
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                with open(filename, 'rb') as file:
                    return BytesIO(file.read())
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return None

# ----------------- Основные обработчики -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /start."""
    await update.message.reply_text(
        "Привет! Выберите действие:",
        reply_markup=main_menu_keyboard()
    )
    return MENU

async def handle_video_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик запросов на скачивание видео."""
    url = update.message.text.strip()
    
    if await check_back_to_menu(url, update):
        return MENU
        
    if not any(domain in url for domain in ALLOWED_DOMAINS):
        await update.message.reply_text("Поддерживаются только TikTok и Instagram.")
        return VIDEO
        
    await update.message.reply_text("Скачиваю...")
    referer = "https://www.instagram.com/" if "instagram" in url else "https://www.tiktok.com/"
    
    try:
        media = await download_media(url, referer)
        if media:
            media.name = "video.mp4"
            await update.message.reply_video(video=media)
        else:
            await update.message.reply_text("Не удалось скачать медиа.")
    except Exception as e:
        logger.error(f"Video error: {e}")
        await update.message.reply_text("Ошибка при обработке.")

    return VIDEO

async def handle_currency_conversion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик конвертации валют."""
    # ... (реализация аналогична вашему коду, но с использованием get_currency_rates())
    pass

# ----------------- Запуск бота -----------------
async def post_init(application):
    """Установка команд бота после инициализации."""
    commands = [
        BotCommand("start", "Начать работу"),
        BotCommand("cancel", "Отменить текущее действие")
    ]
    await application.bot.set_my_commands(commands)

def main():
    """Точка входа."""
    app = ApplicationBuilder() \
        .token(TOKEN) \
        .post_init(post_init) \
        .build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu)],
            VIDEO: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video_request)],
            # ... другие состояния
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()