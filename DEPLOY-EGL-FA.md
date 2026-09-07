# استقرار Zenovix Agent برای Elian Global Logistics (EGL) روی Railway

این پوشه = کل پروژه‌ی AGI + دیتای EGL + کد Twilio (واتس‌اپ و ایمیل)، آماده‌ی دیپلوی.
هیچ رمزی داخل این پوشه نیست؛ همه‌ی رمزها فقط در Variables ریلوی وارد می‌شوند.

## چه چیزهایی نسبت به ریپوی اصلی تغییر کرده (۲۳ فایل)

| بخش | فایل‌ها | چه شد |
|---|---|---|
| دانش EGL | `db/seed/001..004_*.json`، `product/knowledge/*.md` | دیتای واقعی سایت egl.co.ae (۱۱ محصول/خدمت، ۲۳ FAQ، ۷ راهنما، ۶ قالب، ۶ سند) |
| اتصال دانش به ربات | `app/core/knowledge_context.py` (جدید)، `app/core/hermes_client.py` | FAQ/راهنما/اسناد قبل از هر پاسخ به مدل داده می‌شوند |
| پاک‌سازی دیتای نمونه | `db/migrations/0014_retire_sample_dataset.sql` (جدید) | ردیف‌های نمونه‌ی قدیمی (PET-001…) در دیتابیس فعلی غیرفعال می‌شوند |
| برندینگ | `app/core/translations.py`، `env.example` | منوها و تماس EGL به‌جای ZENOVIX |
| Twilio | `app/config.py`، `app/channels/email.py`، `app/channels/whatsapp.py`، `app/channels/base.py`، `app/main.py` | ایمیل از طریق SendGrid، دریافت ایمیل با IMAP (پولر روشن شد)، تبدیل HTML برای واتس‌اپ |
| تست | `tests/unit/test_knowledge_context.py`، `tests/unit/test_twilio_channels.py` | ۲۰ تست جدید؛ کل پروژه ۱۲۲۲ تست پاس |

## قدم ۱ — بردن پروژه به GitHub

**راه الف (پیشنهادی، بدون ترمینال):** در ریپوی `ImXforever/AGI` → Add file → **Upload files** → کل محتویات این پوشه را (نه خود پوشه را) بکش و رها کن → Commit.
GitHub فایل‌های هم‌نام را جایگزین می‌کند و جدیدها را اضافه می‌کند.
فقط یک فایل باید دستی حذف شود: `product/knowledge/policies.md` (نمونه‌ی قدیمی) → باز کن → ⋯ → Delete file.

**راه ب (ترمینال):**
```
git clone https://github.com/ImXforever/AGI.git && cd AGI
# محتویات این zip را روی پوشه کپی کن (جایگزین)، سپس:
git rm -q product/knowledge/policies.md
git add -A && git commit -m "EGL tenant: knowledge base, Twilio WhatsApp + SendGrid email" && git push
```

## قدم ۲ — متغیرهای Railway

سرویس **AGI** → Variables → **Raw Editor** → محتوای `railway-variables-ZENOVIX.env` (کنار همین فایل) را Paste کن.
فقط مقادیر `PASTE_…` را خودت پر کن:

| متغیر | از کجا |
|---|---|
| `TELEGRAM_BOT_TOKEN` | تلگرام → @BotFather |
| `TELEGRAM_ADMIN_IDS` | تلگرام → @userinfobot (عدد Id خودت؛ همین شخص تأییدها را می‌گیرد) |
| `DIRECT_API_KEY` | کلید OpenAI (یا OpenRouter؛ توضیح داخل فایل) |
| `TWILIO_ACCOUNT_SID`، `TWILIO_AUTH_TOKEN` | Twilio Console → صفحه‌ی اصلی → کادر Account Info |
| `SENDGRID_API_KEY` | کارت Send an email → SendGrid → Settings → API Keys → Create (Full Access) |
| `EMAIL_FROM` | آدرسی که در SendGrid → Sender Authentication → Single Sender تأیید کردی |
| `IMAP_USER`، `IMAP_PASSWORD` | همان صندوق (Gmail: IMAP روشن + App Password ۱۶ رقمی) |

اگر ۴ متغیر `R2_*` بعد از ذخیره قرمز/خالی بودند: Bucket → تب Credentials → ۴ مقدار را دستی کپی کن.

## قدم ۳ — بعد از سبز شدن Deploy (یک بار)

1. **تلگرام** — این آدرس را در مرورگر باز کن (توکن خودت را بگذار):
   `https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://agi-production-1f9f.up.railway.app/tg/webhook&secret_token=934ab050e9b8fca0840fbcf286816b62aa44a13e9a46ea26`
   باید `"ok":true` ببینی.
2. **واتس‌اپ** — Twilio → Messaging → Try it out → Send a WhatsApp message → تب Sandbox settings →
   *When a message comes in* = `https://agi-production-1f9f.up.railway.app/wa/webhook` (POST) → Save.
   با گوشی خودت کد `join …` را به شماره‌ی Sandbox بفرست.
3. **سلامت** — `https://agi-production-1f9f.up.railway.app/healthz` باید `"status":"ok"` بدهد.
4. **پنل ادمین** — `https://agi-production-1f9f.up.railway.app/admin` با `ADMIN_USERNAME` / `ADMIN_BOOTSTRAP_PASSWORD`.

## قدم ۴ — تست

| کانال | چه کنی | چه باید ببینی |
|---|---|---|
| تلگرام | `/start` سپس «ساعت کاری‌تون چیه؟» | منوی EGL، سپس پاسخ: میز معاملات ۲۴/۷، دفتر یکشنبه–پنجشنبه ۹–۱۸ |
| واتس‌اپ | از شماره‌ی join‌شده: «Do you supply bunker fuel in Fujairah?» | پاسخ از FAQ + پیشنهاد پیش‌فاکتور، **بدون هیچ عددی** |
| ایمیل | از یک ایمیل دیگر به صندوق IMAP بنویس | حداکثر ۶۰ ثانیه بعد پاسخ می‌آید؛ Reply-To = info@egl.co.ae |
| قیمت | «قیمت دیزل چنده؟» | ربات قیمت نمی‌گوید؛ پیش‌فاکتور توسط تیم را پیشنهاد می‌دهد |

## محدودیت‌هایی که باید بدانی

- **Sandbox واتس‌اپ**: فقط شماره‌های join‌شده جواب می‌گیرند؛ هر ۷۲ ساعت باید دوباره join کرد. برای مشتری واقعی باید شماره‌ی خود EGL در Twilio ثبت شود.
- **ایمیل ورودی Twilio (Inbound Parse)** به دامنه‌ی اختصاصی + رکورد MX نیاز دارد؛ به همین دلیل دریافت با IMAP انجام می‌شود. برای حالت نهایی: دامنه‌ی egl.co.ae را در SendGrid احراز کن و `EMAIL_FROM=info@egl.co.ae` و IMAP همان صندوق شرکت.
- **قیمت‌ها**: سایت EGL هیچ قیمتی ندارد؛ ربات هرگز قیمت نمی‌گوید و به پیش‌فاکتور (با تأیید انسانی) ارجاع می‌دهد.
- **CI گیت‌هاب**: بررسی فرمت (ruff) روی ریپوی اصلی از قبل قرمز بود (۵۴ فایل قدیمی)؛ روی دیپلوی ریلوی اثری ندارد.
