"""Complete UI translations for all supported languages with English default."""

from __future__ import annotations

from typing import Any

MENUS: dict[str, dict[str, str]] = {
    "en": {
        "welcome": "✨ <b>Welcome to Zenovix</b>\n━━━━━━━━━━━━━━━━━━━━━━━\nAI &amp; Digital Technology · Dubai\n\nArtificial intelligence, cloud &amp; ICT, web &amp; mobile,\nintelligent automation, data &amp; analytics, animation &amp; 3D.\n\nHow can we help you today?",
        "help": "📖 <b>Help Guide</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n🚀 <b>Quick Commands</b>\n  /start  — Open main menu\n  /lang   — Change language\n  /prices — Product pricing\n  /support — Technical support\n  /quote — Request a quote\n  /contact — Contact information\n  /help — This help page\n\n💡 You can also send any question directly\nand I'll route it to the right specialist.\n\n🆘 For emergencies, just type <b>emergency</b>.",
        "clarification": "Sorry, I couldn't fully understand your request. Could you please rephrase or clarify what you need?",
        "guard_rejected": "⚠️ This message was rejected because it contains disallowed content. If you have a genuine question, please rephrase it.",
        "no_knowledge": "I'm sorry, I don't have enough information about this topic in our database. Can I help you with something else related to our products or services?",
        "pricing": "💰 <b>Products &amp; Pricing</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nEvery project is scoped and priced in a formal proposal.\n\nTell us the service (e.g. <b>AI chatbot</b>, <b>website</b>, <b>automation</b>, <b>dashboard</b>), the scope and your timeline — our team will prepare a proposal.",
        "support": "🛠️ <b>Technical Support</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nDescribe your issue and I'll connect you with the right team.\n\nFor urgent issues, type <b>emergency</b>.",
        "quote": "📋 <b>Request a Quote</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nPlease provide:\n• Service (AI, cloud &amp; ICT, web &amp; mobile, automation, data, animation &amp; 3D)\n• What you want to build and for whom\n• Languages, integrations and timeline\n• Company name and contact\n\nOur team will prepare a proposal and a manager will confirm it.",
        "contact": "📞 <b>Contact Us</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n📧 Email: {email}\n📞 Phone: +971 4570 1100\n💬 WhatsApp: wa.me/97145701100\n🕐 Office: Mon–Fri 9:00–18:00 GST (UTC+4)\n📍 Office 2703, Aspect Tower, Business Bay, Dubai, UAE\n\n🚨 For urgent matters, type <b>emergency</b>",
        "lang_picker": "🌐 <b>Choose your language / لطفاً زبان خود را انتخاب کنید:</b>",
    },
    "fa": {
        "welcome": "✨ <b>به زنوویکس خوش آمدید</b>\n━━━━━━━━━━━━━━━━━━━━━━━\nهوش مصنوعی و فناوری دیجیتال · دبی\n\nهوش مصنوعی، کلاود و ICT، وب و موبایل،\nاتوماسیون هوشمند، داده و تحلیل، انیمیشن و سه‌بعدی.\n\nامروز چطور می‌توانم کمکتان کنم؟",
        "help": "📖 <b>راهنمای دستورات و استفاده</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n🚀 <b>دستورات سریع:</b>\n  /start  — باز کردن منوی اصلی\n  /lang   — تغییر زبان سیستم\n  /prices — لیست قیمت و محصولات\n  /support — پشتیبانی فنی\n  /quote — درخواست پیش‌فاکتور\n  /contact — اطلاعات تماس\n  /help — صفحه راهنما\n\n💡 همچنین می‌توانید هر سوالی دارید را مستقیماً ارسال کنید تا پاسخ مناسب دریافت نمایید.\n\n🆘 برای موارد اضطراری کلمه <b>emergency</b> را ارسال کنید.",
        "clarification": "متأسفانه متوجه درخواست شما نشدم. لطفاً سوال یا درخواست خود را دقیق‌تر بیان کنید.",
        "guard_rejected": "⚠️ پیام ارسالی به دلیل محتوای غیرمجاز پردازش نشد. در صورت وجود سوال مرتبط، لطفاً پیام خود را بازنویسی کنید.",
        "no_knowledge": "متأسفانه اطلاعات کافی در این زمینه در پایگاه دانش موجود نیست. آیا می‌توانم در مورد محصولات یا خدمات دیگر به شما کمک کنم؟",
        "pricing": "💰 <b>محصولات و قیمت‌ها</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nقیمت هر پروژه پس از بررسی دامنهٔ کار در پیشنهاد رسمی اعلام می‌شود.\n\nخدمت موردنظر (مثلاً <b>چت‌بات هوش مصنوعی</b>، <b>وب‌سایت</b>، <b>اتوماسیون</b>، <b>داشبورد</b>)، دامنهٔ کار و زمان‌بندی را بفرستید تا تیم ما پیشنهاد فنی و مالی آماده کند.",
        "support": "🛠️ <b>پشتیبانی فنی</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nمشکل یا سوال فنی خود را شرح دهید تا بررسی شود.\n\nبرای موارد فوری کلمه <b>emergency</b> را تایپ کنید.",
        "quote": "📋 <b>درخواست استعلام / پیش‌فاکتور</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nلطفاً موارد زیر را مشخص فرمایید:\n• خدمت (هوش مصنوعی، کلاود و ICT، وب و موبایل، اتوماسیون، داده، انیمیشن و سه‌بعدی)\n• چه چیزی می‌خواهید بسازید و برای چه کسی\n• زبان‌ها، یکپارچه‌سازی‌ها و زمان‌بندی\n• نام شرکت و اطلاعات تماس\n\nتیم ما پیشنهاد فنی و مالی را آماده می‌کند و یک مدیر آن را تأیید می‌کند.",
        "contact": "📞 <b>اطلاعات تماس</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n📧 ایمیل: {email}\n📞 تلفن: +971 4570 1100\n💬 واتس‌اپ: wa.me/97145701100\n🕐 دفتر: دوشنبه تا جمعه ۹ تا ۱۸ به وقت خلیج (UTC+4)\n📍 دفتر ۲۷۰۳، برج Aspect، بیزینس‌بی، دبی، امارات\n\n🚨 برای موارد اضطراری کلمه <b>emergency</b> را تایپ کنید.",
        "lang_picker": "🌐 <b>لطفاً زبان مورد نظر خود را انتخاب کنید / Choose your language:</b>",
    },
    "ar": {
        "welcome": "✨ <b>مرحباً بكم في زينوفكس</b>\n━━━━━━━━━━━━━━━━━━━━━━━\nالذكاء الاصطناعي والتقنية الرقمية · دبي\n\nالذكاء الاصطناعي، الحوسبة وتقنية المعلومات، الويب والتطبيقات،\nالأتمتة الذكية، البيانات والتحليلات، الرسوم ثلاثية الأبعاد.\n\nكيف يمكننا مساعدتك اليوم؟",
        "help": "📖 <b>دليل المساعدة</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n🚀 <b>أوامر سريعة</b>\n  /start  — فتح القائمة الرئيسية\n  /lang   — تغيير اللغة\n  /prices — أسعار المنتجات\n  /support — الدعم الفني\n  /quote — طلب عرض سعر\n  /contact — معلومات الاتصال\n  /help — صفحة المساعدة\n\n💡 يمكنك أيضاً إرسال أي سؤال مباشرة\nوسأوجهه إلى القسم المناسب.\n\n🆘 للطوارئ، اكتب فقط <b>emergency</b>.",
        "clarification": "عذراً، لم أتمكن من فهم طلبك بالكامل. هل يمكنك إعادة صياغة طلبك أو توضيح ما تحتاجه؟",
        "guard_rejected": "⚠️ تم رفض هذه الرسالة لأنها تحتوي على محتوى غير مسموح به. إذا كان لديك سؤال حقيقي، يرجى إعادة صياغة الرسالة.",
        "no_knowledge": "عذراً، لا تتوفر لدي معلومات كافية حول هذا الموضوع في قاعدة بياناتنا. هل يمكنني مساعدتك في شيء آخر يتعلق بمنتجاتنا أو خدماتنا؟",
        "pricing": "💰 <b>المنتجات والأسعار</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nيُحدَّد سعر كل مشروع في عرض رسمي بعد دراسة نطاق العمل.\n\nأخبرنا بالخدمة (مثل <b>روبوت محادثة ذكي</b>، <b>موقع إلكتروني</b>، <b>أتمتة</b>، <b>لوحة بيانات</b>) ونطاق العمل والجدول الزمني — وسيُعدّ فريقنا العرض.",
        "support": "🛠️ <b>الدعم الفني</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nاشرح مشكلتك وسأربطك بالفريق المناسب.\n\nللحالات الطارئة، اكتب <b>emergency</b>.",
        "quote": "📋 <b>طلب عرض سعر</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nيرجى تزويدنا بـ:\n• الخدمة (الذكاء الاصطناعي، الحوسبة وتقنية المعلومات، الويب والتطبيقات، الأتمتة، البيانات، الرسوم ثلاثية الأبعاد)\n• ما الذي تريد بناءه ولمن\n• اللغات والتكاملات والجدول الزمني\n• اسم الشركة وبيانات التواصل\n\nسيُعدّ فريقنا العرض ويعتمده أحد المديرين.",
        "contact": "📞 <b>تواصل معنا</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n📧 البريد الإلكتروني: {email}\n📞 الهاتف: +971 4570 1100\n💬 واتساب: wa.me/97145701100\n🕐 المكتب: الاثنين–الجمعة 9:00–18:00 بتوقيت الخليج (UTC+4)\n📍 مكتب 2703، برج أسبكت، الخليج التجاري، دبي، الإمارات\n\n🚨 للطوارئ، اكتب <b>emergency</b>",
        "lang_picker": "🌐 <b>اختر لغتك / Choose your language:</b>",
    },
    "es": {
        "welcome": "✨ <b>Bienvenido a Zenovix</b>\n━━━━━━━━━━━━━━━━━━━━━━━\nInteligencia artificial · Nube e ICT · Web y móvil · Automatización · Datos · Animación 3D.\n\n¿Cómo podemos ayudarle hoy?",
        "help": "📖 <b>Guía de Ayuda</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n🚀 <b>Comandos Rápidos</b>\n  /start  — Abrir menú principal\n  /lang   — Cambiar idioma\n  /prices — Precios de productos\n  /support — Soporte técnico\n  /quote — Solicitar cotización\n  /contact — Información de contacto\n  /help — Esta página de ayuda",
        "clarification": "Lo siento, no pude entender completamente su solicitud. ¿Podría reformular o aclarar lo que necesita?",
        "guard_rejected": "⚠️ Este mensaje fue rechazado porque contiene contenido no permitido.",
        "no_knowledge": "Lo siento, no tengo suficiente información sobre este tema en nuestra base de datos.",
        "pricing": "💰 <b>Productos y Precios</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nCada proyecto se cotiza en una propuesta formal. Indique el servicio, el alcance y su plazo.",
        "support": "🛠️ <b>Soporte Técnico</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nDescriba su problema y lo conectaremos con el equipo adecuado.",
        "quote": "📋 <b>Solicitar Cotización</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nIndique el servicio, qué quiere construir, idiomas e integraciones y su plazo.",
        "contact": "📞 <b>Contáctenos</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n📧 Email: {email}",
        "lang_picker": "🌐 <b>Elija su idioma / Choose your language:</b>",
    },
    "fr": {
        "welcome": "✨ <b>Bienvenue chez Zenovix</b>\n━━━━━━━━━━━━━━━━━━━━━━━\nIntelligence artificielle · Cloud et ICT · Web et mobile · Automatisation · Données · Animation 3D.\n\nComment pouvons-nous vous aider aujourd'hui ?",
        "help": "📖 <b>Guide d'Aide</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n🚀 <b>Commandes Rapides</b>\n  /start  — Menu principal\n  /lang   — Changer de langue\n  /prices — Tarifs produits\n  /support — Support technique\n  /quote — Demander un devis\n  /contact — Informations de contact\n  /help — Cette page d'aide",
        "clarification": "Désolé, je n'ai pas compris complètement votre demande. Pourriez-vous reformuler ?",
        "guard_rejected": "⚠️ Ce message a été rejeté car il contient du contenu interdit.",
        "no_knowledge": "Désolé, je n'ai pas assez d'informations sur ce sujet dans notre base de données.",
        "pricing": "💰 <b>Produits et Tarifs</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nChaque projet est chiffré dans une proposition formelle. Indiquez le service, le périmètre et votre délai.",
        "support": "🛠️ <b>Support Technique</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nDécrivez votre problème.",
        "quote": "📋 <b>Demande de Devis</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nIndiquez le service, ce que vous voulez construire, les langues, les intégrations et votre délai.",
        "contact": "📞 <b>Contactez-nous</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n📧 Email: {email}",
        "lang_picker": "🌐 <b>Choisissez votre langue / Choose your language:</b>",
    },
    "de": {
        "welcome": "✨ <b>Willkommen bei Zenovix</b>\n━━━━━━━━━━━━━━━━━━━━━━━\nKünstliche Intelligenz · Cloud und ICT · Web und Mobile · Automatisierung · Daten · 3D-Animation.\n\nWie können wir Ihnen heute helfen?",
        "help": "📖 <b>Hilfe-Leitfaden</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n🚀 <b>Schnellbefehle</b>\n  /start  — Hauptmenü öffnen\n  /lang   — Sprache ändern\n  /prices — Produktpreise\n  /support — Technischer Support\n  /quote — Angebot anfordern\n  /contact — Kontaktinformationen\n  /help — Diese Hilfe-Seite",
        "clarification": "Entschuldigung, ich konnte Ihre Anfrage nicht vollständig verstehen.",
        "guard_rejected": "⚠️ Diese Nachricht wurde abgelehnt, da sie nicht erlaubte Inhalte enthält.",
        "no_knowledge": "Entschuldigung, ich habe nicht genügend Informationen über dieses Thema.",
        "pricing": "💰 <b>Produkte und Preise</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nJedes Projekt wird in einem formellen Angebot kalkuliert. Nennen Sie Leistung, Umfang und Zeitrahmen.",
        "support": "🛠️ <b>Technischer Support</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nBeschreiben Sie Ihr Problem.",
        "quote": "📋 <b>Angebot anfordern</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nBitte nennen Sie Leistung, Vorhaben, Sprachen, Integrationen und Zeitrahmen.",
        "contact": "📞 <b>Kontaktieren Sie uns</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n📧 Email: {email}",
        "lang_picker": "🌐 <b>Wählen Sie Ihre Sprache / Choose your language:</b>",
    },
    "tr": {
        "welcome": "✨ <b>Zenovix'e Hoş Geldiniz</b>\n━━━━━━━━━━━━━━━━━━━━━━━\nYapay zeka · Bulut ve ICT · Web ve mobil · Otomasyon · Veri · 3D animasyon.\n\nBugün size nasıl yardımcı olabiliriz?",
        "help": "📖 <b>Yardım Rehberi</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n🚀 <b>Hızlı Komutlar</b>\n  /start  — Ana menüyü aç\n  /lang   — Dil değiştir\n  /prices — Ürün fiyatları\n  /support — Teknik destek\n  /quote — Teklif iste\n  /contact — İletişim bilgileri\n  /help — Bu yardım sayfası",
        "clarification": "Üzgünüm, isteğinizi tam olarak anlayamadım. Lütfen yeniden ifade eder misiniz?",
        "guard_rejected": "⚠️ Bu mesaj izin verilmeyen içerik içerdiği için reddedildi.",
        "no_knowledge": "Üzgünüm, bu konu hakkında veritabanımızda yeterli bilgi bulunmamaktadır.",
        "pricing": "💰 <b>Ürünler ve Fiyatlar</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nHer proje resmi teklifle fiyatlandırılır. Hizmeti, kapsamı ve zaman planınızı belirtin.",
        "support": "🛠️ <b>Teknik Destek</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nSorununuzu açıklayın, doğru ekiple iletişime geçelim.",
        "quote": "📋 <b>Teklif İste</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nLütfen hizmeti, ne inşa etmek istediğinizi, dilleri, entegrasyonları ve zaman planınızı belirtin.",
        "contact": "📞 <b>Bize Ulaşın</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n📧 E-posta: {email}",
        "lang_picker": "🌐 <b>Dilinizi seçin / Choose your language:</b>",
    },
    "ru": {
        "welcome": "✨ <b>Добро пожаловать в Zenovix</b>\n━━━━━━━━━━━━━━━━━━━━━━━\nИскусственный интеллект · Облако и ICT · Веб и мобильные · Автоматизация · Данные · 3D-анимация.\n\nЧем мы можем вам помочь сегодня?",
        "help": "📖 <b>Руководство</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n🚀 <b>Команды</b>\n  /start  — Главное меню\n  /lang   — Сменить язык\n  /prices — Цены на продукцию\n  /support — Техническая поддержка\n  /quote — Запросить расчет\n  /contact — Контакты\n  /help — Помощь",
        "clarification": "Извините, не удалось понять ваш запрос. Пожалуйста, уточните детали.",
        "guard_rejected": "⚠️ Сообщение отклонено, так как содержит недопустимый контент.",
        "no_knowledge": "К сожалению, в нашей базе данных недостаточно информации по этой теме.",
        "pricing": "💰 <b>Продукция и цены</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nКаждый проект оценивается в официальном предложении. Укажите услугу, объём и сроки.",
        "support": "🛠️ <b>Техническая поддержка</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nОпишите вашу проблему.",
        "quote": "📋 <b>Запрос расчета</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nУкажите услугу, что вы хотите создать, языки, интеграции и сроки.",
        "contact": "📞 <b>Контакты</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n📧 Email: {email}",
        "lang_picker": "🌐 <b>Выберите язык / Choose your language:</b>",
    },
}

BUTTONS: dict[str, dict[str, str]] = {
    "en": {
        "prices": "💰 Products & Pricing",
        "quote": "📋 Request Quote",
        "support": "🛠 Technical Support",
        "contact": "📞 Contact Us",
        "help": "❓ Help",
        "lang": "🌐 Language / زبان",
    },
    "fa": {
        "prices": "💰 محصولات و قیمت‌ها",
        "quote": "📋 درخواست پیش‌فاکتور",
        "support": "🛠 پشتیبانی فنی",
        "contact": "📞 اطلاعات تماس",
        "help": "❓ راهنما",
        "lang": "🌐 تغییر زبان / Language",
    },
    "ar": {
        "prices": "💰 المنتجات والأسعار",
        "quote": "📋 طلب عرض سعر",
        "support": "🛠 الدعم الفني",
        "contact": "📞 تواصل معنا",
        "help": "❓ المساعدة",
        "lang": "🌐 تغيير اللغة / Language",
    },
    "es": {
        "prices": "💰 Productos y Precios",
        "quote": "📋 Solicitar Cotización",
        "support": "🛠 Soporte Técnico",
        "contact": "📞 Contacto",
        "help": "❓ Ayuda",
        "lang": "🌐 Idioma / Language",
    },
    "fr": {
        "prices": "💰 Produits & Tarifs",
        "quote": "📋 Demande de Devis",
        "support": "🛠 Support Technique",
        "contact": "📞 Contact",
        "help": "❓ Aide",
        "lang": "🌐 Langue / Language",
    },
    "de": {
        "prices": "💰 Produkte & Preise",
        "quote": "📋 Angebot anfordern",
        "support": "🛠 Technischer Support",
        "contact": "📞 Kontakt",
        "help": "❓ Hilfe",
        "lang": "🌐 Sprache / Language",
    },
    "tr": {
        "prices": "💰 Ürünler & Fiyatlar",
        "quote": "📋 Teklif İste",
        "support": "🛠 Teknik Destek",
        "contact": "📞 İletişim",
        "help": "❓ Yardım",
        "lang": "🌐 Dil / Language",
    },
    "ru": {
        "prices": "💰 Товары и цены",
        "quote": "📋 Запрос КП",
        "support": "🛠 Поддержка",
        "contact": "📞 Контакты",
        "help": "❓ Помощь",
        "lang": "🌐 Язык / Language",
    },
}


def get_text(lang: str, key: str, **kwargs: Any) -> str:
    """Get translated text for a given language and key.

    Falls back to English if the language is not found.
    """
    code = (lang or "en").lower().strip()
    lang_dict = MENUS.get(code, MENUS.get("en", {}))
    text = lang_dict.get(key, MENUS["en"].get(key, ""))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text


def get_button_text(lang: str, key: str) -> str:
    """Get localized button label."""
    code = (lang or "en").lower().strip()
    btn_dict = BUTTONS.get(code, BUTTONS.get("en", {}))
    return btn_dict.get(key, BUTTONS["en"].get(key, key))


# ---------------------------------------------------------------------------
# 1.4.0 — section sub-menus, order flow and contact details. English is the
# reference; every other language is a display layer with English fallback.
# ---------------------------------------------------------------------------

_BUTTONS_140: dict[str, dict[str, str]] = {
    "en": {
        "shop": "🛒 Products & Prices",
        "my_requests": "🧾 My requests",
        "back": "◀ Back",
        "talk_sales": "💬 Talk to sales",
        "new_ticket": "🎫 New support ticket",
        "faq": "📖 FAQ",
        "emergency": "🚨 Emergency",
        "call": "📞 Call / WhatsApp",
        "email": "✉️ E-mail",
        "location": "📍 Location",
        "hours": "🕘 Office hours",
    },
    "fa": {
        "shop": "🛒 محصولات و قیمت‌ها",
        "my_requests": "🧾 درخواست‌های من",
        "back": "◀ بازگشت",
        "talk_sales": "💬 گفتگو با فروش",
        "new_ticket": "🎫 تیکت پشتیبانی جدید",
        "faq": "📖 سوالات متداول",
        "emergency": "🚨 اضطراری",
        "call": "📞 تماس / واتساپ",
        "email": "✉️ ایمیل",
        "location": "📍 آدرس",
        "hours": "🕘 ساعات کاری",
    },
    "ar": {
        "shop": "🛒 المنتجات والأسعار",
        "my_requests": "🧾 طلباتي",
        "back": "◀ رجوع",
        "talk_sales": "💬 التحدث مع المبيعات",
        "new_ticket": "🎫 تذكرة دعم جديدة",
        "faq": "📖 الأسئلة الشائعة",
        "emergency": "🚨 طوارئ",
        "call": "📞 اتصال / واتساب",
        "email": "✉️ البريد الإلكتروني",
        "location": "📍 الموقع",
        "hours": "🕘 ساعات العمل",
    },
    "es": {
        "shop": "🛒 Productos y precios",
        "my_requests": "🧾 Mis solicitudes",
        "back": "◀ Atrás",
        "talk_sales": "💬 Hablar con ventas",
        "new_ticket": "🎫 Nuevo ticket",
        "faq": "📖 Preguntas frecuentes",
        "emergency": "🚨 Emergencia",
        "call": "📞 Llamar / WhatsApp",
        "email": "✉️ Correo",
        "location": "📍 Ubicación",
        "hours": "🕘 Horario",
    },
    "fr": {
        "shop": "🛒 Produits & prix",
        "my_requests": "🧾 Mes demandes",
        "back": "◀ Retour",
        "talk_sales": "💬 Parler aux ventes",
        "new_ticket": "🎫 Nouveau ticket",
        "faq": "📖 FAQ",
        "emergency": "🚨 Urgence",
        "call": "📞 Appel / WhatsApp",
        "email": "✉️ E-mail",
        "location": "📍 Adresse",
        "hours": "🕘 Horaires",
    },
    "de": {
        "shop": "🛒 Produkte & Preise",
        "my_requests": "🧾 Meine Anfragen",
        "back": "◀ Zurück",
        "talk_sales": "💬 Mit dem Vertrieb sprechen",
        "new_ticket": "🎫 Neues Support-Ticket",
        "faq": "📖 FAQ",
        "emergency": "🚨 Notfall",
        "call": "📞 Anruf / WhatsApp",
        "email": "✉️ E-Mail",
        "location": "📍 Standort",
        "hours": "🕘 Öffnungszeiten",
    },
    "tr": {
        "shop": "🛒 Ürünler ve fiyatlar",
        "my_requests": "🧾 Taleplerim",
        "back": "◀ Geri",
        "talk_sales": "💬 Satışla görüş",
        "new_ticket": "🎫 Yeni destek talebi",
        "faq": "📖 SSS",
        "emergency": "🚨 Acil durum",
        "call": "📞 Ara / WhatsApp",
        "email": "✉️ E-posta",
        "location": "📍 Konum",
        "hours": "🕘 Çalışma saatleri",
    },
    "ru": {
        "shop": "🛒 Продукты и цены",
        "my_requests": "🧾 Мои запросы",
        "back": "◀ Назад",
        "talk_sales": "💬 Связаться с отделом продаж",
        "new_ticket": "🎫 Новое обращение",
        "faq": "📖 Вопросы и ответы",
        "emergency": "🚨 Экстренный случай",
        "call": "📞 Звонок / WhatsApp",
        "email": "✉️ E-mail",
        "location": "📍 Адрес",
        "hours": "🕘 Часы работы",
    },
}

_MENUS_140: dict[str, dict[str, str]] = {
    "en": {
        "waiting_manager": "Your request has been passed to a manager for confirmation. We will follow up as soon as it is reviewed.",
        "talk_sales": "Tell me what you need — the service, what you want to build and your timeline — and our team will reply with a formal proposal. You can also pick a service from the menu and send a request in three taps.",
        "new_ticket": "Describe the issue in one message (what happened, where, since when). A ticket is opened and the right team is notified. Safety cases are escalated immediately.",
        "faq": "Common questions:\n- Prices: every project is scoped and quoted in a formal proposal after a manager confirms.\n- Services: AI, cloud and ICT, web and mobile (bilingual EN/AR), intelligent automation, data and analytics, animation and 3D.\n- Process: strategy first, then design, engineering and launch with a team that stays after go-live.\n- Payment: never taken in this chat.\nAsk anything else in your own words.",
        "contact_call_title": "Phone & WhatsApp",
        "contact_email_title": "E-mail",
        "contact_location_title": "Office",
        "contact_hours_title": "Office hours",
        "contact_missing": "This detail is not published yet. Please use the other contact options.",
    },
    "fa": {
        "waiting_manager": "درخواست شما برای تأیید به مدیر ارجاع شد. به\u200cمحض بررسی، به شما اطلاع می\u200cدهیم.",
        "talk_sales": "نیازتان را بگویید — خدمت موردنظر، چیزی که می‌خواهید ساخته شود و زمان‌بندی — تا تیم ما با پیشنهاد رسمی پاسخ دهد. می‌توانید از منو هم خدمت را انتخاب کنید و با سه لمس درخواست بفرستید.",
        "new_ticket": "مشکل را در یک پیام توضیح دهید (چه شده، کجا، از کی). تیکت باز می‌شود و تیم مربوطه مطلع می‌شود. موارد ایمنی فوراً ارجاع می‌شوند.",
        "faq": "سوالات متداول:\n- قیمت: هر پروژه پس از بررسی دامنهٔ کار و تأیید مدیر، در پیشنهاد رسمی قیمت‌گذاری می‌شود.\n- خدمات: هوش مصنوعی، کلاود و ICT، وب و موبایل (دوزبانهٔ انگلیسی/عربی)، اتوماسیون هوشمند، داده و تحلیل، انیمیشن و سه‌بعدی.\n- روند کار: اول استراتژی، بعد طراحی، مهندسی و راه‌اندازی؛ تیم بعد از تحویل هم کنار شماست.\n- پرداخت: هرگز در این گفتگو انجام نمی‌شود.\nهر سوال دیگری دارید به زبان خودتان بپرسید.",
        "contact_call_title": "تلفن و واتساپ",
        "contact_email_title": "ایمیل",
        "contact_location_title": "دفتر",
        "contact_hours_title": "ساعات کاری",
        "contact_missing": "این مورد هنوز منتشر نشده است. لطفاً از گزینه‌های دیگر تماس استفاده کنید.",
    },
    "ar": {
        "waiting_manager": "تمت إحالة طلبك إلى المدير للتأكيد وسنعود إليك فور مراجعته.",
        "talk_sales": "أخبرنا بما تحتاجه — الخدمة وما تريد بناءه وجدولك الزمني — وسيرد فريقنا بعرض رسمي. يمكنك أيضاً اختيار خدمة من القائمة وإرسال طلب بثلاث نقرات.",
        "new_ticket": "صف المشكلة في رسالة واحدة (ماذا حدث، أين، منذ متى). تُفتح تذكرة ويُبلَّغ الفريق المختص. حالات السلامة تُصعَّد فوراً.",
        "faq": "الأسئلة الشائعة:\n- الأسعار: يُسعَّر كل مشروع في عرض رسمي بعد دراسة نطاق العمل وتأكيد المدير.\n- الخدمات: الذكاء الاصطناعي، الحوسبة وتقنية المعلومات، الويب والتطبيقات (عربي/إنجليزي)، الأتمتة الذكية، البيانات والتحليلات، الرسوم ثلاثية الأبعاد.\n- طريقة العمل: الاستراتيجية أولاً، ثم التصميم والهندسة والإطلاق مع فريق يبقى معك بعد التسليم.\n- الدفع: لا يتم أبداً عبر هذه المحادثة.\nاسأل عن أي شيء آخر بكلماتك.",
        "contact_call_title": "الهاتف وواتساب",
        "contact_email_title": "البريد الإلكتروني",
        "contact_location_title": "المكتب",
        "contact_hours_title": "ساعات العمل",
        "contact_missing": "لم يُنشر هذا البيان بعد. يرجى استخدام خيارات التواصل الأخرى.",
    },
    "es": {
        "waiting_manager": "Su solicitud se ha enviado a un gerente para su confirmación. Le responderemos en cuanto se revise.",
        "talk_sales": "Díganos qué necesita — el servicio, qué quiere construir y su plazo — y nuestro equipo responderá con una propuesta formal. También puede elegir un servicio del menú y enviar una solicitud en tres toques.",
        "new_ticket": "Describa el problema en un mensaje (qué pasó, dónde, desde cuándo). Se abre un ticket y se avisa al equipo correcto.",
        "faq": "Preguntas frecuentes:\n- Precios: cada proyecto se cotiza en una propuesta formal tras la confirmación de un gerente.\n- Servicios: IA, nube e ICT, web y móvil, automatización, datos y análisis, animación 3D.\n- Proceso: primero la estrategia, luego diseño, ingeniería y lanzamiento.\n- Pago: nunca en este chat.",
        "contact_call_title": "Teléfono y WhatsApp",
        "contact_email_title": "Correo",
        "contact_location_title": "Oficina",
        "contact_hours_title": "Horario",
        "contact_missing": "Este dato aún no está publicado. Use las otras opciones de contacto.",
    },
    "fr": {
        "waiting_manager": "Votre demande a été transmise à un responsable pour confirmation. Nous revenons vers vous dès qu'elle est examinée.",
        "talk_sales": "Dites-nous ce qu'il vous faut — le service, ce que vous voulez construire et votre délai — et notre équipe répondra par une proposition formelle. Vous pouvez aussi choisir un service dans le menu et envoyer une demande en trois touches.",
        "new_ticket": "Décrivez le problème en un message (quoi, où, depuis quand). Un ticket est ouvert et l'équipe concernée est prévenue.",
        "faq": "Questions fréquentes :\n- Prix : chaque projet est chiffré dans une proposition formelle, après validation d'un responsable.\n- Services : IA, cloud et ICT, web et mobile, automatisation, données et analyses, animation 3D.\n- Méthode : la stratégie d'abord, puis design, ingénierie et lancement.\n- Paiement : jamais dans cette conversation.",
        "contact_call_title": "Téléphone & WhatsApp",
        "contact_email_title": "E-mail",
        "contact_location_title": "Bureau",
        "contact_hours_title": "Horaires",
        "contact_missing": "Cette information n'est pas encore publiée. Utilisez les autres options de contact.",
    },
    "de": {
        "waiting_manager": "Ihre Anfrage wurde zur Bestätigung an einen Manager weitergeleitet. Wir melden uns, sobald sie geprüft ist.",
        "talk_sales": "Sagen Sie uns, was Sie brauchen — Leistung, Vorhaben und Zeitrahmen — und unser Team antwortet mit einem formellen Angebot. Sie können auch eine Leistung im Menü wählen und mit drei Tipps eine Anfrage senden.",
        "new_ticket": "Beschreiben Sie das Problem in einer Nachricht (was, wo, seit wann). Ein Ticket wird eröffnet und das zuständige Team informiert.",
        "faq": "Häufige Fragen:\n- Preise: jedes Projekt wird in einem formellen Angebot nach Freigabe eines Managers kalkuliert.\n- Leistungen: KI, Cloud und ICT, Web und Mobile, Automatisierung, Daten und Analysen, 3D-Animation.\n- Vorgehen: erst Strategie, dann Design, Engineering und Launch.\n- Zahlung: nie in diesem Chat.",
        "contact_call_title": "Telefon & WhatsApp",
        "contact_email_title": "E-Mail",
        "contact_location_title": "Büro",
        "contact_hours_title": "Öffnungszeiten",
        "contact_missing": "Diese Angabe ist noch nicht veröffentlicht. Bitte nutzen Sie die anderen Kontaktwege.",
    },
    "tr": {
        "waiting_manager": "Talebiniz onay için bir yöneticiye iletildi. İncelenir incelenmez size döneceğiz.",
        "talk_sales": "Neye ihtiyacınız olduğunu söyleyin — hizmet, ne inşa etmek istediğiniz ve zaman planınız — ekibimiz resmi teklifle yanıt versin. Menüden bir hizmet seçip üç dokunuşla da talep gönderebilirsiniz.",
        "new_ticket": "Sorunu tek mesajda anlatın (ne oldu, nerede, ne zamandan beri). Bir talep açılır ve ilgili ekip bilgilendirilir.",
        "faq": "Sık sorulanlar:\n- Fiyatlar: her proje, yönetici onayından sonra resmi teklifle fiyatlandırılır.\n- Hizmetler: yapay zeka, bulut ve ICT, web ve mobil, otomasyon, veri ve analitik, 3D animasyon.\n- Süreç: önce strateji, sonra tasarım, mühendislik ve lansman.\n- Ödeme: bu sohbette asla alınmaz.",
        "contact_call_title": "Telefon ve WhatsApp",
        "contact_email_title": "E-posta",
        "contact_location_title": "Ofis",
        "contact_hours_title": "Çalışma saatleri",
        "contact_missing": "Bu bilgi henüz yayımlanmadı. Lütfen diğer iletişim seçeneklerini kullanın.",
    },
    "ru": {
        "waiting_manager": "Ваш запрос передан менеджеру на подтверждение. Мы свяжемся с вами сразу после проверки.",
        "talk_sales": "Опишите, что вам нужно — услугу, что вы хотите создать и сроки — и наша команда ответит официальным предложением. Можно также выбрать услугу в меню и отправить запрос в три касания.",
        "new_ticket": "Опишите проблему одним сообщением (что, где, с какого момента). Обращение будет открыто, ответственная команда уведомлена.",
        "faq": "Частые вопросы:\n- Цены: каждый проект оценивается в официальном предложении после подтверждения менеджера.\n- Услуги: ИИ, облако и ICT, веб и мобильные, автоматизация, данные и аналитика, 3D-анимация.\n- Процесс: сначала стратегия, затем дизайн, разработка и запуск.\n- Оплата: никогда не принимается в этом чате.",
        "contact_call_title": "Телефон и WhatsApp",
        "contact_email_title": "E-mail",
        "contact_location_title": "Офис",
        "contact_hours_title": "Часы работы",
        "contact_missing": "Эти данные ещё не опубликованы. Используйте другие способы связи.",
    },
}

for _code, _items in _BUTTONS_140.items():
    BUTTONS.setdefault(_code, {}).update(_items)
for _code, _items in _MENUS_140.items():
    MENUS.setdefault(_code, {}).update(_items)
