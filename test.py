import threading
import time
import telebot
from telebot import apihelper, types
import sqlite3
from datetime import datetime


def safe_send_message(chat_id, text, **kwargs):
    """Send a message while safely ignoring users who blocked the bot."""
    try:
        return bot.send_message(chat_id, text, **kwargs)
    except apihelper.ApiTelegramException as e:
        # Ignore users who blocked the bot (Telegram returns 403 Forbidden)
        desc = ""
        try:
            desc = (e.result_json or {}).get("description", "").lower()
        except Exception:
            pass
        if "bot was blocked" in str(e).lower() or "forbidden" in desc:
            return None
        raise

# ---------------- CONFIG ----------------
TOKEN = "7505333614:AAGAdECKNcmwnLf9iixeYYm8c6NmeQsv8Og"
ADMIN_GROUP_ID = -1002177227451
ADMIN_TOPIC_ID = 460326
PUBLIC_GROUP_ID = -1001885837165
LOG_TOPIC_ID = 370829        # ضع هنا ID التوبيك الخاص بالسجل في مجموعة الإدارة
BOSS_GROUP_ID = -1001885837165  # ضع هنا ID مجموعة الـ Boss

OWNERS = [8083360929, 1486469878]
bot = telebot.TeleBot(TOKEN)
user_forms = {}

# Wrap answer_callback_query to ignore stale callback query errors (query too old / invalid query_id)
_orig_answer_callback = bot.answer_callback_query

def safe_answer_callback(call_id, text=None, show_alert=False, url=None, cache_time=None):
    try:
        return _orig_answer_callback(call_id, text=text, show_alert=show_alert, url=url, cache_time=cache_time)
    except apihelper.ApiTelegramException as e:
        err = str(e).lower()
        if "query is too old" in err or "query id is invalid" in err:
            return None
        raise

bot.answer_callback_query = safe_answer_callback

# ---------------- DATABASE ----------------
conn = sqlite3.connect('bot_database.db', check_same_thread=False)
cur = conn.cursor()
db_lock = threading.Lock()

cur.execute('CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)')
cur.execute('CREATE TABLE IF NOT EXISTS blocked (user_id INTEGER PRIMARY KEY)')
cur.execute('''
CREATE TABLE IF NOT EXISTS requests(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT,
    age TEXT,
    country TEXT,
    time TEXT,
    benefit TEXT,
    prev TEXT,
    mic TEXT,
    date TEXT,
    status TEXT,
    decision_date TEXT,
    admin_name TEXT,
    message_id INTEGER,
    request_text TEXT
)
''')
cur.execute('CREATE TABLE IF NOT EXISTS announcement(id INTEGER PRIMARY KEY,message_id INTEGER)')
cur.execute('CREATE TABLE IF NOT EXISTS spam_limit(user_id INTEGER, date TEXT)')
conn.commit()


with db_lock:
    cur.execute('''
    CREATE TABLE IF NOT EXISTS temp_punishments(
        admin_id INTEGER PRIMARY KEY,
        target_id INTEGER,
        target_name TEXT,
        target_username TEXT,
        action_type TEXT,
        duration TEXT,
        reason TEXT
    )
    ''')
    conn.commit()

# ---------------- STATUS ----------------
def get_status(uid):
    if uid in OWNERS:
        return "owner"

    with db_lock:
        cur.execute('SELECT 1 FROM admins WHERE user_id=?', (uid,))
        if cur.fetchone():
            return "admin"
        cur.execute('SELECT 1 FROM blocked WHERE user_id=?', (uid,))
        if cur.fetchone():
            return "blocked"

    return "user"

# ---------------- SPAM CHECK ----------------
def get_today_request_count(uid):
    today = datetime.now().strftime("%Y-%m-%d")
    with db_lock:
        cur.execute("SELECT COUNT(*) FROM spam_limit WHERE user_id=? AND date=?", (uid, today))
        return cur.fetchone()[0]


def check_spam(uid, max_per_day=2):
    today = datetime.now().strftime("%Y-%m-%d")
    with db_lock:
        cur.execute("DELETE FROM spam_limit WHERE date<?", (today,))
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM spam_limit WHERE user_id=? AND date=?", (uid, today))
        count = cur.fetchone()[0]
        if count >= max_per_day:
            return False
        cur.execute("INSERT INTO spam_limit(user_id,date) VALUES(?,?)", (uid, today))
        conn.commit()
    return True


def decrement_spam(uid, amount=1):
    """Reduce the spam counter (e.g., when user cancels a pending request)."""
    today = datetime.now().strftime("%Y-%m-%d")
    with db_lock:
        for _ in range(amount):
            cur.execute("DELETE FROM spam_limit WHERE user_id=? AND date=? LIMIT 1", (uid, today))
        conn.commit()

# ---------------- KEYBOARDS ----------------
def get_request_keyboard(uid, request_id):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("👤 البروفايل", url=f"tg://user?id={uid}"))
    kb.add(
        types.InlineKeyboardButton("✅ قبول", callback_data=f"pre_acc_{request_id}"),
        types.InlineKeyboardButton("❌ رفض", callback_data=f"pre_rej_{request_id}")
    )
    return kb

def get_admin_panel_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("🚫 حظر", callback_data="ask_block"),
        types.InlineKeyboardButton("✅ فك حظر", callback_data="ask_unblock"),
        types.InlineKeyboardButton("📋 عرض المحظورين", callback_data="view_blocked"),
        types.InlineKeyboardButton("📋 الطلبات المعلقة", callback_data="pending_requests")
    )
    kb.add(types.InlineKeyboardButton("📢 نشر إعلان", callback_data="send_announcement"))
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_home"))
    return kb

def get_owner_panel_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("➕ إضافة مسؤول (بالآيدي)", callback_data="ask_add_admin"),
        types.InlineKeyboardButton("➖ حذف مسؤول (بالآيدي)", callback_data="ask_remove_admin")
    )
    kb.add(types.InlineKeyboardButton("📋 عرض المسؤولين", callback_data="view_admins"))
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_home"))
    return kb

def get_announcement_manage_keyboard(message_id, pinned=False):
    kb = types.InlineKeyboardMarkup()
    if pinned:
        kb.add(types.InlineKeyboardButton("❌ إلغاء التثبيت", callback_data=f"unpin_{message_id}"))
    else:
        kb.add(types.InlineKeyboardButton("📌 تثبيت", callback_data=f"pin_{message_id}"))
    kb.add(types.InlineKeyboardButton("🗑 حذف الإعلان", callback_data=f"del_{message_id}"))
    return kb


def get_cancel_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⛔ إلغاء", callback_data="cancel_apply"))
    return kb

# --- helper functions for application questions ---
COUNTRY_OPTIONS = {
    "eg": "مصر",
    "sa": "السعودية",
    "ae": "الإمارات",
    "tn": "تونس",
    "ma": "المغرب",
}

TIME_OPTIONS = {
    "lt1": "أقل من ساعة",
    "1_3": "1-3 ساعات",
    "3_6": "3-6 ساعات",
    "gt6": "أكثر من 6 ساعات",
    "var": "وقت متغير",
}


def send_country_question(chat_id):
    kb = types.InlineKeyboardMarkup(row_width=2)
    for key, label in COUNTRY_OPTIONS.items():
        kb.add(types.InlineKeyboardButton(label, callback_data=f"country_{key}"))
    kb.add(types.InlineKeyboardButton("🌍 دولة أخرى", callback_data="country_other"))
    kb.add(types.InlineKeyboardButton("⛔ إلغاء", callback_data="cancel_apply"))
    bot.send_message(chat_id, "🌍 من أي بلد أنت؟", reply_markup=kb)


def send_time_question(chat_id):
    kb = types.InlineKeyboardMarkup(row_width=1)
    for key, label in TIME_OPTIONS.items():
        kb.add(types.InlineKeyboardButton(label, callback_data=f"time_{key}"))
    kb.add(types.InlineKeyboardButton("⛔ إلغاء", callback_data="cancel_apply"))
    bot.send_message(chat_id, "⏱ ما هي ساعات تفاعلك اليومية؟", reply_markup=kb)


def send_prev_question(chat_id):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("نعم", callback_data="adm_yes"),
        types.InlineKeyboardButton("لا", callback_data="adm_no")
    )
    kb.add(types.InlineKeyboardButton("⛔ إلغاء", callback_data="cancel_apply"))
    bot.send_message(chat_id, "🛡 هل سبق لك العمل كإداري بمجموعة أخرى؟", reply_markup=kb)


def send_mic_question(chat_id):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("نعم", callback_data="mic_yes"),
        types.InlineKeyboardButton("لا", callback_data="mic_no")
    )
    kb.add(types.InlineKeyboardButton("⛔ إلغاء", callback_data="cancel_apply"))
    bot.send_message(chat_id, "🎤 هل تستطيع التحدث في المايك؟", reply_markup=kb)


@bot.callback_query_handler(func=lambda call: call.data.startswith("country_"))
def handle_country_selection(call):
    uid = call.from_user.id
    data = call.data.split("_", 1)[1]

    if data == "other":
        bot.edit_message_text("🌍 اكتب اسم بلدك:", call.message.chat.id, call.message.message_id)
        msg = bot.send_message(call.message.chat.id, "🌍 اكتب اسم بلدك:", reply_markup=get_cancel_keyboard())
        bot.register_next_step_handler(msg, step_country_other)
        bot.answer_callback_query(call.id)
        return

    country = COUNTRY_OPTIONS.get(data)
    if not country:
        bot.answer_callback_query(call.id, "❌ اختيار غير صالح", show_alert=True)
        return

    user_forms.setdefault(uid, {})["country"] = country
    bot.edit_message_text(f"✅ بلدك: {country}", call.message.chat.id, call.message.message_id)
    send_time_question(call.message.chat.id)
    bot.answer_callback_query(call.id)


def step_country_other(m):
    if m.text.strip().lower() in ["إلغاء", "cancel", "/cancel"]:
        clear_application_and_send_home(m.from_user.id, m.chat.id)
        return

    user_forms[m.from_user.id]["country"] = m.text.strip()
    send_time_question(m.chat.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("time_"))
def handle_time_selection(call):
    uid = call.from_user.id
    data = call.data.split("_", 1)[1]

    if data == "other":
        bot.edit_message_text("⏱ اكتب عدد ساعات تفاعلك اليومية:", call.message.chat.id, call.message.message_id)
        msg = bot.send_message(call.message.chat.id, "⏱ اكتب عدد ساعات تفاعلك اليومية:", reply_markup=get_cancel_keyboard())
        bot.register_next_step_handler(msg, step_time_other)
        bot.answer_callback_query(call.id)
        return

    time_text = TIME_OPTIONS.get(data)
    if not time_text:
        bot.answer_callback_query(call.id, "❌ اختيار غير صالح", show_alert=True)
        return

    user_forms.setdefault(uid, {})["time"] = time_text
    bot.edit_message_text(f"✅ ساعات التفاعل: {time_text}", call.message.chat.id, call.message.message_id)
    msg = bot.send_message(call.message.chat.id, "💡 لماذا تريد الانضمام وما فائدتك؟", reply_markup=get_cancel_keyboard())
    bot.register_next_step_handler(msg, step6)
    bot.answer_callback_query(call.id)


def step_time_other(m):
    if m.text.strip().lower() in ["إلغاء", "cancel", "/cancel"]:
        clear_application_and_send_home(m.from_user.id, m.chat.id)
        return

    user_forms[m.from_user.id]["time"] = m.text.strip()
    msg = bot.send_message(m.chat.id, "💡 لماذا تريد الانضمام وما فائدتك؟", reply_markup=get_cancel_keyboard())
    bot.register_next_step_handler(msg, step6)


# ---------------- USER APPLICATION ----------------
def send_main_menu(chat_id, user_id):
    status = get_status(user_id)
    if status == "blocked":
        return

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📝 تقديم  انضمام", callback_data="start_apply"))

    if status == "user":
        used = get_today_request_count(user_id)
        remaining = max(0, 2 - used)
        kb.add(types.InlineKeyboardButton(f"📌 المتبقي اليوم: {remaining}", callback_data="noop"))
        kb.add(types.InlineKeyboardButton("🗂️ سجل طلباتي", callback_data="my_history"))
        kb.add(types.InlineKeyboardButton("🗑️ إلغاء طلب", callback_data="cancel_request"))

    if status in ["admin", "owner"]:
        kb.add(types.InlineKeyboardButton("⚙️ لوحة الإدارة", callback_data="admin_panel"))
    if status == "owner":
        kb.add(types.InlineKeyboardButton("👑 لوحة الأونر", callback_data="owner_panel"))

    safe_send_message(chat_id, f"أهلاً بك في نظام الإدارة.\nرتبتك: {status.upper()}", reply_markup=kb)


def clear_application_and_send_home(user_id, chat_id):
    # Keep partial info so user can resume later
    send_main_menu(chat_id, user_id)


def discard_application(user_id, chat_id):
    user_forms.pop(user_id, None)
    send_main_menu(chat_id, user_id)


def build_application_summary(uid):
    d = user_forms.get(uid, {})
    return (
        f"📥 *ملخص طلبك:*\n"
        f"• الاسم: {d.get('name', 'غير محدد')}\n"
        f"• العمر: {d.get('age', 'غير محدد')}\n"
        f"• البلد: {d.get('country', 'غير محدد')}\n"
        f"• ساعات التفاعل: {d.get('time', 'غير محدد')}\n"
        f"• الفائدة: {d.get('benefit', 'غير محدد')}\n"
        f"• إداري سابق: {d.get('prev', 'غير محدد')}\n"
        f"• مايك: {d.get('mic', 'غير محدد')}\n"
    )


@bot.callback_query_handler(func=lambda call: call.data=="start_apply")
def step1(call):
    status = get_status(call.from_user.id)
    if status == "blocked":
        bot.answer_callback_query(call.id,"🚫 أنت محظور من استخدام البوت", show_alert=True)
        return

    # Spam check only for normal users (admins/owners غير مقيدين)
    if status == "user" and not check_spam(call.from_user.id):
        bot.answer_callback_query(call.id,"⚠️ لقد وصلت الحد الأقصى للطلبات اليوم (2)", show_alert=True)
        return

    # إذا كان هناك نموذج جاري (ليس مكتملاً) - نعطي خيار استكمال أو البدء من جديد
    if call.from_user.id in user_forms and user_forms[call.from_user.id]:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("▶️ استكمال الطلب", callback_data="resume_apply"))
        kb.add(types.InlineKeyboardButton("🔄 إعادة بداية الطلب", callback_data="restart_apply"))
        bot.edit_message_text(
            "لديك طلب غير مكتمل، اختر ما تريد:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb
        )
        return

    user_forms[call.from_user.id] = {}
    bot.edit_message_text(
        "👤 أرسل اسمك الثلاثي:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=get_cancel_keyboard()
    )
    bot.register_next_step_handler(call.message, step2)

def step2(m):
    if m.text.strip().lower() in ["إلغاء", "cancel", "/cancel"]:
        clear_application_and_send_home(m.from_user.id, m.chat.id)
        return

    user_forms[m.from_user.id]["name"] = m.text.strip()
    kb = get_cancel_keyboard()
    bot.send_message(m.chat.id, "🔞 كم عمرك؟ (بالأرقام)", reply_markup=kb)
    bot.register_next_step_handler(m, step3)

def step3(m):
    if m.text.strip().lower() in ["إلغاء", "cancel", "/cancel"]:
        clear_application_and_send_home(m.from_user.id, m.chat.id)
        return

    try:
        age = int(m.text.strip())
        if age <= 10:
            raise ValueError
    except ValueError:
        kb = get_cancel_keyboard()
        bot.send_message(m.chat.id, "⚠️ الرجاء إدخال عدد صحيح (أكبر من 10).", reply_markup=kb)
        bot.register_next_step_handler(m, step3)
        return

    user_forms[m.from_user.id]["age"] = str(age)
    send_country_question(m.chat.id)

def step6(m):
    if m.text.strip().lower() in ["إلغاء", "cancel", "/cancel"]:
        clear_application_and_send_home(m.from_user.id, m.chat.id)
        return

    user_forms[m.from_user.id]["benefit"] = m.text.strip()
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("نعم", callback_data="adm_yes"),
        types.InlineKeyboardButton("لا", callback_data="adm_no")
    )
    bot.send_message(m.chat.id, "🛡 هل سبق لك العمل كإداري بمجموعة أخرى؟", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data in ["adm_yes","adm_no"])
def step7(call):
    user_forms[call.from_user.id]["prev"] = "نعم" if call.data=="adm_yes" else "لا"
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("نعم", callback_data="mic_yes"),
        types.InlineKeyboardButton("لا", callback_data="mic_no")
    )
    kb.add(types.InlineKeyboardButton("⛔ إلغاء", callback_data="cancel_apply"))
    bot.edit_message_text("🎤 هل تستطيع التحدث في المايك؟", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data in ["mic_yes","mic_no"])
def final_submit(call):
    uid = call.from_user.id
    user_forms[uid]["mic"] = "نعم" if call.data == "mic_yes" else "لا"

    summary = build_application_summary(uid)

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ تأكيد الإرسال", callback_data="confirm_submit"))
    kb.add(types.InlineKeyboardButton("⛔ إلغاء", callback_data="cancel_apply"))

    bot.edit_message_text(summary, call.message.chat.id, call.message.message_id, reply_markup=kb, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_apply")
def cancel_apply(call):
    # يُبقي البيانات حتى يتمكن المستخدم من استئناف الطلب لاحقاً
    bot.answer_callback_query(call.id, "✅ تم إيقاف التقديم مؤقتاً")
    clear_application_and_send_home(call.from_user.id, call.message.chat.id)


@bot.callback_query_handler(func=lambda call: call.data == "resume_apply")
def resume_apply(call):
    uid = call.from_user.id
    data = user_forms.get(uid)
    if not data:
        return bot.answer_callback_query(call.id, "لا يوجد طلب لإستكماله.")

    bot.answer_callback_query(call.id)

    # نكمل من الخطوة التالية غير المملوءة
    if "name" not in data:
        msg = bot.send_message(call.message.chat.id, "👤 أرسل اسمك الثلاثي:", reply_markup=get_cancel_keyboard())
        bot.register_next_step_handler(msg, step2)
        return
    if "age" not in data:
        msg = bot.send_message(call.message.chat.id, "🔞 كم عمرك؟ (بالأرقام)", reply_markup=get_cancel_keyboard())
        bot.register_next_step_handler(msg, step3)
        return
    if "country" not in data:
        send_country_question(call.message.chat.id)
        return
    if "time" not in data:
        send_time_question(call.message.chat.id)
        return
    if "benefit" not in data:
        msg = bot.send_message(call.message.chat.id, "💡 لماذا تريد الانضمام وما فائدتك؟", reply_markup=get_cancel_keyboard())
        bot.register_next_step_handler(msg, step6)
        return
    if "prev" not in data:
        send_prev_question(call.message.chat.id)
        return
    if "mic" not in data:
        send_mic_question(call.message.chat.id)
        return

    summary = build_application_summary(uid)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ تأكيد الإرسال", callback_data="confirm_submit"))
    kb.add(types.InlineKeyboardButton("⛔ إلغاء", callback_data="cancel_apply"))
    bot.send_message(call.message.chat.id, summary, reply_markup=kb, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda call: call.data == "restart_apply")
def restart_apply(call):
    user_forms.pop(call.from_user.id, None)
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        "👤 أرسل اسمك الثلاثي:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=get_cancel_keyboard()
    )
    bot.register_next_step_handler(call.message, step2)


@bot.callback_query_handler(func=lambda call: call.data == "confirm_submit")
def confirm_submit(call):
    uid = call.from_user.id
    
    if uid not in user_forms or not user_forms[uid]:
        bot.answer_callback_query(call.id, "⚠️ انتهت صلاحية الجلسة، اعد التقديم من جديد.", show_alert=True)
        return

    d = user_forms[uid]
    request_date = datetime.now().strftime("%d/%m/%Y")

    # 1. حفظ الطلب مبدئياً للحصول على ID
    try:
        with db_lock:
            c = conn.cursor()
            c.execute('''
                INSERT INTO requests(user_id, name, age, country, time, benefit, prev, mic, date, status)
                VALUES(?,?,?,?,?,?,?,?,?,?)
            ''', (
                uid, d.get('name'), d.get('age'), d.get('country'),
                d.get('time'), d.get('benefit'), d.get('prev'), 
                d.get('mic'), request_date, "pending"
            ))
            request_id = c.lastrowid
            conn.commit()
    except Exception as e:
        print(f"Database Error: {e}")
        bot.answer_callback_query(call.id, "❌ خطأ في قاعدة البيانات")
        return

    # 2. تجهيز النص النهائي
    request_code = f"{request_id:04d}"
    text = (
        f"📥 *طلب إداري جديد* — `#{request_code}`\n"
        f"📅 {request_date}\n\n"
        f"━━━━━━━━━━━━\n"
        f"👤 المستخدم: [{call.from_user.first_name}](tg://user?id={uid})\n"
        f"🆔 ID: `{uid}`\n\n"
        f"📋 *معلومات التقديم*\n"
        f"• الاسم: {d.get('name')}\n"
        f"• العمر: {d.get('age')}\n"
        f"• البلد: {d.get('country')}\n"
        f"• التفاعل: {d.get('time')}\n"
        f"• الفائدة: {d.get('benefit')}\n"
        f"• إداري سابق: {d.get('prev')}\n"
        f"• مايك: {d.get('mic')}\n"
        f"━━━━━━━━━━━━"
    )

    # 3. إرسال الطلب لمجموعة الإدارة مع الأزرار مباشرة
    try:
        msg = bot.send_message(
            ADMIN_GROUP_ID,
            text,
            parse_mode="Markdown",
            message_thread_id=ADMIN_TOPIC_ID,
            reply_markup=get_request_keyboard(uid, request_id) # إرسال الأزرار هنا
        )
        
        # 4. إضافة رابط الرسالة للنص وتحديث قاعدة البيانات
        group_id_clean = str(ADMIN_GROUP_ID).replace("-100", "")
        message_link = f"https://t.me/c/{group_id_clean}/{msg.message_id}"
        final_text_with_link = text + f"\n\n🔗 [رابط الطلب]({message_link})"

        with db_lock:
            c = conn.cursor()
            c.execute("UPDATE requests SET message_id=?, request_text=? WHERE id=?", 
                     (msg.message_id, final_text_with_link, request_id))
            conn.commit()

        # 5. تعديل الرسالة لإضافة الرابط (مع إعادة إرسال الأزرار لضمان بقائها)
        bot.edit_message_text(
            final_text_with_link,
            ADMIN_GROUP_ID,
            msg.message_id,
            parse_mode="Markdown",
            reply_markup=get_request_keyboard(uid, request_id) # إعادة إرسال الأزرار هنا
        )

        # 6. تنظيف الذاكرة وإبلاغ المستخدم
        user_forms.pop(uid, None)
        bot.edit_message_text("✅ تم إرسال طلبك بنجاح! سيتم الرد عليك قريباً.", call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        print(f"Telegram Error: {e}")
        bot.answer_callback_query(call.id, "❌ فشل إرسال الطلب للمشرفين", show_alert=True)


# ---------------- DECISIONS ----------------
@bot.callback_query_handler(func=lambda call: call.data.startswith(("pre_acc_","pre_rej_")))
def pre_decision(call):
    if get_status(call.from_user.id) not in ["admin","owner"]:
        return bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية", show_alert=True)
    action, request_id = call.data.split("_")[1], int(call.data.split("_")[2])

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ تأكيد القرار", callback_data=f"fix_{action}_{request_id}"),
        types.InlineKeyboardButton("🔙 إلغاء", callback_data=f"rollback_{request_id}")
    )
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=kb)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("rollback_"))
def rollback_action(call):
    request_id = int(call.data.split("_")[1])

    with db_lock:
        c = conn.cursor()
        c.execute("SELECT user_id FROM requests WHERE id=?", (request_id,))
        row = c.fetchone()
    if not row:
        return bot.answer_callback_query(call.id, "❌ الطلب غير موجود")

    uid = row[0]
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_request_keyboard(uid, request_id))
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "back_home")
def back_home(call):
    status = get_status(call.from_user.id)
    if status == "blocked":
        return bot.answer_callback_query(call.id, "🚫 أنت محظور من استخدام البوت", show_alert=True)

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📝 تقديم طلب انضمام", callback_data="start_apply"))
    if status in ["admin", "owner"]:
        kb.add(types.InlineKeyboardButton("⚙️ لوحة الإدارة", callback_data="admin_panel"))
    if status == "owner":
        kb.add(types.InlineKeyboardButton("👑 لوحة الأونر", callback_data="owner_panel"))

    bot.edit_message_text(
        f"أهلاً بك في نظام الإدارة.\nرتبتك: {status.upper()}",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("fix_"))
def finalize_decision(call):
    if get_status(call.from_user.id) not in ["admin", "owner"]:
        return bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية", show_alert=True)

    action, request_id = call.data.split("_")[1], int(call.data.split("_")[2])
    decision_date = datetime.now().strftime("%d/%m/%Y")
    result = "✅ تم قبول الطلب" if action == "acc" else "❌ تم رفض الطلب"
    status = "accepted" if action == "acc" else "rejected"

    with db_lock:
        c = conn.cursor()
        c.execute("""
        UPDATE requests 
        SET status=?, decision_date=?, admin_name=? 
        WHERE id=?
        """, (status, decision_date, call.from_user.first_name, request_id))
        conn.commit()

        c.execute("SELECT user_id, request_text, message_id FROM requests WHERE id=?", (request_id,))
        row = c.fetchone()
    if not row:
        return

    uid, old_text, msg_id = row

    new_text = old_text + f"""

━━━━━━━━━━━━
{result}

👮 بواسطة: {call.from_user.first_name}
📅 التاريخ: {decision_date}
"""

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("👤 البروفايل", url=f"tg://user?id={uid}"))

    bot.edit_message_text(
        new_text,
        ADMIN_GROUP_ID,
        msg_id,
        parse_mode="Markdown",
        reply_markup=kb
    )

    try:
        bot.send_message(uid, f"📢 نتيجة طلبك:\n{result}")
    except:
        pass

    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "noop")
def noop(call):
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "my_history")
def my_history(call):
    uid = call.from_user.id
    with db_lock:
        cur.execute(
            "SELECT id, status, message_id FROM requests WHERE user_id=? ORDER BY id DESC LIMIT 10",
            (uid,)
        )
        rows = cur.fetchall()

    if not rows:
        return bot.answer_callback_query(call.id, "📌 لا يوجد أي طلبات سابقة.")

    group_id_for_link = str(ADMIN_GROUP_ID).replace("-100", "")
    lines = []
    for request_id, status, message_id in rows:
        link = f"https://t.me/c/{group_id_for_link}/{message_id}"
        lines.append(f"• `#{request_id:04d}` - {status} - [رابط]({link})")

    text = "📜 سجل طلباتك (آخر 10):\n\n" + "\n".join(lines)
    bot.send_message(call.from_user.id, text)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_request")
def cancel_request(call):
    uid = call.from_user.id
    with db_lock:
        cur.execute(
            "SELECT id, message_id, request_text FROM requests WHERE user_id=? AND status='pending' ORDER BY id DESC LIMIT 1",
            (uid,)
        )
        row = cur.fetchone()
        if not row:
            return bot.answer_callback_query(call.id, "🚫 لا يوجد طلب معلق لإلغائه.")

        request_id, message_id, old_text = row
        decision_date = datetime.now().strftime("%d/%m/%Y")
        cancel_note = f"\n\n━━━━━━━━━━━━\n❌ تم إلغاء الطلب من المستخدم\n📅 التاريخ: {decision_date}\n"
        new_text = old_text + cancel_note

        cur.execute(
            "UPDATE requests SET status=?, decision_date=?, admin_name=?, request_text=? WHERE id=?",
            ("cancelled", decision_date, call.from_user.first_name, new_text, request_id)
        )
        conn.commit()

    # Decrement spam counter so user can re-submit if يريد
    decrement_spam(uid, amount=1)

    try:
        bot.edit_message_text(new_text, ADMIN_GROUP_ID, message_id, parse_mode="Markdown")
    except Exception:
        pass

    bot.answer_callback_query(call.id, "✅ تم إلغاء الطلب.")

@bot.callback_query_handler(func=lambda call: call.data == "pending_requests")
def pending_requests(call):
    if get_status(call.from_user.id) not in ["admin", "owner"]:
        return bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية", show_alert=True)

    with db_lock:
        cur.execute("SELECT id, user_id, message_id FROM requests WHERE status='pending' ORDER BY id ASC")
        rows = cur.fetchall()

    if not rows:
        bot.answer_callback_query(call.id, "📋 لا يوجد طلبات معلقة حالياً.")
        return

    group_id_for_link = str(ADMIN_GROUP_ID).replace("-100", "")
    lines = []
    for request_id, uid, message_id in rows:
        link = f"https://t.me/c/{group_id_for_link}/{message_id}"
        lines.append(f"• `#{request_id:04d}` - `{uid}` - [رابط]({link})")

    text = "📋 الطلبات المعلقة:\n\n" + "\n".join(lines)
    bot.send_message(call.from_user.id, text)
    bot.answer_callback_query(call.id)

# ---------------- ADMIN PANEL ----------------
@bot.callback_query_handler(func=lambda call: call.data in ["admin_panel", "owner_panel"])
def panels(call):
    status = get_status(call.from_user.id)
    if call.data == "admin_panel":
        bot.edit_message_text("اختر العملية:", call.message.chat.id, call.message.message_id, reply_markup=get_admin_panel_keyboard())
    elif call.data == "owner_panel":
        bot.edit_message_text("اختر العملية:", call.message.chat.id, call.message.message_id, reply_markup=get_owner_panel_keyboard())

# ---------------- ADD ADMIN ----------------
@bot.callback_query_handler(func=lambda call: call.data == "ask_add_admin")
def ask_add_admin(call):
    bot.send_message(call.from_user.id, "📥 أرسل ID الشخص الذي تريد إضافته كمسؤول:")
    bot.register_next_step_handler_by_chat_id(call.from_user.id, add_admin)

def add_admin(m):
    try:
        uid = int(m.text)
        with db_lock:
            cur.execute("INSERT OR IGNORE INTO admins(user_id) VALUES(?)", (uid,))
            conn.commit()
        bot.send_message(m.chat.id, f"✅ تم إضافة {uid} كمسؤول")
    except:
        bot.send_message(m.chat.id, "❌ أدخل رقم ID صحيح")

# ---------------- VIEW ADMINS ----------------
@bot.callback_query_handler(func=lambda call: call.data == "view_admins")
def view_admins(call):
    with db_lock:
        cur.execute("SELECT user_id FROM admins")
        admins = cur.fetchall()
    if not admins:
        bot.send_message(call.from_user.id, "📋 لا يوجد أي مسؤولين حالياً.")
        return

    lines = []
    for a in admins:
        uid = a[0]
        name = None
        try:
            chat = bot.get_chat(uid)
            name_parts = []
            if getattr(chat, "first_name", None):
                name_parts.append(chat.first_name)
            if getattr(chat, "last_name", None):
                name_parts.append(chat.last_name)
            if getattr(chat, "username", None):
                name_parts.append(f"(@{chat.username})")
            name = " ".join(name_parts).strip()
        except Exception:
            name = None

        if name:
            lines.append(f"• {name} — `{uid}`")
        else:
            lines.append(f"• `{uid}`")

    text = "📋 قائمة المسؤولين:\n\n" + "\n".join(lines)
    bot.send_message(call.from_user.id, text)

# ---------------- REMOVE ADMIN (by ID) ----------------
@bot.callback_query_handler(func=lambda call: call.data == "ask_remove_admin")
def ask_remove_admin(call):
    bot.send_message(call.from_user.id, "📥 أرسل ID الشخص الذي تريد حذف صلاحية المسؤول عنه:")
    bot.register_next_step_handler_by_chat_id(call.from_user.id, remove_admin_by_id)


def remove_admin_by_id(m):
    try:
        uid = int(m.text)
        with db_lock:
            cur.execute("DELETE FROM admins WHERE user_id=?", (uid,))
            conn.commit()
        bot.send_message(m.chat.id, f"✅ تم حذف {uid} من المسؤولين")
    except ValueError:
        bot.send_message(m.chat.id, "❌ أدخل رقم ID صحيح")

# ---------------- VIEW BLOCKED ----------------
@bot.callback_query_handler(func=lambda call: call.data == "view_blocked")
def view_blocked(call):
    with db_lock:
        cur.execute("SELECT user_id FROM blocked")
        blocked_users = cur.fetchall()
    if not blocked_users:
        bot.send_message(call.from_user.id, "📋 لا يوجد أي محظورين حالياً.")
        return

    lines = []
    for u in blocked_users:
        uid = u[0]
        name = None
        try:
            chat = bot.get_chat(uid)
            name_parts = []
            if getattr(chat, "first_name", None):
                name_parts.append(chat.first_name)
            if getattr(chat, "last_name", None):
                name_parts.append(chat.last_name)
            if getattr(chat, "username", None):
                name_parts.append(f"(@{chat.username})")
            name = " ".join(name_parts).strip()
        except Exception:
            name = None

        if name:
            lines.append(f"• {name} — `{uid}`")
        else:
            lines.append(f"• `{uid}`")

    text = "📋 قائمة المحظورين:\n\n" + "\n".join(lines)

    kb = types.InlineKeyboardMarkup(row_width=1)
    for u in blocked_users:
        uid = u[0]
        kb.add(types.InlineKeyboardButton(f"✅ رفع الحظر {uid}", callback_data=f"unblock_{uid}"))

    bot.send_message(call.from_user.id, text, reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("unblock_"))
def unblock_user_btn(call):
    if get_status(call.from_user.id) not in ["admin", "owner"]:
        return bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية", show_alert=True)
    uid = int(call.data.split("_")[1])
    with db_lock:
        cur.execute("DELETE FROM blocked WHERE user_id=?", (uid,))
        conn.commit()
    bot.answer_callback_query(call.id, f"✅ تم رفع الحظر عن {uid}")

    # إزالة زر رفع الحظر من نفس الرسالة
    new_kb = call.message.reply_markup
    new_buttons = [b for b in new_kb.keyboard if not any(btn.callback_data == f"unblock_{uid}" for btn in b)]
    if new_buttons:
        new_markup = types.InlineKeyboardMarkup()
        for row in new_buttons:
            new_markup.row(*row)
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=new_markup)
    else:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

# ---------------- BLOCK USERS ----------------
@bot.callback_query_handler(func=lambda call: call.data == "ask_block")
def ask_block(call):
    bot.send_message(call.from_user.id, "📥 أرسل ID الشخص الذي تريد حظره (المستخدمين العاديين فقط):")
    bot.register_next_step_handler_by_chat_id(call.from_user.id, block_user)

def block_user(m):
    try:
        uid = int(m.text)
        status = get_status(uid)
        if status in ["admin", "owner"]:
            bot.send_message(m.chat.id, "❌ لا يمكنك حظر المسؤولين أو الأونر.")
            return
        with db_lock:
            cur.execute("INSERT OR IGNORE INTO blocked(user_id) VALUES(?)", (uid,))
            conn.commit()
        bot.send_message(m.chat.id, f"✅ تم حظر {uid}")
    except ValueError:
        bot.send_message(m.chat.id, "❌ أدخل رقم ID صحيح.")

# ---------------- SEND ANNOUNCEMENT ----------------
@bot.callback_query_handler(func=lambda call: call.data == "send_announcement")
def send_announcement(call):
    announcement_text = """
🌟 **إعلان فتح التقديم للإدارة** 🌟

━━━━━━━━━━━━

نبحث عن **إداريين جدد** للانضمام إلى طاقم العمل.

إذا كنت:
• نشيط
• متفاعل
• تستطيع مساعدة الأعضاء

يمكنك التقديم الآن عبر البوت.

━━━━━━━━━━━━
"""
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        "🚀 التقديم الآن",
        url=f"https://t.me/{bot.get_me().username}?start"
    ))
    msg = bot.send_message(
        PUBLIC_GROUP_ID,
        announcement_text,
        parse_mode="Markdown",
        reply_markup=kb
    )
    bot.pin_chat_message(PUBLIC_GROUP_ID, msg.message_id)
    bot.answer_callback_query(call.id, "✅ تم نشر الإعلان وتثبيته")



# --- مراقبة العقوبات في مجموعة الـ Boss # --- دالة مساعدة لاستخراج ID العضو ---
def get_target_id(m):
    # إذا كان هناك رد، نأخذ ايدي الشخص المردود عليه
    if m.reply_to_message:
        return m.reply_to_message.from_user.id
    
    # إذا لم يكن هناك رد، نبحث عن ID أو يوزر في النص
    text = m.text.split()
    for word in text:
        # فحص إذا كان Word عبارة عن ID رقمي
        if word.isdigit():
            return int(word)
        # فحص إذا كان Word عبارة عن يوزر
        if word.startswith("@"):
            try:
                chat = bot.get_chat(word)
                return chat.id
            except:
                return None
    return None

# --- دالة المراقبة المحدثة ---
@bot.message_handler(func=lambda m: m.chat.id == BOSS_GROUP_ID and m.text)
def watch_punishments(m):
    # 1. فحص الصلاحيات
    try:
        member = bot.get_chat_member(m.chat.id, m.from_user.id)
        if member.status not in ['administrator', 'creator']: return
    except: return

    # 2. التحقق من الكلمة الأولى فقط (الرصد الذكي)
    words = m.text.split()
    first_word = words[0].lower()
    
    # خريطة العقوبات
    punishments = {
        "حظر": "حظر", "كتم": "كتم", "طرد": "طرد", 
        "تقييد": "تقييد", "انذار": "إنذار", "إنذار": "إنذار"
    }

    # إذا كانت الكلمة الأولى ضمن القائمة
    if first_word in punishments:
        action = punishments[first_word]
        target_id = get_target_id(m)
        
        if not target_id: return 

        # جلب المعلومات
        try:
            t_chat = bot.get_chat(target_id)
            t_name, t_user = t_chat.first_name, t_chat.username
        except:
            t_name, t_user = "غير معروف", None

        # تسجيل مؤقت
        with db_lock:
            cur.execute("REPLACE INTO temp_punishments (admin_id, target_id, target_name, target_username, action_type, duration) VALUES (?,?,?,?,?,?)",
                        (m.from_user.id, target_id, t_name, t_user, action, "دائم"))
            conn.commit()

        # إرسال زر الإكمال
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📝 إكمال تسجيل العقوبة", url=f"https://t.me/{bot.get_me().username}?start=punish_{m.from_user.id}"))
        bot.reply_to(m, f"🛡️ تم رصد {action} للعضو `{target_id}`. يرجى إكمال التفاصيل في الخاص.", reply_markup=kb)


# --- معالجة الانتقال للخاص ---
@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.text.startswith('/start punish_'))
def start_punish_private(m):
    try:
        admin_id = int(m.text.split('_')[1])
        if m.from_user.id != admin_id:
            return bot.send_message(m.chat.id, "❌ هذا الرابط مخصص للإداري الذي أصدر العقوبة فقط.")
        
        msg = bot.send_message(m.chat.id, "📝 أرسل سبب العقوبة الآن:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, step_get_reason)
    except: pass

def step_get_reason(m):
    with db_lock:
        cur.execute("UPDATE temp_punishments SET reason=? WHERE admin_id=?", (m.text, m.from_user.id))
        conn.commit()
    msg = bot.send_message(m.chat.id, "📸 أرسل الدليل (صورة أو نص):")
    bot.register_next_step_handler(msg, step_get_evidence)

def step_get_evidence(m):
    admin_id = m.from_user.id
    
    # تحديد نوع الدليل بأمان
    if m.content_type == 'photo':
        evidence_type = "photo"
        evidence_data = m.photo[-1].file_id
    else:
        evidence_type = "text"
        evidence_data = m.text

    with db_lock:
        cur.execute("SELECT * FROM temp_punishments WHERE admin_id=?", (admin_id,))
        data = cur.fetchone()
        cur.execute("DELETE FROM temp_punishments WHERE admin_id=?", (admin_id,))
        conn.commit()

    if not data: 
        return bot.send_message(m.chat.id, "❌ حدث خطأ، يرجى المحاولة من جديد.")

    # تجهيز التقرير
    target_username = f"@{data[3]}" if data[3] else "لا يوجد"
    report_text = (f"🚨 *سجل عقوبة جديد*\n\n"
                   f"🔹 *اسم الإداري:* {m.from_user.first_name}\n"
                   f"🔹 *ايدي العضو:* `{data[1]}`\n"
                   f"🔹 *يوزره:* {target_username}\n"
                   f"🔹 *السبب:* {data[6]}\n"
                   f"🔹 *العقوبة:* {data[4]}\n"
                   f"🔹 *المدة:* {data[5]}\n"
                   f"🔹 *الدليل:* {evidence_data if evidence_type == 'text' else '(صورة مرفقة)'}")

    # --- تصحيح التنسيق هنا ---
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("👤 الإداري", url=f"tg://user?id={admin_id}"),
        types.InlineKeyboardButton("👤 المعاقب", url=f"tg://user?id={data[1]}")
    )

    if evidence_type == "photo":
        bot.send_photo(ADMIN_GROUP_ID, evidence_data, caption=report_text, 
                       message_thread_id=LOG_TOPIC_ID, parse_mode="Markdown", reply_markup=kb)
    else:
        bot.send_message(ADMIN_GROUP_ID, report_text, 
                         message_thread_id=LOG_TOPIC_ID, parse_mode="Markdown", reply_markup=kb)
    
    bot.send_message(m.chat.id, "✅ تم تسجيل العقوبة بنجاح.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("show_p_"))
def show_profile(call):
    uid = call.data.split("_")[2]
    # هذا الأمر يقوم بفتح بروفايل المستخدم مباشرة عبر الرابط الصحيح
    bot.answer_callback_query(call.id, url=f"tg://user?id={uid}")

# ---------------- START ----------------
# ---------------- START ----------------
@bot.message_handler(commands=['start'])
def start(m):
    status = get_status(m.from_user.id)
    if status == "blocked":
        return

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📝 تقديم طلب انضمام", callback_data="start_apply"))

    # عرض عدد الطلبات المتبقية للمستخدم العادي
    if status == "user":
        used = get_today_request_count(m.from_user.id)
        remaining = max(0, 2 - used)
        kb.add(types.InlineKeyboardButton(f"📌 المتبقي اليوم: {remaining}", callback_data="noop"))
        kb.add(types.InlineKeyboardButton("🗂️ سجل طلباتي", callback_data="my_history"))
        kb.add(types.InlineKeyboardButton("🗑️ إلغاء طلب", callback_data="cancel_request"))

    if status in ["admin", "owner"]:
        kb.add(types.InlineKeyboardButton("⚙️ لوحة الإدارة", callback_data="admin_panel"))
    if status == "owner":
        kb.add(types.InlineKeyboardButton("👑 لوحة الأونر", callback_data="owner_panel"))

    safe_send_message(m.chat.id, f"أهلاً بك في نظام الإدارة.\nرتبتك: {status.upper()}", reply_markup=kb)

# ---------------- RUN BOT ----------------
# ---------------- RUN BOT ----------------
if __name__ == "__main__":
    # أضف هذا السطر هنا لحل المشكلة
    bot.remove_webhook() 
    while True:
        try:
            bot.polling(none_stop=True)
        except apihelper.ApiTelegramException as e:
            err = str(e).lower()
            # Common polling conflicts (another instance running) should retry
            if "conflict" in err and "getupdates" in err:
                time.sleep(5)
                continue
            raise
        except Exception:
            # For any other unexpected error, wait a bit and retry
            time.sleep(5)
            continue
