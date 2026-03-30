import os
import threading
from flask import Flask, jsonify
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

# HTML Dashboard content (embedded for reliability on serverless)
DASHBOARD_HTML = """<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🤖 Dashboard البوت</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea, #764ba2);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }
        .header {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .status-bar {
            display: flex;
            justify-content: space-around;
            padding: 20px;
            background: #f5f5f5;
            border-bottom: 2px solid #ddd;
        }
        .status-value { font-size: 1.5em; font-weight: bold; color: #667eea; }
        .content { padding: 30px; }
        .section { margin-bottom: 30px; }
        .section-title {
            font-size: 1.3em;
            font-weight: bold;
            margin-bottom: 15px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .button-group {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        button {
            padding: 12px 24px;
            font-size: 1em;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
        }
        .btn-start { background: #4CAF50; color: white; }
        .btn-stop { background: #f44336; color: white; }
        .btn-restart { background: #2196F3; color: white; }
        .btn-clear { background: #FF9800; color: white; }
        .console {
            background: #1e1e1e;
            color: #00ff00;
            padding: 15px;
            border-radius: 5px;
            font-family: monospace;
            max-height: 400px;
            overflow-y: auto;
            line-height: 1.5;
        }
        .console-line { margin: 2px 0; }
        .status-indicator {
            width: 15px;
            height: 15px;
            border-radius: 50%;
            display: inline-block;
            margin-left: 5px;
        }
        .running { background: #4CAF50; animation: pulse 1s infinite; }
        .stopped { background: #f44336; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Dashboard البوت</h1>
            <p>إدارة البوت بسهولة</p>
        </div>
        <div class="status-bar">
            <div style="text-align: center;">
                الحالة: <span class="status-value"><span class="status-indicator stopped" id="status-ind"></span><span id="status-text">متوقف</span></span>
            </div>
            <div style="text-align: center;">
                الرسائل: <span class="status-value" id="msg-count">0</span>
            </div>
            <div style="text-align: center;">
                البدء: <span class="status-value" id="start-time">--:--:--</span>
            </div>
        </div>
        <div class="content">
            <div class="section">
                <div class="section-title">🎮 التحكم بالبوت</div>
                <div class="button-group">
                    <button class="btn-start" onclick="startBot()">▶️ ابدأ البوت</button>
                    <button class="btn-stop" onclick="stopBot()">⏹️ أوقف البوت</button>
                    <button class="btn-restart" onclick="restartBot()">🔄 أعدا التشغيل</button>
                    <button class="btn-clear" onclick="clearLogs()">🗑️ امسح السجل</button>
                </div>
            </div>
            <div class="section">
                <div class="section-title">📝 Live Console</div>
                <div class="console" id="console">
                    <div class="console-line">🚀 جاري التحميل...</div>
                </div>
            </div>
        </div>
    </div>
    <script>
        setInterval(updateDash, 1000);
        
        function updateDash() {
            fetch('/api/status')
                .then(r => r.json())
                .then(d => {
                    document.getElementById('status-ind').className = d.running ? 'status-indicator running' : 'status-indicator stopped';
                    document.getElementById('status-text').textContent = d.running ? '🟢 يعمل' : '🔴 متوقف';
                    document.getElementById('msg-count').textContent = d.messages_count;
                    document.getElementById('start-time').textContent = d.started_at || '--:--:--';
                    document.getElementById('console').innerHTML = d.logs.map(l => '<div class="console-line">' + l + '</div>').join('');
                    document.getElementById('console').scrollTop = 999999;
                }).catch(e => console.log('Error:', e));
        }
        
        function startBot() { fetch('/api/start', {method: 'POST'}); }
        function stopBot() { fetch('/api/stop', {method: 'POST'}); }
        function restartBot() { fetch('/api/restart', {method: 'POST'}); }
        function clearLogs() { fetch('/api/clear-logs', {method: 'POST'}); }
        
        updateDash();
    </script>
</body>
</html>"""

@app.route('/', methods=['GET'])
def dashboard():
    """Serve dashboard HTML"""
    return DASHBOARD_HTML, 200, {'Content-Type': 'text/html; charset=utf-8'}

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
