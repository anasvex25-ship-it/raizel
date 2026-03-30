# دليل استضافة البوت على Vercel 🚀

## الخطوات الأساسية لنشر البوت على Vercel

### 1. متطلبات قبل البدء
- ✅ حساب GitHub (مجاني)
- ✅ حساب Vercel (مجاني)
- ✅ قاعدة بيانات PostgreSQL (يمكن استخدام:)
  - ElephantSQL (مجاني): https://www.elephantsql.com
  - Railway: https://railway.app
  - Supabase: https://supabase.com

### 2. إعداد قاعدة البيانات

1. اذهب إلى أحد خدمات قاعدة البيانات أعلاه
2. أنشئ قاعدة بيانات جديدة
3. انسخ رابط الاتصال (DATABASE_URL)
   - يبدو مثل: `postgresql://user:password@host:5432/dbname`

### 3. رفع الكود على GitHub

```bash
# 1. أنشئ مستودع جديد على GitHub
# (اذهب إلى https://github.com/new)

# 2. قم برفع المشروع
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

### 4. نشر على Vercel

#### الطريقة الأولى: عبر الواجهة الرسومية

1. اذهب إلى https://vercel.com
2. سجل الدخول باستخدام GitHub
3. انقر على "New Project"
4. اختر مستودعك من GitHub
5. انقر على "Deploy"

#### الطريقة الثانية: عبر Vercel CLI

```bash
# تثبيت Vercel CLI
npm i -g vercel

# نشر المشروع
vercel
```

### 5. ضبط متغيرات البيئة على Vercel

بعد النشر الأولي:

1. اذهب إلى لوحة التحكم في Vercel
2. اختر مشروعك
3. انقر على "Settings" → "Environment Variables"
4. أضف المتغيرات التالية:

| المتغير | القيمة | الملاحظة |
|---------|--------|---------|
| `TELEGRAM_TOKEN` | `7505333614:AAGAdECKNcmwnLf9iixeYYm8c6NmeQsv8Og` | رمز البوت من BotFather |
| `DATABASE_URL` | `postgresql://...` | رابط قاعدة البيانات الكاملة |

### 6. ضبط الـ Webhook في Telegram

بعد النشر الناجح، ستحصل على URL Vercel (مثل: `https://your-bot.vercel.app`)

قم بتشغيل هذا الأمر (أو البحث والاستخدام عبر Telegram API):

```bash
curl -X POST https://api.telegram.org/bot<TELEGRAM_TOKEN>/setWebhook \
  -d "url=https://your-bot.vercel.app/<TELEGRAM_TOKEN>"
```

استبدل:
- `<TELEGRAM_TOKEN>` برمز البوت الفعلي
- `https://your-bot.vercel.app` برابط مشروعك على Vercel

**أو استخدم بوت BotFather مباشرة:**

أرسل إلى BotFather:
```
/setwebhook
https://your-bot.vercel.app/YOUR_TOKEN
```

### 7. التحقق من أن البوت يعمل

- اذهب إلى Vercel Dashboard
- انقر على "Deployments"
- تأكد من أن آخر نشر في حالة "Ready"
- تفعل البوت على Telegram وتأكد من استجابته

### 8. رفع تغييرات جديدة

كل ما تحتاج فقط:

```bash
git add .
git commit -m "Your message"
git push
```

Vercel سيعيد النشر تلقائياً! 🎉

---

## معلومات مهمة ⚠️

### ملفات المشروع الأساسية:

```
📦 Your Bot Project
├── 📄 vercel.json          # ✅ يحتوي على إعدادات Vercel
├── 📄 requirements.txt      # ✅ المكتبات المطلوبة
├── 📂 api/
│   └── 📄 index.py        # ✅ الكود الرئيسي للبوت
└── 📄 .gitignore          # (اختياري) لإخفاء الملفات
```

### تجنب الأخطاء الشائعة:

❌ **لا تفعل:**
- لا تحفظ رموز مباشرة في الكود
- لا تحفظ DATABASE_URL في الملفات
- لا تستخدم `bot.polling()` سيؤدي للتوقف

✅ **افعل:**
- استخدم متغيرات البيئة فقط
- استخدم Webhooks (الكود يفعل هذا تلقائياً)
- تأكد من `os.getenv()` يقرأ المتغيرات

### هياكل الملفات المطلوبة:

**vercel.json:** يجب أن يحتوي على:
```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/index.py"
    }
  ]
}
```

---

## المتطلبات التقنية 🔧

البوت الحالي يستخدم:
- **Flask** - خادم الويب
- **pyTelegramBotAPI** - مكتبة Telegram
- **PostgreSQL** - قاعدة البيانات
- **Vercel Python Runtime** - استضافة الكود

---

## الدعم والمشاكل الشائعة 🆘

### المشكلة: "Module not found"
**الحل:** تأكد من أن جميع المكتبات مدرجة في `requirements.txt`

### المشكلة: "Database connection refused"
**الحل:** تحقق من صحة `DATABASE_URL` وأنه فعال

### المشكلة: "Bot not responding"
**الحل:** 
1. تحقق من أن Webhook مضبوط بشكل صحيح
2. تفقد السجلات في Vercel Dashboard → Logs

### المشكلة: "Unauthorized"
**الحل:** تحقق من أن `TELEGRAM_TOKEN` صحيح وفعال

---

## روابط مفيدة 📚

- Telegram BotFather: https://t.me/botfather
- Vercel Docs: https://vercel.com/docs
- Python Runtime: https://vercel.com/docs/runtimes/python
- ElephantSQL: https://www.elephantsql.com/
- telebot Documentation: https://pypi.org/project/pyTelegramBotAPI/

---

**تم التحديث:** 30 مارس 2026
