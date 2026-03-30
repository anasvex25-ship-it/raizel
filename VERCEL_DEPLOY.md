# 🚀 Deploy to Vercel - محرك التثبيت

## حالة الكود الحالية ✅
الكود محدث ومجهز للتثبيت:
- ✅ `api/index.py` - البوت مع لوحة التحكم
- ✅ `api/dashboard.html` - واجهة التحكم بـ HTML مرحب
- ✅ Git commits جاهزة

## المشكلة 🚫
لا يمكن دفع الكود عبر GitHub لأن حسابك `anaslot` لا يملك صلاحيات على المستودع

## الحل 2️⃣ Options

### خيار 1️⃣: استخدام Vercel CLI (الأسهل)
```
npm install -g vercel
vercel --prod
```
هذا سيدفع الملفات مباشرة إلى Vercel بدون الحاجة لـ GitHub!

### خيار 2️⃣: إعادة تسجيل GitHub
إذا تريد استخدام GitHub:
1. تأكد من أن اسمك صاحب المستودع
2. أو استخدم GitHub token:
```
git remote set-url origin https://[TOKEN]@github.com/USERNAME/raizel.git
git push origin main
```

### خيار 3️⃣: من Vercel Dashboard مباشرة
1. اذهب إلى https://vercel.com/dashboard
2. اختر المشروع raizel-d2c3
3. انقر على "Redeploy" هنا: https://vercel.com/dashboard/raizel-d2c3/deployments

## بعد التثبيت 🎉
روابط مهمة:
- Dashboard: https://razael.vercel.app/
- API Status: https://razael.vercel.app/api/status

## الأزرار على Dashboard 🎮
- ▶️ ابدأ البوت - بدء البوت
- ⏹️ أوقف البوت - إيقاف البوت
- 🔄 أعدا التشغيل - إعادة تشغيل
- 🗑️ امسح السجل - حذف السجلات

---

تم التحديث: 30/3/2026 ✨
