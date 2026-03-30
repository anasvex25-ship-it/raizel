# قائمة المراجعة السريعة - نشر البوت على Vercel ✅

## الخطوات الأساسية (10 دقائق)

### 1️⃣ إعداد GitHub
- [ ] أنشئ حساب GitHub (إذا لم يكن موجوداً)
- [ ] أنشئ مستودع جديد: https://github.com/new
- [ ] أعطِ المستودع اسماً (مثل: `telegram-admin-bot`)

### 2️⃣ إعداد قاعدة البيانات
- [ ] اذهب إلى https://www.elephantsql.com
- [ ] أنشئ حساب مجاني
- [ ] أنشئ قاعدة بيانات جديدة
- [ ] **انسخ DATABASE_URL** (ستحتاج إليها لاحقاً)

### 3️⃣ رفع الكود
```bash
cd "c:\Users\Hp\Downloads\Nouveau dossier"
git init
git add .
git commit -m "Initial bot setup"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### 4️⃣ نشر على Vercel
- [ ] اذهب إلى https://vercel.com
- [ ] سجل الدخول بـ GitHub
- [ ] انقر "New Project"
- [ ] اختر مستودعك
- [ ] انقر "Deploy"

### 5️⃣ إضافة متغيرات البيئة
بعد النشر الأولي:
1. اذهب إلى لوحة المشروع
2. انقر "Settings"
3. اختر "Environment Variables"
4. أضف:
   - **Name:** `TELEGRAM_TOKEN`
   - **Value:** `7505333614:AAGAdECKNcmwnLf9iixeYYm8c6NmeQsv8Og`
   
5. أضف:
   - **Name:** `DATABASE_URL`
   - **Value:** (الرابط من ElephantSQL)

6. انقر "Redeploy" لتطبيق التغييرات

### 6️⃣ ضبط Webhook
احصل على رابط Vercel من: **Settings → Domains**

ثم ارسل أمر curl في Terminal:
```bash
curl -X POST https://api.telegram.org/bot7505333614:AAGAdECKNcmwnLf9iixeYYm8c6NmeQsv8Og/setWebhook \
  -d "url=https://YOUR-BOT.vercel.app/7505333614:AAGAdECKNcmwnLf9iixeYYm8c6NmeQsv8Og"
```

أو ارسل إلى @BotFather:
```
/setwebhook
https://YOUR-BOT.vercel.app/7505333614:AAGAdECKNcmwnLf9iixeYYm8c6NmeQsv8Og
```

### 7️⃣ اختبر البوت
- [ ] اذهب إلى البوت على Telegram
- [ ] ارسل `/start`
- [ ] تأكد من الاستجابة

---

## ملاحظات مهمة ⚠️

✅ **تم تنفيذه بالفعل:**
- ✔️ إزالة TOKEN المشفر من الكود
- ✔️ إعدادات vercel.json صحيحة
- ✔️ متطلبات requirements.txt محدثة
- ✔️ ملف .gitignore موجود

⚠️ **انتبه:**
- لا تشارك رابط قاعدة البيانات مع أحد
- لا تحفظ البيانات الحساسة في الملفات
- استخدم Environment Variables فقط

---

## روابط سريعة

| الخدمة | الرابط |
|-------|--------|
| Vercel | https://vercel.com |
| GitHub | https://github.com |
| ElephantSQL | https://www.elephantsql.com |
| BotFather | https://t.me/botfather |
| Telegram API | https://core.telegram.org |

---

**الوقت المتوقع:** 15-20 دقيقة
**المستوى:** مبتدئ ✨
**تاريخ:** 30 مارس 2026
