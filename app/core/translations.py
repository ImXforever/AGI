"""Complete UI translations for all supported languages with English default."""

from __future__ import annotations

from typing import Any

MENUS: dict[str, dict[str, str]] = {
    "en": {
        "welcome": "🏗️ <b>Welcome to ZENOVIX DIGITAL</b>\n━━━━━━━━━━━━━━━━━━━━━━━\nYour trusted business & AI operations partner.\n\nWe provide industrial lubricants, specialty products,\nand automated customer operations.\n\nHow can we help you today?",
        "help": "📖 <b>Help Guide</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n🚀 <b>Quick Commands</b>\n  /start  — Open main menu\n  /lang   — Change language\n  /prices — Product pricing\n  /support — Technical support\n  /quote — Request a quote\n  /contact — Contact information\n  /help — This help page\n\n💡 You can also send any question directly\nand I'll route it to the right specialist.\n\n🆘 For emergencies, just type <b>emergency</b>.",
        "clarification": "Sorry, I couldn't fully understand your request. Could you please rephrase or clarify what you need?",
        "guard_rejected": "⚠️ This message was rejected because it contains disallowed content. If you have a genuine question, please rephrase it.",
        "no_knowledge": "I'm sorry, I don't have enough information about this topic in our database. Can I help you with something else related to our products or services?",
        "pricing": "💰 <b>Products &amp; Pricing</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nSend a product name or SKU code to search.\n\nExample: <code>PET-001</code> or <b>drilling fluid</b>",
        "support": "🛠️ <b>Technical Support</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nDescribe your issue and I'll connect you with the right team.\n\nFor urgent issues, type <b>emergency</b>.",
        "quote": "📋 <b>Request a Quote</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nPlease provide:\n• Product name or code\n• Quantity needed\n• Delivery location\n\nOur team will prepare a quote promptly.",
        "contact": "📞 <b>Contact Us</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n📧 Email: {email}\n🕐 Hours: Sun–Thu 8AM–5PM\n📍 UAE / Global\n\n🚨 For urgent matters, type <b>emergency</b>",
        "lang_picker": "🌐 <b>Choose your language / لطفاً زبان خود را انتخاب کنید:</b>",
    },
    "fa": {
        "welcome": "🏗️ <b>به ZENOVIX DIGITAL خوش آمدید</b>\n━━━━━━━━━━━━━━━━━━━━━━━\nهمراه هوشمند و ارائه‌دهنده خدمات تخصصی و صنعتی.\n\nمن می‌توانم در پاسخ به سوالات فنی، استعلام قیمت، صدور پیش‌فاکتور، ثبت تیکت پشتیبانی و هماهنگی سفارش‌ها به شما کمک کنم.\n\nامروز چطور می‌توانم به شما کمک کنم؟",
        "help": "📖 <b>راهنمای دستورات و استفاده</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n🚀 <b>دستورات سریع:</b>\n  /start  — باز کردن منوی اصلی\n  /lang   — تغییر زبان سیستم\n  /prices — لیست قیمت و محصولات\n  /support — پشتیبانی فنی\n  /quote — درخواست پیش‌فاکتور\n  /contact — اطلاعات تماس\n  /help — صفحه راهنما\n\n💡 همچنین می‌توانید هر سوالی دارید را مستقیماً ارسال کنید تا پاسخ مناسب دریافت نمایید.\n\n🆘 برای موارد اضطراری کلمه <b>emergency</b> را ارسال کنید.",
        "clarification": "متأسفانه متوجه درخواست شما نشدم. لطفاً سوال یا درخواست خود را دقیق‌تر بیان کنید.",
        "guard_rejected": "⚠️ پیام ارسالی به دلیل محتوای غیرمجاز پردازش نشد. در صورت وجود سوال مرتبط، لطفاً پیام خود را بازنویسی کنید.",
        "no_knowledge": "متأسفانه اطلاعات کافی در این زمینه در پایگاه دانش موجود نیست. آیا می‌توانم در مورد محصولات یا خدمات دیگر به شما کمک کنم؟",
        "pricing": "💰 <b>محصولات و قیمت‌ها</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nنام محصول یا کد کالا را برای جستجو ارسال کنید.\n\nمثال: <code>PET-001</code> یا <b>روغن صنعتی</b>",
        "support": "🛠️ <b>پشتیبانی فنی</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nمشکل یا سوال فنی خود را شرح دهید تا بررسی شود.\n\nبرای موارد فوری کلمه <b>emergency</b> را تایپ کنید.",
        "quote": "📋 <b>درخواست استعلام / پیش‌فاکتور</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nلطفاً موارد زیر را مشخص فرمایید:\n• نام یا کد محصول درخواستی\n• تعداد یا حجم مورد نیاز\n• محل تحویل",
        "contact": "📞 <b>اطلاعات تماس</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n📧 ایمیل: {email}\n🕐 ساعات کاری: شنبه تا چهارشنبه ۸ الی ۱۷\n\n🚨 برای موارد اضطراری کلمه <b>emergency</b> را تایپ کنید.",
        "lang_picker": "🌐 <b>لطفاً زبان مورد نظر خود را انتخاب کنید / Choose your language:</b>",
    },
    "ar": {
        "welcome": "🏗️ <b>مرحباً بكم في ZENOVIX DIGITAL</b>\n━━━━━━━━━━━━━━━━━━━━━━━\nشريككم الموثوق في المنتجات والخدمات الصناعية.\n\nنورد زيوت التشحيم الصناعية، وسوائل الحفر،\nوالمواد الكيميائية، والخدمات التشغيلية.\n\nكيف يمكننا مساعدتك اليوم؟",
        "help": "📖 <b>دليل المساعدة</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n🚀 <b>أوامر سريعة</b>\n  /start  — فتح القائمة الرئيسية\n  /lang   — تغيير اللغة\n  /prices — أسعار المنتجات\n  /support — الدعم الفني\n  /quote — طلب عرض سعر\n  /contact — معلومات الاتصال\n  /help — صفحة المساعدة\n\n💡 يمكنك أيضاً إرسال أي سؤال مباشرة\nوسأوجهه إلى القسم المناسب.\n\n🆘 للطوارئ، اكتب فقط <b>emergency</b>.",
        "clarification": "عذراً، لم أتمكن من فهم طلبك بالكامل. هل يمكنك إعادة صياغة طلبك أو توضيح ما تحتاجه؟",
        "guard_rejected": "⚠️ تم رفض هذه الرسالة لأنها تحتوي على محتوى غير مسموح به. إذا كان لديك سؤال حقيقي، يرجى إعادة صياغة الرسالة.",
        "no_knowledge": "عذراً، لا تتوفر لدي معلومات كافية حول هذا الموضوع في قاعدة بياناتنا. هل يمكنني مساعدتك في شيء آخر يتعلق بمنتجاتنا أو خدماتنا؟",
        "pricing": "💰 <b>المنتجات والأسعار</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nأرسل اسم المنتج أو رمز الصنف للبحث.\n\nمثال: <code>PET-001</code> أو <b>سوائل الحفر</b>",
        "support": "🛠️ <b>الدعم الفني</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nاشرح مشكلتك وسأربطك بالفريق المناسب.\n\nللحالات الطارئة، اكتب <b>emergency</b>.",
        "quote": "📋 <b>طلب عرض سعر</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nيرجى تزويدنا بـ:\n• اسم المنتج أو الكود\n• الكمية المطلوبة\n• موقع التوصيل\n\nسيقوم فريقنا بإعداد عرض سعر في أقرب وقت.",
        "contact": "📞 <b>تواصل معنا</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n📧 البريد الإلكتروني: {email}\n🕐 ساعات العمل: الأحد–الخميس 8 صباحاً–5 مساءً\n\n🚨 للطوارئ، اكتب <b>emergency</b>",
        "lang_picker": "🌐 <b>اختر لغتك / Choose your language:</b>",
    },
    "es": {
        "welcome": "🏗️ <b>Bienvenido a ZENOVIX DIGITAL</b>\n━━━━━━━━━━━━━━━━━━━━━━━\nSu socio de confianza en productos industriales y automatización.\n\n¿Cómo podemos ayudarle hoy?",
        "help": "📖 <b>Guía de Ayuda</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n🚀 <b>Comandos Rápidos</b>\n  /start  — Abrir menú principal\n  /lang   — Cambiar idioma\n  /prices — Precios de productos\n  /support — Soporte técnico\n  /quote — Solicitar cotización\n  /contact — Información de contacto\n  /help — Esta página de ayuda",
        "clarification": "Lo siento, no pude entender completamente su solicitud. ¿Podría reformular o aclarar lo que necesita?",
        "guard_rejected": "⚠️ Este mensaje fue rechazado porque contiene contenido no permitido.",
        "no_knowledge": "Lo siento, no tengo suficiente información sobre este tema en nuestra base de datos.",
        "pricing": "💰 <b>Productos y Precios</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nEnvíe un nombre de producto o código SKU para buscar.",
        "support": "🛠️ <b>Soporte Técnico</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nDescriba su problema y lo conectaremos con el equipo adecuado.",
        "quote": "📋 <b>Solicitar Cotización</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nPor favor proporcione nombre del producto, cantidad y ubicación.",
        "contact": "📞 <b>Contáctenos</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n📧 Email: {email}",
        "lang_picker": "🌐 <b>Elija su idioma / Choose your language:</b>",
    },
    "fr": {
        "welcome": "🏗️ <b>Bienvenue chez ZENOVIX DIGITAL</b>\n━━━━━━━━━━━━━━━━━━━━━━━\nVotre partenaire de confiance en opérations industrielles et IA.\n\nComment pouvons-nous vous aider aujourd'hui ?",
        "help": "📖 <b>Guide d'Aide</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n🚀 <b>Commandes Rapides</b>\n  /start  — Menu principal\n  /lang   — Changer de langue\n  /prices — Tarifs produits\n  /support — Support technique\n  /quote — Demander un devis\n  /contact — Informations de contact\n  /help — Cette page d'aide",
        "clarification": "Désolé, je n'ai pas compris complètement votre demande. Pourriez-vous reformuler ?",
        "guard_rejected": "⚠️ Ce message a été rejeté car il contient du contenu interdit.",
        "no_knowledge": "Désolé, je n'ai pas assez d'informations sur ce sujet dans notre base de données.",
        "pricing": "💰 <b>Produits et Tarifs</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nEnvoyez un nom de produit ou un code SKU.",
        "support": "🛠️ <b>Support Technique</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nDécrivez votre problème.",
        "quote": "📋 <b>Demande de Devis</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nVeuillez fournir le produit, la quantité et le lieu.",
        "contact": "📞 <b>Contactez-nous</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n📧 Email: {email}",
        "lang_picker": "🌐 <b>Choisissez votre langue / Choose your language:</b>",
    },
    "de": {
        "welcome": "🏗️ <b>Willkommen bei ZENOVIX DIGITAL</b>\n━━━━━━━━━━━━━━━━━━━━━━━\nIhr Partner für industrielle Lösungen und KI-Automatisierung.\n\nWie können wir Ihnen heute helfen?",
        "help": "📖 <b>Hilfe-Leitfaden</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n🚀 <b>Schnellbefehle</b>\n  /start  — Hauptmenü öffnen\n  /lang   — Sprache ändern\n  /prices — Produktpreise\n  /support — Technischer Support\n  /quote — Angebot anfordern\n  /contact — Kontaktinformationen\n  /help — Diese Hilfe-Seite",
        "clarification": "Entschuldigung, ich konnte Ihre Anfrage nicht vollständig verstehen.",
        "guard_rejected": "⚠️ Diese Nachricht wurde abgelehnt, da sie nicht erlaubte Inhalte enthält.",
        "no_knowledge": "Entschuldigung, ich habe nicht genügend Informationen über dieses Thema.",
        "pricing": "💰 <b>Produkte und Preise</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nSenden Sie einen Produktnamen oder SKU-Code.",
        "support": "🛠️ <b>Technischer Support</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nBeschreiben Sie Ihr Problem.",
        "quote": "📋 <b>Angebot anfordern</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nBitte geben Sie Produkt, Menge und Lieferort an.",
        "contact": "📞 <b>Kontaktieren Sie uns</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n📧 Email: {email}",
        "lang_picker": "🌐 <b>Wählen Sie Ihre Sprache / Choose your language:</b>",
    },
    "tr": {
        "welcome": "🏗️ <b>ZENOVIX DIGITAL'e Hoş Geldiniz</b>\n━━━━━━━━━━━━━━━━━━━━━━━\nGüvenilir endüstriyel çözümler ve yapay zeka operasyonları ortağınız.\n\nBugün size nasıl yardımcı olabiliriz?",
        "help": "📖 <b>Yardım Rehberi</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n🚀 <b>Hızlı Komutlar</b>\n  /start  — Ana menüyü aç\n  /lang   — Dil değiştir\n  /prices — Ürün fiyatları\n  /support — Teknik destek\n  /quote — Teklif iste\n  /contact — İletişim bilgileri\n  /help — Bu yardım sayfası",
        "clarification": "Üzgünüm, isteğinizi tam olarak anlayamadım. Lütfen yeniden ifade eder misiniz?",
        "guard_rejected": "⚠️ Bu mesaj izin verilmeyen içerik içerdiği için reddedildi.",
        "no_knowledge": "Üzgünüm, bu konu hakkında veritabanımızda yeterli bilgi bulunmamaktadır.",
        "pricing": "💰 <b>Ürünler ve Fiyatlar</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nAramak için ürün adı veya SKU kodu gönderin.",
        "support": "🛠️ <b>Teknik Destek</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nSorununuzu açıklayın, doğru ekiple iletişime geçelim.",
        "quote": "📋 <b>Teklif İste</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nLütfen ürün adı, miktar ve teslimat konumunu belirtin.",
        "contact": "📞 <b>Bize Ulaşın</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n📧 E-posta: {email}",
        "lang_picker": "🌐 <b>Dilinizi seçin / Choose your language:</b>",
    },
    "ru": {
        "welcome": "🏗️ <b>Добро пожаловать в ZENOVIX DIGITAL</b>\n━━━━━━━━━━━━━━━━━━━━━━━\nВаш надежный партнер по промышленным решениям и автоматизации.\n\nЧем мы можем вам помочь сегодня?",
        "help": "📖 <b>Руководство</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n🚀 <b>Команды</b>\n  /start  — Главное меню\n  /lang   — Сменить язык\n  /prices — Цены на продукцию\n  /support — Техническая поддержка\n  /quote — Запросить расчет\n  /contact — Контакты\n  /help — Помощь",
        "clarification": "Извините, не удалось понять ваш запрос. Пожалуйста, уточните детали.",
        "guard_rejected": "⚠️ Сообщение отклонено, так как содержит недопустимый контент.",
        "no_knowledge": "К сожалению, в нашей базе данных недостаточно информации по этой теме.",
        "pricing": "💰 <b>Продукция и цены</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nОтправьте название или SKU для поиска.",
        "support": "🛠️ <b>Техническая поддержка</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nОпишите вашу проблему.",
        "quote": "📋 <b>Запрос расчета</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nУкажите товар, количество и место доставки.",
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
