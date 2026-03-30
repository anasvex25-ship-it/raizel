import os
from flask import Flask, request
import telebot

# Simple config
TOKEN = os.getenv("TELEGRAM_TOKEN", "7505333614:AAGAdECKNcmwnLf9iixeYYm8c6NmeQsv8Og")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

print(f"🤖 Bot started with TOKEN: {TOKEN[:20]}...")

# ============= HANDLERS =============

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Simple start handler"""
    bot.reply_to(message, "🤖 مرحباً! البوت يعمل ✅\n\nاختر من الخيارات:")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    """Echo all other messages"""
    bot.reply_to(message, f"استقبلت: {message.text}")

# ============= ENDPOINTS =============

@app.route('/', methods=['GET'])
def home():
    """Health check"""
    return {"status": "ok", "message": "Bot is running"}, 200

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    """Telegram webhook"""
    try:
        json_data = request.get_json()
        update = telebot.types.Update.de_json(json_data)
        bot.process_new_updates([update])
        return "ok", 200
    except Exception as e:
        print(f"Error: {e}")
        return "error", 500

# ============= RUN =============
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
