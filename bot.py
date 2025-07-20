import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    ConversationHandler,
    filters,
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ========== Налаштування ==========
TOKEN = "7744082797:AAFrLzG_k1tyXsK0KbJAXB0keTNBP7OBzWE"
TABLE_NAME = "order"
SHEET_NAME = "Аркуш1"
CREDS_FILE = "creds.json"

# ========== Авторизація до Google Sheets ==========
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open(TABLE_NAME).worksheet(SHEET_NAME)

# ========== Стани ==========
TTN, SALE_PRICE, SUPPLIER_PRICE, COMMISSION = range(4)

# ========== Логування ==========
logging.basicConfig(level=logging.INFO)

# ========== Меню з кнопкою ==========
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Розпочати розрахунок"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("👋 Вітаю! Оберіть дію:", reply_markup=reply_markup)

# ========== Початок розрахунку ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введіть номер ТТН:")
    return TTN

async def get_ttn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("📥 Отримано ТТН:", update.message.text)  # Debug
    context.user_data["ttn"] = update.message.text
    await update.message.reply_text("Введіть ціну продажу:")
    return SALE_PRICE

async def get_sale_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["sale_price"] = float(update.message.text)
    await update.message.reply_text("Введіть ціну у постачальника:")
    return SUPPLIER_PRICE

async def get_supplier_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["supplier_price"] = float(update.message.text)
    await update.message.reply_text("Введіть комісію (грн):")
    return COMMISSION

async def get_commission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        commission = float(update.message.text)
        ttn = context.user_data["ttn"]
        sale = context.user_data["sale_price"]
        supplier = context.user_data["supplier_price"]

        profit = sale - supplier - commission
        part65 = round(profit * 0.65, 2)
        part35 = round(profit * 0.35, 2)
        date = datetime.now().strftime("%d.%m.%Y %H:%M")

        # Запис у Google таблицю
        sheet.append_row([ttn, sale, supplier, commission, profit, part65, part35, date])

        await update.message.reply_text(
            f"✅ Чистий прибуток: {profit} грн\n"
            f"🔹 65% = {part65} грн\n"
            f"🔹 35% = {part35} грн\n"
            f"📋 Дані збережено!"
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Помилка: {e}")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операцію скасовано.")
    return ConversationHandler.END

# ========== Запуск ==========
app = ApplicationBuilder().token(TOKEN).build()

# Меню з кнопкою
app.add_handler(CommandHandler("start", menu))

# Основна розмова
conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^Розпочати розрахунок$"), start)],
    states={
        TTN: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_ttn)],
        SALE_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_sale_price)],
        SUPPLIER_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_supplier_price)],
        COMMISSION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_commission)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

app.add_handler(conv_handler)

print("✅ Бот запущено!")
app.run_polling()
