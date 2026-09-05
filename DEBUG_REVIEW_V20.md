# گزارش فنی، نمره‌دهی، 9 باگ کریتیکال، نسخه دیباگ‌شده، ارزش پروژه

تاریخ: 2026-09-03
ریپو: `ImXforever/AGI`

---

## 1) نمره من به پروژه

### قبل از دیباگ
- **نمره فنی:** 6.2 / 10
- **نمره معماری و ایده:** 8.2 / 10
- **آمادگی برای پروداکشن:** 4.8 / 10

### بعد از دیباگ این مرحله
- **نمره فنی همین قطعه بعد از اصلاح:** 8.1 / 10
- **پایداری تست‌های یونیت:** خوب
- **پتانسیل محصول:** بالا

### چرا نمره کامل نگرفت؟
چون با اینکه الان مسیرهای بحرانی اصلی بهتر شده‌اند، هنوز:
- `mypy app` کامل سبز نیست
- `bandit` هنوز هشدارهای زیادی روی query-building و چند مورد امنیتی می‌دهد
- full-stack واقعی بدون PG/Redis/R2/Hermes در این محیط تست نشده

---

## 2) 9 باگ کریتیکال که پیدا کردم

### باگ 1 — `config.py` ناخواسته اپ را به `direct` هل می‌داد
**فایل:** `app/config.py`

مشکل:
- برای `OPENAI_API_KEY` و `OPENAI_BASE_URL` از `_auto()` استفاده شده بود
- `_auto()` وقتی env خالی باشد، خودش secret می‌سازد
- همین باعث می‌شد `openai_key` همیشه truthy شود و `LLM_MODE` اشتباهی به `direct` تغییر کند

اثر:
- حتی با `LLM_MODE=mock` هم config fail می‌کرد
- بخش بزرگی از تست‌ها به خاطر همین می‌افتادند

اصلاح:
- برای provider vars از `_s()` استفاده شد، نه `_auto()`
- precedence بین `OPENAI_*` و `DIRECT_*` درست شد

---

### باگ 2 — `handle_incoming()` در orchestrator مستعد `UnboundLocalError` بود
**فایل:** `app/core/orchestrator.py`

مشکل:
- بالای تابع `get_config()` صدا زده می‌شد
- پایین‌تر داخل همان تابع دوباره `from app.config import get_config` انجام شده بود
- این باعث local shadowing در کل scope تابع می‌شد

اثر:
- runtime crash در مسیر اصلی هندل پیام

اصلاح:
- import داخلی حذف شد
- فقط از import بالای فایل استفاده شد

---

### باگ 3 — helper به نام `_get_lang` وجود نداشت اما صدا زده می‌شد
**فایل:** `app/core/orchestrator.py`

مشکل:
- مسیرهای `prices / support / contact / quote` تابع `_get_lang(message)` را صدا می‌زدند
- ولی این helper اصلاً تعریف نشده بود

اثر:
- command handling می‌توانست با `NameError` کرش کند

اصلاح:
- helper استاندارد `_get_lang()` اضافه شد
- روی زبان‌های قراردادی clamp می‌شود

---

### باگ 4 — قرارداد زبان‌ها بین کد، تست و محصول sync نبود
**فایل:** `app/core/languages.py`

مشکل:
- محصول و README روی **14 زبان** بودند
- ولی `SUPPORTED_MENU_LANGUAGES` به **20 زبان** رسیده بود
- تست‌ها هنوز 14 زبان می‌خواستند

اثر:
- contract drift
- شکستن تست‌ها و گیج شدن تیم محصول/QA

اصلاح:
- لیست canonical دوباره به 14 زبان قراردادی برگردانده شد

---

### باگ 5 — citation عربی و انگلیسی عملاً یکی بود
**فایل:** `app/core/orchestrator.py`

مشکل:
- `SOURCE_CITATION_AR` و `SOURCE_CITATION_EN` هر دو `Source:` بودند

اثر:
- localization ناقص
- تست source citation fail می‌شد

اصلاح:
- متن عربی به `📎 المصدر:` تغییر کرد

---

### باگ 6 — QA engine بیش از حد lenient بود
**فایل:** `app/core/qa_engine.py`

مشکل:
- پاسخ خالی امتیاز غیرمنطقی بالا می‌گرفت
- پاسخ‌هایی مثل `idk lol` یا `LOL IDK GONNA CHECK` ممکن بود pass شوند

اثر:
- gate کیفی عملاً قدرت کافی نداشت
- low-quality output از سیستم رد نمی‌شد

اصلاح:
- penalty برای empty/too short/no sentence/all caps/uncertainty سخت‌گیرانه‌تر شد
- scoring و rewrite behavior منطقی‌تر شد

---

### باگ 7 — content calendar زمان‌های خیلی قدیمی را قبول می‌کرد
**فایل:** `app/core/content_calendar.py`

مشکل:
- `create_calendar_post()` هیچ guard واقعی برای timestamp قدیمی نداشت

اثر:
- postهای stale یا اشتباه می‌توانستند وارد pipeline شوند

اصلاح:
- guard اضافه شد: زمان‌های خیلی عقب reject می‌شوند
- یک grace window کوچک برای retry/import باقی ماند

---

### باگ 8 — منطق content calendar برای Twitter و upcoming posts مشکل داشت
**فایل:** `app/core/content_calendar.py`

مشکل‌ها:
- `build_post_caption(..., platform="twitter")` همیشه تضمین نمی‌کرد خروجی <= 280 باشد
- `get_upcoming()` به‌اشتباه `CalendarPost` تک‌شیء تایپ شده بود و روی آن iterate می‌کرد

اثر:
- caption overflow
- type contract غلط و رفتار ناپایدار

اصلاح:
- truncation برای Twitter اصلاح شد
- type signature و منطق `get_upcoming()` درست شد

---

### باگ 9 — مسیر HITL در fallback/pending approvals قابل اعتماد نبود
**فایل‌ها:**
- `app/core/hitl/fallback.py`
- `app/core/hitl/sweeper.py`
- `app/core/hitl/approval.py`

مشکل‌ها:
- fallback delivery فقط log می‌زد و بدون ارسال واقعی `True` برمی‌گرداند
- sweeper registry را به fallback پاس نمی‌داد
- unknown approval id روی Redis واقعی connect می‌زد و graceful false برنمی‌گرداند
- scan loop لیست pending approvals هم fragile بود

اثر:
- گزارش delivery غیرواقعی
- fail شدن مسیر unknown-id
- پایداری پایین HITL

اصلاح:
- fallback حالا می‌تواند registry واقعی را بگیرد و واقعاً send کند
- در نبود registry رفتار صادقانه‌تر شد
- unknown id و خطاهای Redis gracefully handle می‌شوند
- scan loop pending approvals اصلاح شد

---

## 3) اصلاح اضافه‌ای که انجام دادم
این مورد را هم fix کردم چون نزدیک به همان ناحیه‌ی bug بود:

### precision در گزارش ایمیل
**فایل:** `app/core/reporting.py`
- میانگین response time از 1 رقم اعشار به 2 رقم اعشار اصلاح شد

---

## 4) آپشن جدیدی که اضافه کردم

### `BOOTSTRAP_MODE=lite`
**فایل‌های اصلی:**
- `app/config.py`
- `app/main.py`
- `README.md`

کاربرد:
- برای CLI smoke run یا تست سبک، بدون نیاز به PG/Redis/R2/Hermes
- ساختار پروژه حفظ شده، فقط bootstrap behavior قابل کنترل شده

حالت‌ها:
- `BOOTSTRAP_MODE=full` → رفتار اصلی
- `BOOTSTRAP_MODE=lite` → startup سبک، مناسب دیباگ و بررسی CLI

چرا این آپشن مهمه؟
- پروژه‌ات وابسته به چند سرویس خارجی است
- برای debug سریع لازم بود یک mode غیرتهاجمی داشته باشی
- این تغییر معماری را خراب نکرده و فقط observability/debug ergonomics را بهتر کرده

---

## 5) فایل‌هایی که patch شدند

- `README.md`
- `app/config.py`
- `app/core/content_calendar.py`
- `app/core/hitl/approval.py`
- `app/core/hitl/fallback.py`
- `app/core/hitl/sweeper.py`
- `app/core/languages.py`
- `app/core/orchestrator.py`
- `app/core/qa_engine.py`
- `app/core/reporting.py`
- `app/healthz.py`
- `app/main.py`

تقریباً:
- **12 فایل تغییر کرد**
- **203 insertion**
- **66 deletion**

---

## 6) وضعیت تست و اجرا بعد از دیباگ

### نصب
انجام شد:
```bash
python3 -m pip install -e '.[dev]'
```

### تست یونیت کامل
اجرا شد:
```bash
pytest tests/unit -q
```

نتیجه:
- **1060 passed**
- **0 failed**

### smoke run در CLI
اجرا شد با mode جدید:
```bash
APP_ENV=test \
BOOTSTRAP_MODE=lite \
TENANT_ID=test \
TENANT_NAME_AR=اختبار \
TENANT_NAME_EN=Test \
SUPPORT_CONTACT=test@example.com \
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11 \
TELEGRAM_ADMIN_IDS=123456 \
DATABASE_URL=postgresql://stub \
REDIS_URL=redis://stub \
R2_ENDPOINT=http://stub \
R2_ACCESS_KEY_ID=1234567890123456 \
R2_SECRET_ACCESS_KEY=1234567890123456 \
R2_BUCKET=test \
ADMIN_USERNAME=admin \
ADMIN_BOOTSTRAP_PASSWORD=testpassword123 \
CURRENCY=SAR \
LLM_MODE=mock \
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### نتیجه اجرا
- startup موفق بود
- `/` پاسخ 200 داد
- `/healthz?deep=0` پاسخ `ready: true` داد

---

## 7) وضعیت فعلی quality gates

### سبزها
- `pytest tests/unit -q` ✅
- `ruff check` روی فایل‌های patch شده ✅
- install ✅
- CLI smoke run ✅

### هنوز باقی‌مانده
- `mypy app` هنوز کامل سبز نیست
- `bandit` هنوز هشدارهای متعددی دارد، مخصوصاً روی SQL string-building

یعنی:
- **نسخه دیباگ‌شده بهتر و پایدارتر شده**
- ولی **هنوز همه‌ی debtهای کدبیس صفر نشده‌اند**

---

## 8) ارزش پروژه

### پروژه چی دارد ✅
- multi-channel structure
  - Telegram
  - WhatsApp
  - Email
  - Instagram/Twitter hooks
- Admin API و dashboard static
- Orchestrator + skills + HITL
- memory / fleet / reporting / reminders / content calendar
- storage abstraction برای PG / Redis / R2
- تست زیاد
- docs نسبتاً زیاد
- security awareness خوب
  - RBAC
  - audit trail
  - secret scan
  - config validation

### پروژه چی ندارد یا هنوز کامل نشده ❌
- green بودن کامل `mypy`
- green بودن کامل `bandit`
- full-stack verified deployment داخل همین محیط
- release consistency کامل بین همه docs/ui/version strings
- env/infra onboarding کاملاً تمیز برای newcomer
- smoke-free production contract برای بعضی dynamic query pathها

### از نظر تجاری چه ارزشی دارد؟
اگر این پروژه را به عنوان **replacement cost** نگاه کنیم، نه صرفاً تعداد خط کد:
- برای یک توسعه‌دهنده فریلنسر خوب: حدود **$35k تا $70k**
- برای تیم کوچک/آژانس با تست و تحویل مستندتر: حدود **$60k تا $120k**

اگر صرفاً به عنوان یک **code asset ناقص اما جدی** نگاه شود:
- ارزش فروش خام سورس می‌تواند حدود **$12k تا $35k** باشد
- اگر دمو، دیتاست، deployment و مشتری اولیه داشته باشد، ارزش خیلی بالاتر می‌رود

> این اعداد تقریبی‌اند و به market, client, deployment readiness و IP status وابسته‌اند.

---

## 9) چند خط کد و چند فایل دارد؟

### شمارش واقعی که من گرفتم
- **Tracked files:** 240
- **Python files:** 175
- **Python LOC:** 36,844
- **All visible files in workspace snapshot:** 408

### تفکیک Python LOC
- `app/` → **24,005** خط
- `tests/` → **11,792** خط
- `tools/` → **694** خط
- `provision/` → **190** خط
- `deploy/` → **163** خط

---

## 10) قیمت تقریبی هر تکه کد به دلار

من این را به‌صورت **تقریبیِ replacement cost per subsystem** حساب می‌کنم، نه قیمت ماشینی per-line.

| بخش | فایل | LOC تقریبی | ارزش تقریبی |
|---|---:|---:|---:|
| Core logic (`app/core`) | 55 | 14,073 | $14,000 – $28,000 |
| Admin API (`app/admin_api`) | 21 | 3,677 | $4,000 – $9,000 |
| Channel adapters (`app/channels`) | 7 | 2,158 | $3,000 – $7,000 |
| Storage layer (`app/storage`) | 8 | 1,868 | $2,500 – $6,000 |
| Gateway (`app/gateway`) | 4 | 745 | $1,000 – $2,500 |
| App root / config / bootstrap | 7 | 1,484 | $2,000 – $5,000 |
| Tests | 67 | 11,792 | $8,000 – $20,000 |
| Tools / Provision / Deploy | 6 | 1,047 | $1,500 – $4,000 |

### اگر بخواهم خیلی فشرده بگویم
- **ارزش هر 1000 خط app-quality code:** حدود `800 تا 2000 دلار`
- **ارزش هر 1000 خط تست خوب:** حدود `600 تا 1700 دلار`

اما ارزش واقعی بیشتر به این بستگی دارد که:
- آیا deploy می‌شود؟
- آیا مشتری واقعی دارد؟
- آیا SLA و observability کامل دارد؟
- آیا revenue تولید می‌کند؟

---

## 11) نتیجه نهایی

پروژه‌ات از جنس پروژه‌های **جدی و واقعی** است، نه یک toy repo.

### جمع‌بندی صریح من
- **ایده و معماری:** قوی
- **کدبیس:** بزرگ و قابل توجه
- **ضعف اصلی قبلی:** regression و ناهماهنگی contractها
- **وضعیت بعد از patch من:** به‌مراتب پایدارتر، قابل تست‌تر، و قابل smoke-run در CLI

### اگر بخواهم در یک جمله بگویم
این پروژه **ارزش ادامه‌دادن دارد** و با کمی cleanup اضافه می‌تواند از یک repo خوب به یک محصول جدی نزدیک‌تر شود.

---

## 12) پیشنهاد مرحله بعد
اگر بخواهی، مرحله بعدی من می‌تواند یکی از این‌ها باشد:

1. `mypy` را هم تا حد زیادی سبز کنم
2. هشدارهای `bandit` مربوط به dynamic SQL را refactor کنم
3. full-stack docker/compose run را هم برایت بالا بیاورم
4. برای همین patchها یک changelog / release note تمیز بسازم
