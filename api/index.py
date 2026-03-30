import os
import threading
from flask import Flask, send_file, jsonify
import telebot
from datetime import datetime

# ============= CONFIG =============
TOKEN = os.getenv("TELEGRAM_TOKEN", "7505333614:AAGAdECKNcmwnLf9iixeYYm8c6NmeQsv8Og")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Bot state
bot_state = {
    "running": False,
    "logs": [],
    "started_at": None,
    "messages_count": 0
}

# ============= LOGGING =============
def log_message(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {msg}"
    bot_state["logs"].append(log_entry)
    print(log_entry)
    if len(bot_state["logs"]) > 50:
        bot_state["logs"] = bot_state["logs"][-50:]

# ============= BOT HANDLERS =============
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot_state["messages_count"] += 1
    log_message(f"✅ /start from {message.from_user.id}")
    bot.reply_to(message, "🤖 مرحباً! البوت يعمل ✅")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot_state["messages_count"] += 1
    log_message(f"📨 Message: {message.text[:50]}")
    bot.reply_to(message, f"✅ استقبلت: {message.text}")

# ============= POLLING =============
def start_bot_polling():
    if bot_state["running"]:
        return
    bot_state["running"] = True
    bot_state["started_at"] = datetime.now().strftime("%H:%M:%S")
    bot_state["messages_count"] = 0
    log_message("🚀 Bot started...")
    try:
        bot.infinity_polling(non_stop=True, timeout=30)
    except Exception as e:
        log_message(f"❌ Error: {e}")
        bot_state["running"] = False

# ============= API ENDPOINTS =============

@app.route('/', methods=['GET'])
def dashboard():
    """Serve dashboard HTML"""
    try:
        dashboard_path = os.path.join(os.path.dirname(__file__), 'dashboard.html')
        return send_file(dashboard_path, mimetype='text/html')
    except:
        return "<h1>Dashboard</h1><p>Loading...</p>"

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify(bot_state)

@app.route('/api/start', methods=['POST'])
def api_start():
    if not bot_state["running"]:
        thread = threading.Thread(target=start_bot_polling, daemon=True)
        thread.start()
    return jsonify({"ok": True})

@app.route('/api/stop', methods=['POST'])
def api_stop():
    bot_state["running"] = False
    log_message("⏹️ Bot stopped")
    return jsonify({"ok": True})

@app.route('/api/restart', methods=['POST'])
def api_restart():
    bot_state["running"] = False
    log_message("🔄 Restarting...")
    thread = threading.Thread(target=start_bot_polling, daemon=True)
    thread.start()
    return jsonify({"ok": True})

@app.route('/api/clear-logs', methods=['POST'])
def api_clear():
    bot_state["logs"] = []
    return jsonify({"ok": True})

if __name__ == '__main__':
    log_message("🌟 Server started!")
    app.run(host='0.0.0.0', port=5000, debug=False)

@app.route('/api/restart', methods=['POST'])
def api_restart():
    bot_state["running"] = False
    log_message("🔄 Restarting...")
    thread = threading.Thread(target=start_bot_polling, daemon=True)
    thread.start()
    return jsonify({"ok": True})

@app.route('/api/clear-logs', methods=['POST'])
def api_clear():
    bot_state["logs"] = []
    return jsonify({"ok": True})

if __name__ == '__main__':
    log_message("🌟 Server started!")
    app.run(host='0.0.0.0', port=5000, debug=False)
