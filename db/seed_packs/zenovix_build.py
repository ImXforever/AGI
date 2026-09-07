#!/usr/bin/env python3
"""Build the Zenovix seed pack (db/seed/*.json) from the content of zenovix.ae.

Run from the repo root:  python3 db/seed_packs/zenovix_build.py

Facts come from https://zenovix.ae (crawled 2026-09-07). No prices, team
sizes or client counts are invented: every service is ``unit_price = 0``
(price on request) and the FAQ says "scoped in a formal proposal".
The EGL pack that shipped with 1.1.x–1.4.0 is kept in db/seed_packs/egl/.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "db" / "seed"
NS = uuid.UUID("2b1c5b0e-9a4f-5c7e-8d2a-7f3e6a1b9c0d")  # Zenovix seed namespace

COMPANY = "Zenovix"
EMAIL = "studio@zenovix.com"
PHONE = "+971 4570 1100"
WHATSAPP = "https://wa.me/97145701100"
ADDRESS = "Office 2703, Aspect Tower, Business Bay, Dubai, UAE"
SITE = "https://zenovix.ae"
HOURS_EN = "Mon–Fri 9:00–18:00 GST (UTC+4)"


def uid(kind: str, key: str) -> str:
    return str(uuid.uuid5(NS, f"{kind}:{key}"))


# ---------------------------------------------------------------------------
# 001 products (services) — codes 101–106, 8 languages
# ---------------------------------------------------------------------------

SERVICES = [
    {
        "code": "101",
        "sku": "ZX-SVC-AI",
        "name_en": "Artificial Intelligence",
        "title_en": "Custom models, computer vision and conversational AI trained on your data",
        "names": {
            "fa": "هوش مصنوعی",
            "ar": "الذكاء الاصطناعي",
            "tr": "Yapay Zeka",
            "de": "Künstliche Intelligenz",
            "fr": "Intelligence artificielle",
            "es": "Inteligencia artificial",
            "ru": "Искусственный интеллект",
        },
        "titles": {
            "fa": "مدل‌های اختصاصی، بینایی ماشین و هوش مصنوعی مکالمه‌ای آموزش‌دیده روی داده‌های شما",
            "ar": "نماذج مخصّصة ورؤية حاسوبية وذكاء اصطناعي حواري مدرّب على بياناتك",
            "tr": "Verilerinizle eğitilmiş özel modeller, bilgisayarlı görü ve diyalog yapay zekası",
            "de": "Individuelle Modelle, Computer Vision und Conversational AI auf Ihren Daten",
            "fr": "Modèles sur mesure, vision par ordinateur et IA conversationnelle entraînée sur vos données",
            "es": "Modelos a medida, visión por computador e IA conversacional entrenada con sus datos",
            "ru": "Кастомные модели, компьютерное зрение и диалоговый ИИ на ваших данных",
        },
        "name_ar": "الذكاء الاصطناعي",
        "description_en": (
            "Custom models, computer vision and conversational AI trained on your data and shipped "
            "production-ready. Typical deliverables: AI assistants and chatbots on your own knowledge, "
            "document understanding, image and video analysis, forecasting models, and integration "
            "into your existing systems. Every engagement is scoped and priced in a formal proposal."
        ),
        "description_ar": (
            "نماذج مخصّصة ورؤية حاسوبية وذكاء اصطناعي حواري مدرّب على بياناتك وجاهز للإنتاج. "
            "من أبرز المخرجات: مساعدون وروبوتات محادثة تعتمد على معرفتك، فهم المستندات، تحليل الصور "
            "والفيديو، نماذج التنبؤ، والتكامل مع أنظمتك الحالية. يُحدَّد نطاق كل مشروع وسعره في عرض رسمي."
        ),
        "specs": {
            "type": "service",
            "features": [
                "AI assistants and chatbots on your own data",
                "Computer vision (image and video analysis)",
                "Document understanding and extraction",
                "Forecasting and recommendation models",
                "Production deployment and monitoring",
            ],
            "quote_inputs": ["use case", "data available", "channels and integrations", "timeline"],
        },
        "image": "ai.jpg",
        "sort_order": 10,
    },
    {
        "code": "102",
        "sku": "ZX-SVC-CLOUD",
        "name_en": "Cloud & ICT",
        "title_en": "Secure infrastructure, networks and systems integration engineered for scale",
        "names": {
            "fa": "کلاود و ICT",
            "ar": "الحوسبة وتقنية المعلومات",
            "tr": "Bulut ve ICT",
            "de": "Cloud und ICT",
            "fr": "Cloud et ICT",
            "es": "Nube e ICT",
            "ru": "Облако и ICT",
        },
        "titles": {
            "fa": "زیرساخت امن، شبکه و یکپارچه‌سازی سیستم‌ها برای مقیاس‌پذیری و پایداری",
            "ar": "بنية تحتية آمنة وشبكات وتكامل أنظمة مصمّمة للتوسّع والموثوقية",
            "tr": "Ölçek ve güvenilirlik için tasarlanmış güvenli altyapı, ağlar ve sistem entegrasyonu",
            "de": "Sichere Infrastruktur, Netzwerke und Systemintegration für Skalierung und Zuverlässigkeit",
            "fr": "Infrastructure sécurisée, réseaux et intégration de systèmes conçus pour l'échelle",
            "es": "Infraestructura segura, redes e integración de sistemas diseñadas para escalar",
            "ru": "Безопасная инфраструктура, сети и системная интеграция для масштаба и надёжности",
        },
        "name_ar": "الحوسبة وتقنية المعلومات",
        "description_en": (
            "Secure infrastructure, networks and systems integration engineered for scale and "
            "reliability: cloud architecture and migration, DevOps and CI/CD, networking, identity "
            "and security hardening, monitoring and backup, and integration between your business "
            "systems. Scoped and priced in a formal proposal."
        ),
        "description_ar": (
            "بنية تحتية آمنة وشبكات وتكامل أنظمة مصمّمة للتوسّع والموثوقية: هندسة السحابة والترحيل، "
            "DevOps وCI/CD، الشبكات، الهوية وتعزيز الأمان، المراقبة والنسخ الاحتياطي، والتكامل بين "
            "أنظمة أعمالك. يُحدَّد النطاق والسعر في عرض رسمي."
        ),
        "specs": {
            "type": "service",
            "features": [
                "Cloud architecture and migration",
                "DevOps, CI/CD and observability",
                "Networks, identity and security hardening",
                "Systems integration and APIs",
                "Backup, recovery and monitoring",
            ],
            "quote_inputs": ["current environment", "workloads", "compliance needs", "timeline"],
        },
        "image": "cloud.jpg",
        "sort_order": 20,
    },
    {
        "code": "103",
        "sku": "ZX-SVC-WEB",
        "name_en": "Web & Mobile",
        "title_en": "Fast, bilingual EN/AR websites and apps with motion and detail that convert",
        "names": {
            "fa": "وب و موبایل",
            "ar": "الويب والتطبيقات",
            "tr": "Web ve Mobil",
            "de": "Web und Mobile",
            "fr": "Web et mobile",
            "es": "Web y móvil",
            "ru": "Веб и мобильные приложения",
        },
        "titles": {
            "fa": "وب‌سایت‌ها و اپلیکیشن‌های سریع و دوزبانه (انگلیسی/عربی) با موشن و جزئیاتی که نتیجه می‌دهد",
            "ar": "مواقع وتطبيقات سريعة وأنيقة — تدعم العربية والإنجليزية — بحركة وتفاصيل تُحقّق النتائج",
            "tr": "Hızlı, iki dilli (EN/AR) web siteleri ve uygulamalar; dönüşüm sağlayan hareket ve detay",
            "de": "Schnelle, zweisprachige (EN/AR) Websites und Apps mit Motion und Details, die konvertieren",
            "fr": "Sites et applications rapides, bilingues EN/AR, avec motion design et détails qui convertissent",
            "es": "Sitios y apps rápidos, bilingües EN/AR, con movimiento y detalle que convierten",
            "ru": "Быстрые двуязычные (EN/AR) сайты и приложения с анимацией и вниманием к деталям",
        },
        "name_ar": "الويب والتطبيقات",
        "description_en": (
            "Fast, beautiful websites and apps — bilingual EN/AR ready — with motion and detail that "
            "convert. Corporate websites, landing pages, e-commerce, web applications, iOS/Android apps, "
            "design systems and performance work. Scoped and priced in a formal proposal."
        ),
        "description_ar": (
            "مواقع وتطبيقات سريعة وأنيقة — تدعم العربية والإنجليزية — بحركة وتفاصيل تُحقّق النتائج. "
            "مواقع الشركات، صفحات الهبوط، المتاجر الإلكترونية، تطبيقات الويب، تطبيقات iOS/Android، "
            "أنظمة التصميم وتحسين الأداء. يُحدَّد النطاق والسعر في عرض رسمي."
        ),
        "specs": {
            "type": "service",
            "features": [
                "Corporate websites and landing pages",
                "Bilingual EN/AR with full RTL support",
                "Web applications and e-commerce",
                "iOS and Android apps",
                "Motion design and performance optimisation",
            ],
            "quote_inputs": ["pages or screens", "languages", "integrations", "timeline"],
        },
        "image": "web.jpg",
        "sort_order": 30,
    },
    {
        "code": "104",
        "sku": "ZX-SVC-AUTOMATION",
        "name_en": "Intelligent Automation",
        "title_en": "AI agents and workflow automation that remove friction from your operations",
        "names": {
            "fa": "اتوماسیون هوشمند",
            "ar": "الأتمتة الذكية",
            "tr": "Akıllı Otomasyon",
            "de": "Intelligente Automatisierung",
            "fr": "Automatisation intelligente",
            "es": "Automatización inteligente",
            "ru": "Интеллектуальная автоматизация",
        },
        "titles": {
            "fa": "ایجنت‌های هوش مصنوعی و اتوماسیون فرایندها که اصطکاک را از عملیات شما حذف می‌کنند",
            "ar": "وكلاء ذكاء اصطناعي وأتمتة لسير العمل تزيل التعقيد ليركّز فريقك على القرار",
            "tr": "Operasyonlarınızdaki sürtünmeyi kaldıran yapay zeka ajanları ve iş akışı otomasyonu",
            "de": "KI-Agenten und Workflow-Automatisierung, die Reibung aus Ihren Abläufen nehmen",
            "fr": "Agents IA et automatisation des flux qui suppriment les frictions de vos opérations",
            "es": "Agentes de IA y automatización de flujos que eliminan la fricción de sus operaciones",
            "ru": "ИИ-агенты и автоматизация процессов, убирающие рутину из ваших операций",
        },
        "name_ar": "الأتمتة الذكية",
        "description_en": (
            "AI agents and workflow automation that remove friction so your team focuses on judgement: "
            "customer-service and sales agents on WhatsApp, Telegram, email and web; back-office "
            "workflows; document processing; human-in-the-loop approvals; integrations with CRM, ERP "
            "and messaging platforms. Scoped and priced in a formal proposal."
        ),
        "description_ar": (
            "وكلاء ذكاء اصطناعي وأتمتة لسير العمل تزيل التعقيد ليركّز فريقك على القرار: وكلاء خدمة "
            "العملاء والمبيعات على واتساب وتيليغرام والبريد والويب، أتمتة المكاتب الخلفية، معالجة "
            "المستندات، موافقات بشرية ضمن المسار، وتكامل مع CRM وERP ومنصّات المراسلة. "
            "يُحدَّد النطاق والسعر في عرض رسمي."
        ),
        "specs": {
            "type": "service",
            "features": [
                "AI agents on WhatsApp, Telegram, email and web",
                "Human-in-the-loop approvals for sensitive actions",
                "Back-office and document workflows",
                "CRM / ERP / messaging integrations",
                "Monitoring, audit trail and reporting",
            ],
            "quote_inputs": ["processes to automate", "channels", "systems to integrate", "timeline"],
        },
        "image": "automation.jpg",
        "sort_order": 40,
    },
    {
        "code": "105",
        "sku": "ZX-SVC-DATA",
        "name_en": "Data & Analytics",
        "title_en": "Dashboards and pipelines that turn raw numbers into clear decisions",
        "names": {
            "fa": "داده و تحلیل",
            "ar": "البيانات والتحليلات",
            "tr": "Veri ve Analitik",
            "de": "Daten und Analysen",
            "fr": "Données et analyses",
            "es": "Datos y analítica",
            "ru": "Данные и аналитика",
        },
        "titles": {
            "fa": "داشبوردها و پایپ‌لاین‌هایی که اعداد خام را به تصمیم‌های روشن تبدیل می‌کنند",
            "ar": "لوحات ومسارات بيانات تحوّل الأرقام إلى قرارات دقيقة وواضحة",
            "tr": "Ham sayıları net kararlara dönüştüren panolar ve veri hatları",
            "de": "Dashboards und Pipelines, die Rohdaten in klare Entscheidungen verwandeln",
            "fr": "Tableaux de bord et pipelines qui transforment les données brutes en décisions claires",
            "es": "Paneles y pipelines que convierten datos en decisiones claras",
            "ru": "Дашборды и пайплайны, превращающие сырые цифры в понятные решения",
        },
        "name_ar": "البيانات والتحليلات",
        "description_en": (
            "Dashboards and pipelines that turn raw numbers into decisions — accurate and clear: data "
            "warehousing and ETL, BI dashboards, KPI reporting, data quality, and analytics on top of "
            "your operational systems. Scoped and priced in a formal proposal."
        ),
        "description_ar": (
            "لوحات ومسارات بيانات تحوّل الأرقام إلى قرارات دقيقة وواضحة: مستودعات البيانات وETL، لوحات "
            "ذكاء الأعمال، تقارير مؤشرات الأداء، جودة البيانات، والتحليلات فوق أنظمتك التشغيلية. "
            "يُحدَّد النطاق والسعر في عرض رسمي."
        ),
        "specs": {
            "type": "service",
            "features": [
                "Data warehousing and ETL pipelines",
                "BI dashboards and KPI reporting",
                "Data quality and governance",
                "Forecasting and analytics on operational data",
            ],
            "quote_inputs": ["data sources", "KPIs and audiences", "refresh frequency", "timeline"],
        },
        "image": "data.jpg",
        "sort_order": 50,
    },
    {
        "code": "106",
        "sku": "ZX-SVC-3D",
        "name_en": "Animation & 3D",
        "title_en": "Brand films, AI video and interactive 3D that give your technology a story",
        "names": {
            "fa": "انیمیشن و سه‌بعدی",
            "ar": "الرسوم والحركة ثلاثية الأبعاد",
            "tr": "Animasyon ve 3D",
            "de": "Animation und 3D",
            "fr": "Animation et 3D",
            "es": "Animación y 3D",
            "ru": "Анимация и 3D",
        },
        "titles": {
            "fa": "فیلم‌های برند، ویدیوی هوش مصنوعی و سه‌بعدی تعاملی که به فناوری شما داستان می‌دهد",
            "ar": "أفلام العلامة وفيديو الذكاء الاصطناعي ومحتوى ثلاثي الأبعاد تفاعلي يمنح تقنيتك قصة تستحق المشاهدة",
            "tr": "Teknolojinize izlenmeye değer bir hikâye kazandıran marka filmleri, yapay zeka videoları ve etkileşimli 3D",
            "de": "Markenfilme, KI-Video und interaktives 3D, die Ihrer Technologie eine Geschichte geben",
            "fr": "Films de marque, vidéo IA et 3D interactive qui donnent une histoire à votre technologie",
            "es": "Películas de marca, vídeo con IA y 3D interactivo que dan historia a su tecnología",
            "ru": "Бренд-фильмы, ИИ-видео и интерактивное 3D, которые дают вашей технологии историю",
        },
        "name_ar": "الرسوم والحركة ثلاثية الأبعاد",
        "description_en": (
            "Brand films, AI video and interactive 3D that give your technology a story worth watching: "
            "product and explainer animation, motion graphics, AI-generated video, 3D product "
            "visualisation and interactive web 3D. Scoped and priced in a formal proposal."
        ),
        "description_ar": (
            "أفلام العلامة وفيديو الذكاء الاصطناعي ومحتوى ثلاثي الأبعاد تفاعلي يمنح تقنيتك قصة تستحق "
            "المشاهدة: رسوم المنتجات والفيديوهات التوضيحية، الموشن غرافيك، الفيديو المولّد بالذكاء "
            "الاصطناعي، تصوير المنتجات ثلاثي الأبعاد والويب ثلاثي الأبعاد التفاعلي. "
            "يُحدَّد النطاق والسعر في عرض رسمي."
        ),
        "specs": {
            "type": "service",
            "features": [
                "Brand films and explainer animation",
                "Motion graphics and AI-generated video",
                "3D product visualisation",
                "Interactive web 3D experiences",
            ],
            "quote_inputs": ["format and length", "style references", "languages", "timeline"],
        },
        "image": "3d.jpg",
        "sort_order": 60,
    },
]


def products() -> list[dict]:
    rows = []
    for s in SERVICES:
        rows.append(
            {
                "id": uid("product", s["sku"]),
                "sku": s["sku"],
                "code": s["code"],
                "name_en": s["name_en"],
                "title_en": s["title_en"],
                "names": s["names"],
                "titles": s["titles"],
                "name_ar": s["name_ar"],
                "category": "services",
                "unit": "project",
                "base_price": 0,
                "unit_price": 0,
                "currency": "USD",
                "description_ar": s["description_ar"],
                "description_en": s["description_en"],
                "specs": {**s["specs"], "pricing": "proposal only", "source": SITE},
                "image_url": f"/web/assets/img/{s['image']}",
                "sort_order": s["sort_order"],
                "stock_qty": 0,
                "reorder_point": 0,
                "discount_tiers": [],
                "is_active": True,
            }
        )
    return rows


# ---------------------------------------------------------------------------
# 006 categories
# ---------------------------------------------------------------------------

CATEGORIES = [
    {
        "key": "services",
        "name_en": "Services",
        "names": {
            "fa": "خدمات",
            "ar": "الخدمات",
            "tr": "Hizmetler",
            "de": "Leistungen",
            "fr": "Services",
            "es": "Servicios",
            "ru": "Услуги",
        },
        "icon": "✨",
        "sort_order": 10,
        "is_active": True,
    }
]


# ---------------------------------------------------------------------------
# 002 fallback templates
# ---------------------------------------------------------------------------

TEMPLATES = [
    (
        "greeting_default",
        "Welcome to Zenovix, a Dubai studio for AI and digital technology. I can help with "
        "artificial intelligence, cloud and ICT, web and mobile, intelligent automation, data and "
        "analytics, and animation and 3D. How can I help you today?",
        "مرحبًا بك في زينوفكس، استوديو من دبي للذكاء الاصطناعي والتقنية الرقمية. يمكنني مساعدتك في "
        "الذكاء الاصطناعي، الحوسبة وتقنية المعلومات، الويب والتطبيقات، الأتمتة الذكية، البيانات "
        "والتحليلات، والرسوم ثلاثية الأبعاد. كيف يمكنني مساعدتك اليوم؟",
    ),
    (
        "clarification_default",
        "Sorry, I couldn't fully understand your request. Could you tell me whether it concerns an "
        "AI solution, cloud or ICT, a website or app, automation, data and dashboards, or animation "
        "and 3D — and what you would like to achieve?",
        "عذرًا، لم أفهم طلبك بالكامل. هل يتعلق بحلّ ذكاء اصطناعي، أو الحوسبة وتقنية المعلومات، أو "
        "موقع أو تطبيق، أو الأتمتة، أو البيانات ولوحات المعلومات، أو الرسوم ثلاثية الأبعاد — وما الذي "
        "تودّ تحقيقه؟",
    ),
    (
        "processing_default",
        "Thank you — I'm checking this with the team. Please hold on a moment.",
        "شكرًا لك — أراجع الأمر مع الفريق. يرجى الانتظار لحظة.",
    ),
    (
        "safety_emergency",
        "Emergency keyword detected. If a live system or website is down, please share the URL or "
        "system name, what changed, and since when. A team member will be alerted immediately; you "
        f"can also call {PHONE} or WhatsApp {WHATSAPP}.",
        "تم رصد كلمة الطوارئ. إذا كان نظام أو موقع مباشر متوقفًا، يرجى مشاركة الرابط أو اسم النظام، "
        f"وما الذي تغيّر، ومنذ متى. سيتم تنبيه أحد أعضاء الفريق فورًا؛ يمكنك أيضًا الاتصال على {PHONE} "
        f"أو واتساب {WHATSAPP}.",
    ),
    (
        "hitl_timeout",
        "Thank you for your patience. Your request has been recorded and a member of our team will "
        "come back to you directly — typically the same business day.",
        "شكرًا لصبرك. تم تسجيل طلبك وسيتواصل معك أحد أعضاء فريقنا مباشرة — عادةً خلال يوم العمل نفسه.",
    ),
    (
        "off_hours",
        f"Thank you for your message. Our studio hours are {HOURS_EN}. Your message has been "
        f"recorded and we will reply on the next business day. For urgent matters call {PHONE} or "
        f"e-mail {EMAIL}.",
        "شكرًا لرسالتك. ساعات عمل الاستوديو من الاثنين إلى الجمعة 9:00–18:00 بتوقيت الخليج. تم تسجيل "
        f"رسالتك وسنردّ في يوم العمل التالي. للأمور العاجلة اتصل على {PHONE} أو راسلنا على {EMAIL}.",
    ),
]


def templates() -> list[dict]:
    return [
        {
            "id": uid("template", key),
            "key": key,
            "name_ar": key,
            "name_en": key,
            "channel": "",
            "subject": "",
            "body_ar": ar,
            "body_en": en,
            "variables": [],
            "is_active": True,
        }
        for key, en, ar in TEMPLATES
    ]


# ---------------------------------------------------------------------------
# 003 FAQ (24 entries)
# ---------------------------------------------------------------------------

FAQ = [
    # company
    ("company", "Who is Zenovix?", "من هي زينوفكس؟",
     "Zenovix is a Dubai-based AI and digital technology studio: a team of engineers, designers and AI "
     "specialists building the systems modern businesses run on. We work like a partner, not a vendor — "
     "close to your goals and obsessive about the details. From bilingual platforms for the Gulf to AI "
     "products for global markets, we turn ambition into shipped, measurable technology.",
     "زينوفكس استوديو للذكاء الاصطناعي والتقنية الرقمية مقرّه دبي: فريق من المهندسين والمصممين وخبراء "
     "الذكاء الاصطناعي يبنون الأنظمة التي تعتمد عليها الأعمال الحديثة. نعمل كشريك لا كمورّد — قريبين من "
     "أهدافك ومهووسين بالتفاصيل. من المنصّات ثنائية اللغة للخليج إلى منتجات الذكاء الاصطناعي للأسواق "
     "العالمية، نحوّل الطموح إلى تقنية منجزة وقابلة للقياس.",
     ["about", "company", "who", "zenovix", "studio", "من نحن", "شركة"]),
    ("company", "Where are you located?", "أين يقع مقرّكم؟",
     f"Our studio is at {ADDRESS}. We are engineered in Dubai and deliver worldwide. "
     "Map: https://www.google.com/maps?cid=9389408557797241110",
     "يقع الاستوديو في مكتب 2703، برج أسبكت، الخليج التجاري، دبي، الإمارات العربية المتحدة. نعمل من دبي "
     "ونصل إلى العالم. الخريطة: https://www.google.com/maps?cid=9389408557797241110",
     ["location", "address", "office", "dubai", "business bay", "aspect tower", "العنوان", "مكتب"]),
    ("company", "What are your working hours?", "ما هي ساعات العمل؟",
     f"Studio hours are {HOURS_EN}. Messages sent outside these hours are recorded and answered on the "
     "next business day. This assistant is available 24/7 for questions and to capture your request.",
     "ساعات عمل الاستوديو من الاثنين إلى الجمعة 9:00–18:00 بتوقيت الخليج (UTC+4). الرسائل خارج هذه "
     "الساعات تُسجَّل ويُردّ عليها في يوم العمل التالي. هذا المساعد متاح على مدار الساعة للأسئلة وتسجيل طلبك.",
     ["hours", "working hours", "open", "time", "ساعات", "الدوام"]),
    ("company", "How can I contact you?", "كيف يمكنني التواصل معكم؟",
     f"E-mail {EMAIL}, call {PHONE}, or chat on WhatsApp at {WHATSAPP}. You can also send the contact "
     f"form on {SITE} or simply describe your project here and a team member will follow up.",
     f"البريد الإلكتروني {EMAIL}، الهاتف {PHONE}، أو واتساب {WHATSAPP}. يمكنك أيضًا إرسال نموذج التواصل "
     f"على {SITE} أو وصف مشروعك هنا وسيتابع معك أحد أعضاء الفريق.",
     ["contact", "email", "phone", "whatsapp", "تواصل", "هاتف", "بريد"]),
    ("company", "How quickly do you respond to enquiries?", "ما سرعة الرد على الاستفسارات؟",
     "We normally reply the same business day. Complex project requests get a short discovery call "
     "before we send a proposal.",
     "نردّ عادةً خلال يوم العمل نفسه. طلبات المشاريع المعقّدة تسبقها مكالمة استكشاف قصيرة قبل إرسال العرض.",
     ["response", "reply", "how long", "fast", "الرد", "سرعة"]),
    ("company", "Which languages do you support?", "ما اللغات التي تدعمونها؟",
     "English and Arabic are native to everything we build — bilingual EN/AR platforms with full RTL "
     "support are a speciality. This assistant also answers in Persian, Turkish, Russian, German, French "
     "and Spanish.",
     "الإنجليزية والعربية أساس كل ما نبنيه — المنصّات ثنائية اللغة مع دعم كامل للكتابة من اليمين إلى "
     "اليسار من تخصصاتنا. يجيب هذا المساعد أيضًا بالفارسية والتركية والروسية والألمانية والفرنسية والإسبانية.",
     ["language", "arabic", "english", "bilingual", "rtl", "لغة", "عربي"]),
    # services
    ("services", "What services do you offer?", "ما الخدمات التي تقدّمونها؟",
     "Six service lines: 01 Artificial Intelligence, 02 Cloud & ICT, 03 Web & Mobile, 04 Intelligent "
     "Automation, 05 Data & Analytics, 06 Animation & 3D. One partner for strategy, design, engineering "
     "and the AI that ties it together.",
     "ست خدمات: 01 الذكاء الاصطناعي، 02 الحوسبة وتقنية المعلومات، 03 الويب والتطبيقات، 04 الأتمتة الذكية، "
     "05 البيانات والتحليلات، 06 الرسوم ثلاثية الأبعاد. شريك واحد للاستراتيجية والتصميم والهندسة والذكاء "
     "الاصطناعي الذي يجمعها معًا.",
     ["services", "offer", "what do you do", "الخدمات", "ماذا تقدمون"]),
    ("services", "What can you build with artificial intelligence?", "ماذا يمكنكم بناؤه بالذكاء الاصطناعي؟",
     "Custom models, computer vision and conversational AI trained on your data and shipped "
     "production-ready: assistants and chatbots on your own knowledge, document understanding, image and "
     "video analysis, forecasting, and integration into the systems you already use.",
     "نماذج مخصّصة ورؤية حاسوبية وذكاء اصطناعي حواري مدرّب على بياناتك وجاهز للإنتاج: مساعدون وروبوتات "
     "محادثة تعتمد على معرفتك، فهم المستندات، تحليل الصور والفيديو، التنبؤ، والتكامل مع أنظمتك الحالية.",
     ["ai", "artificial intelligence", "chatbot", "model", "computer vision", "ذكاء اصطناعي", "روبوت"]),
    ("services", "Do you build AI chatbots and agents for WhatsApp or Telegram?", "هل تبنون روبوتات ووكلاء ذكاء اصطناعي لواتساب أو تيليغرام؟",
     "Yes. Intelligent Automation covers AI agents on WhatsApp, Telegram, e-mail and the web, trained on "
     "your own knowledge, with human-in-the-loop approvals for anything sensitive (quotes, payments, "
     "contracts) and a full audit trail — the same pattern this assistant runs on.",
     "نعم. تشمل الأتمتة الذكية وكلاء ذكاء اصطناعي على واتساب وتيليغرام والبريد والويب، مدرّبين على "
     "معرفتك، مع موافقات بشرية للأمور الحسّاسة (العروض، المدفوعات، العقود) وسجل تدقيق كامل — وهو النمط "
     "نفسه الذي يعمل به هذا المساعد.",
     ["whatsapp", "telegram", "agent", "bot", "automation", "واتساب", "تيليغرام", "وكيل"]),
    ("services", "What does Cloud & ICT include?", "ماذا تشمل خدمة الحوسبة وتقنية المعلومات؟",
     "Secure infrastructure, networks and systems integration engineered for scale and reliability: cloud "
     "architecture and migration, DevOps and CI/CD, identity and security hardening, monitoring, backup and "
     "recovery, and integration between your business systems.",
     "بنية تحتية آمنة وشبكات وتكامل أنظمة مصمّمة للتوسّع والموثوقية: هندسة السحابة والترحيل، DevOps "
     "وCI/CD، الهوية وتعزيز الأمان، المراقبة، النسخ الاحتياطي والاستعادة، والتكامل بين أنظمة أعمالك.",
     ["cloud", "ict", "infrastructure", "network", "devops", "سحابة", "بنية تحتية"]),
    ("services", "Do you build bilingual English/Arabic websites and mobile apps?", "هل تبنون مواقع وتطبيقات ثنائية اللغة عربي/إنجليزي؟",
     "Yes — fast, beautiful websites and apps, bilingual EN/AR ready with full right-to-left support, "
     "motion and detail that convert. Corporate sites, landing pages, e-commerce, web apps and iOS/Android apps.",
     "نعم — مواقع وتطبيقات سريعة وأنيقة، تدعم العربية والإنجليزية مع دعم كامل للكتابة من اليمين إلى "
     "اليسار، بحركة وتفاصيل تُحقّق النتائج. مواقع الشركات، صفحات الهبوط، المتاجر، تطبيقات الويب وiOS/Android.",
     ["website", "web", "mobile", "app", "arabic", "bilingual", "موقع", "تطبيق"]),
    ("services", "What is intelligent automation?", "ما هي الأتمتة الذكية؟",
     "AI agents and workflow automation that remove friction so your team focuses on judgement: "
     "customer-service and sales agents, back-office workflows, document processing and integrations with "
     "CRM, ERP and messaging platforms — with human approval where it matters.",
     "وكلاء ذكاء اصطناعي وأتمتة لسير العمل تزيل التعقيد ليركّز فريقك على القرار: وكلاء خدمة العملاء "
     "والمبيعات، أتمتة المكاتب الخلفية، معالجة المستندات، والتكامل مع CRM وERP ومنصّات المراسلة — مع "
     "موافقة بشرية حيث يلزم.",
     ["automation", "workflow", "agent", "process", "أتمتة", "سير العمل"]),
    ("services", "What do you offer in data and analytics?", "ماذا تقدّمون في البيانات والتحليلات؟",
     "Dashboards and pipelines that turn raw numbers into decisions — accurate and clear: data "
     "warehousing and ETL, BI dashboards, KPI reporting, data quality and analytics on top of your "
     "operational systems.",
     "لوحات ومسارات بيانات تحوّل الأرقام إلى قرارات دقيقة وواضحة: مستودعات البيانات وETL، لوحات ذكاء "
     "الأعمال، تقارير مؤشرات الأداء، جودة البيانات والتحليلات فوق أنظمتك التشغيلية.",
     ["data", "analytics", "dashboard", "bi", "report", "بيانات", "تحليلات", "لوحة"]),
    ("services", "Do you produce animation, video and 3D?", "هل تنتجون الرسوم المتحركة والفيديو والمحتوى ثلاثي الأبعاد؟",
     "Yes — brand films, AI video and interactive 3D that give your technology a story worth watching: "
     "product and explainer animation, motion graphics, AI-generated video, 3D product visualisation and "
     "interactive web 3D.",
     "نعم — أفلام العلامة وفيديو الذكاء الاصطناعي ومحتوى ثلاثي الأبعاد تفاعلي يمنح تقنيتك قصة تستحق "
     "المشاهدة: رسوم المنتجات والفيديوهات التوضيحية، الموشن غرافيك، الفيديو المولّد بالذكاء الاصطناعي، "
     "التصوير ثلاثي الأبعاد للمنتجات والويب ثلاثي الأبعاد التفاعلي.",
     ["animation", "3d", "video", "motion", "film", "رسوم", "فيديو", "ثلاثي الأبعاد"]),
    # process / pricing
    ("process", "How much does a project cost?", "كم تبلغ تكلفة المشروع؟",
     "Every project is different, so we never quote a price in chat. Tell us what you want to build, for "
     "whom, which languages and integrations you need and your timeline; after a short discovery call we "
     "send a formal proposal with scope, timeline and price, confirmed by a manager.",
     "كل مشروع مختلف، لذلك لا نذكر سعرًا في المحادثة أبدًا. أخبرنا بما تريد بناءه ولمن، وما اللغات "
     "والتكاملات التي تحتاجها وجدولك الزمني؛ بعد مكالمة استكشاف قصيرة نرسل عرضًا رسميًا بالنطاق والجدول "
     "والسعر، مؤكَّدًا من مدير.",
     ["price", "cost", "quote", "how much", "budget", "سعر", "تكلفة", "عرض"]),
    ("process", "How do you work? What is your process?", "كيف تعملون؟ ما هي منهجيتكم؟",
     "Strategy first — we understand the business before we write a line of code. Then design and "
     "engineering with craft in the details: motion, performance and polish are not optional. Built to "
     "last: systems that scale and a team that stays with you after launch.",
     "الاستراتيجية أولاً — نفهم العمل قبل كتابة أي سطر برمجي. ثم التصميم والهندسة بإتقان في التفاصيل: "
     "الحركة والأداء والصقل ليست خيارات ثانوية. مبني ليدوم: أنظمة تتوسّع وفريق يبقى معك بعد الإطلاق.",
     ["process", "how do you work", "method", "approach", "منهجية", "طريقة العمل"]),
    ("process", "How long does a project take?", "كم يستغرق المشروع؟",
     "Timelines depend on scope and are confirmed in the proposal. A landing page and an enterprise AI "
     "platform are very different projects — share your goals and deadline and we will propose a realistic "
     "plan with milestones.",
     "تعتمد المدة على النطاق وتُؤكَّد في العرض. صفحة الهبوط ومنصّة الذكاء الاصطناعي المؤسسية مشروعان "
     "مختلفان جدًا — شاركنا أهدافك وموعدك النهائي وسنقترح خطة واقعية بمراحل واضحة.",
     ["timeline", "how long", "duration", "deadline", "مدة", "وقت"]),
    ("process", "Do you provide support after launch?", "هل تقدّمون الدعم بعد الإطلاق؟",
     "Yes. \"Built to last\" is one of our values: we offer maintenance, monitoring and iteration plans so "
     "the team stays with you after go-live. Support terms are part of the proposal.",
     "نعم. «مبني ليدوم» إحدى قيمنا: نقدّم خطط صيانة ومراقبة وتطوير مستمر ليبقى الفريق معك بعد الإطلاق. "
     "شروط الدعم جزء من العرض.",
     ["support", "maintenance", "after launch", "sla", "دعم", "صيانة"]),
    ("process", "Can you integrate with our existing systems?", "هل يمكنكم التكامل مع أنظمتنا الحالية؟",
     "Yes — systems integration is core to Cloud & ICT and Intelligent Automation: CRM, ERP, payment "
     "gateways, messaging platforms, databases and third-party APIs.",
     "نعم — تكامل الأنظمة جزء أساسي من الحوسبة وتقنية المعلومات والأتمتة الذكية: CRM وERP وبوابات الدفع "
     "ومنصّات المراسلة وقواعد البيانات وواجهات برمجة التطبيقات الخارجية.",
     ["integration", "crm", "erp", "api", "existing systems", "تكامل", "أنظمة"]),
    ("process", "How do I start a project with you?", "كيف أبدأ مشروعًا معكم؟",
     "Describe your goal here or press Quote; the assistant collects the basics and a manager reviews "
     f"it. You can also e-mail {EMAIL} or use the form at {SITE}. We come back with next steps, usually "
     "the same business day.",
     "صِف هدفك هنا أو اضغط زر عرض السعر؛ يجمع المساعد الأساسيات ويراجعها مدير. يمكنك أيضًا مراسلة "
     f"{EMAIL} أو استخدام النموذج على {SITE}. نعود إليك بالخطوات التالية، عادةً خلال يوم العمل نفسه.",
     ["start", "begin", "project", "get started", "ابدأ", "مشروع"]),
    # compliance / data
    ("compliance", "Do you share my enquiry details with third parties?", "هل تشاركون بيانات استفساري مع أطراف ثالثة؟",
     "No. Your details are used only to answer your enquiry and prepare a proposal. This assistant never "
     "shares internal data or other clients' information, and data deletion requests are handled by a manager.",
     "لا. تُستخدم بياناتك فقط للرد على استفسارك وإعداد العرض. لا يشارك هذا المساعد أبدًا البيانات "
     "الداخلية أو معلومات عملاء آخرين، ويتولّى مدير طلبات حذف البيانات.",
     ["privacy", "data", "third parties", "gdpr", "خصوصية", "بيانات"]),
    ("compliance", "Who owns the code and data you build for us?", "من يملك الكود والبيانات التي تبنونها لنا؟",
     "Ownership and IP terms are defined in the proposal and contract. Our default approach is that the "
     "client owns the delivered solution and its data; a manager confirms the exact terms for each project.",
     "تُحدَّد شروط الملكية والملكية الفكرية في العرض والعقد. نهجنا الافتراضي أن العميل يملك الحل المسلَّم "
     "وبياناته؛ ويؤكّد مدير الشروط الدقيقة لكل مشروع.",
     ["ownership", "ip", "code", "contract", "ملكية", "عقد"]),
    ("compliance", "Can this assistant take a payment or sign a contract?", "هل يمكن لهذا المساعد استلام دفعة أو توقيع عقد؟",
     "No. Payments, contracts, price changes and data deletion always go to a human manager. The "
     "assistant records your request and the team follows up.",
     "لا. المدفوعات والعقود وتغييرات الأسعار وحذف البيانات تذهب دائمًا إلى مدير بشري. يسجّل المساعد طلبك "
     "ويتابع الفريق معك.",
     ["payment", "contract", "sign", "pay", "دفع", "عقد"]),
    ("company", "Do you work with clients outside the UAE?", "هل تعملون مع عملاء خارج الإمارات؟",
     "Yes — engineered in Dubai, delivered worldwide. We build bilingual platforms for the Gulf and AI "
     "products for global markets, working remotely with clients in any time zone.",
     "نعم — هندسة من دبي ونصل إلى العالم. نبني منصّات ثنائية اللغة للخليج ومنتجات ذكاء اصطناعي للأسواق "
     "العالمية، ونعمل عن بُعد مع عملاء في أي منطقة زمنية.",
     ["international", "global", "remote", "outside uae", "worldwide", "عالمي", "خارج"]),
]


def faq() -> list[dict]:
    return [
        {
            "id": uid("faq", q_en),
            "question_ar": q_ar,
            "question_en": q_en,
            "answer_ar": a_ar,
            "answer_en": a_en,
            "category": cat,
            "language": "en",
            "tags": tags,
            "is_active": True,
            "hit_count": 0,
        }
        for cat, q_en, q_ar, a_en, a_ar, tags in FAQ
    ]


# ---------------------------------------------------------------------------
# 004 troubleshooting (8 guides)
# ---------------------------------------------------------------------------

GUIDES = [
    ("communication", "low", "No response received to my enquiry", "لم أتلقَّ ردًا على استفساري",
     "Client submitted the website form or sent an e-mail and has not heard back.",
     "أرسل العميل نموذج الموقع أو بريدًا إلكترونيًا ولم يتلقَّ ردًا.",
     f"We normally reply the same business day ({HOURS_EN}). Please check your spam folder for mail from "
     f"{EMAIL}. If more than one business day has passed, contact us directly on {PHONE} or WhatsApp "
     f"{WHATSAPP} mentioning the date of your enquiry — the assistant can also open a follow-up task for the team.",
     f"نردّ عادةً خلال يوم العمل نفسه (الاثنين–الجمعة 9:00–18:00 بتوقيت الخليج). يرجى التحقق من مجلد "
     f"الرسائل غير المرغوب فيها بحثًا عن بريد من {EMAIL}. إذا مرّ أكثر من يوم عمل، تواصل معنا مباشرة على "
     f"{PHONE} أو واتساب {WHATSAPP} مع ذكر تاريخ استفسارك — ويمكن للمساعد أيضًا فتح مهمة متابعة للفريق.",
     ["enquiry", "no reply", "follow up"]),
    ("sales", "medium", "My proposal is taking longer than expected", "عرضي يستغرق وقتًا أطول من المتوقع",
     "Client requested a proposal and it has not arrived in the expected time.",
     "طلب العميل عرضًا ولم يصل في الوقت المتوقع.",
     "Proposals are prepared by the team and confirmed by a manager; complex scopes need a discovery call "
     "first. Share your reference number (ZX-…) or the date of your request and the assistant will check the "
     "status and nudge the owner. If a discovery call was proposed, booking it is the fastest way forward.",
     "يُعدّ الفريق العروض ويؤكّدها مدير؛ النطاقات المعقّدة تحتاج مكالمة استكشاف أولاً. شارك رقمك المرجعي "
     "(ZX-…) أو تاريخ طلبك وسيتحقق المساعد من الحالة ويذكّر المسؤول. إذا اقتُرحت مكالمة استكشاف، فحجزها هو "
     "أسرع طريق للمضي قدمًا.",
     ["proposal", "quote", "delay"]),
    ("operations", "critical", "Live website or system is down", "الموقع أو النظام المباشر متوقف",
     "A production website, app or integration built or hosted by Zenovix is unreachable or erroring.",
     "موقع أو تطبيق أو تكامل إنتاجي بناه أو يستضيفه زينوفكس غير متاح أو يُظهر أخطاء.",
     "Type the word emergency, then share: the URL or system name, the error you see, what changed and "
     f"since when. The on-call engineer is alerted immediately. Also call {PHONE}. Do not restart servers or "
     "change DNS yourself unless the team asks you to.",
     f"اكتب كلمة emergency، ثم شارك: الرابط أو اسم النظام، الخطأ الذي تراه، ما الذي تغيّر ومنذ متى. يُنبَّه "
     f"المهندس المناوب فورًا. اتصل أيضًا على {PHONE}. لا تُعد تشغيل الخوادم أو تغيّر DNS بنفسك ما لم يطلب الفريق ذلك.",
     ["outage", "down", "emergency", "incident"]),
    ("ai", "medium", "The AI assistant gives wrong or outdated answers", "المساعد الذكي يعطي إجابات خاطئة أو قديمة",
     "An AI agent or chatbot delivered by Zenovix answers incorrectly, hallucinates or uses stale information.",
     "وكيل ذكاء اصطناعي أو روبوت محادثة سلّمه زينوفكس يجيب بشكل خاطئ أو يختلق معلومات أو يستخدم بيانات قديمة.",
     "Send the exact question, the answer received and what the correct answer should be. Most cases are "
     "fixed by updating the approved knowledge base (FAQ, documents, catalog) in the admin panel — the "
     "assistant only answers from approved data. If the issue is behavioural (tone, refusing valid questions), "
     "the team adjusts the agent soul and guard settings.",
     "أرسل السؤال بالضبط والإجابة التي تلقيتها وما ينبغي أن تكون الإجابة الصحيحة. تُحلّ معظم الحالات بتحديث "
     "قاعدة المعرفة المعتمدة (الأسئلة الشائعة، المستندات، الكتالوج) في لوحة الإدارة — فالمساعد يجيب فقط من "
     "البيانات المعتمدة. إذا كانت المشكلة سلوكية (النبرة، رفض أسئلة صحيحة)، يعدّل الفريق شخصية الوكيل وإعدادات الحماية.",
     ["ai", "chatbot", "wrong answer", "hallucination", "knowledge"]),
    ("website", "low", "Website contact form not submitting", "نموذج التواصل في الموقع لا يُرسَل",
     "Visitor cannot send the contact form on zenovix.ae.",
     "لا يستطيع الزائر إرسال نموذج التواصل على zenovix.ae.",
     f"Try again after refreshing the page, or e-mail {EMAIL} / WhatsApp {WHATSAPP} with your name, company "
     "and project. If you see a specific error message, share a screenshot so the web team can check the form.",
     f"حاول مجددًا بعد تحديث الصفحة، أو راسل {EMAIL} / واتساب {WHATSAPP} مع اسمك وشركتك ومشروعك. إذا ظهرت "
     "رسالة خطأ محددة، شارك لقطة شاشة ليتحقق فريق الويب من النموذج.",
     ["form", "website", "contact"]),
    ("access", "medium", "I cannot log in to the platform or admin panel", "لا أستطيع تسجيل الدخول إلى المنصّة أو لوحة الإدارة",
     "A client user cannot sign in to a dashboard, app or admin console delivered by Zenovix.",
     "لا يستطيع مستخدم العميل تسجيل الدخول إلى لوحة معلومات أو تطبيق أو لوحة إدارة سلّمها زينوفكس.",
     "Check the URL and that caps lock is off, then use the password-reset link if available. If the account "
     "is locked or you never received credentials, tell the assistant your name, company and the system name; "
     "access changes are confirmed by a manager for security reasons.",
     "تحقق من الرابط ومن أن مفتاح الأحرف الكبيرة غير مفعّل، ثم استخدم رابط إعادة تعيين كلمة المرور إن وُجد. "
     "إذا كان الحساب مقفلاً أو لم تستلم بيانات الدخول، أخبر المساعد باسمك وشركتك واسم النظام؛ تُؤكَّد تغييرات "
     "الوصول من مدير لأسباب أمنية.",
     ["login", "access", "password", "admin"]),
    ("data", "high", "Dashboard numbers look wrong or data is missing", "أرقام لوحة المعلومات تبدو خاطئة أو البيانات ناقصة",
     "A BI dashboard or report shows unexpected values, gaps or stale data.",
     "تُظهر لوحة ذكاء الأعمال أو التقرير قيمًا غير متوقعة أو فجوات أو بيانات قديمة.",
     "Note the dashboard name, the metric, the date range and what you expected. Most issues come from a "
     "delayed pipeline run or a changed source system; the data team checks the pipeline logs and source "
     "connection. Do not make business decisions on the affected metric until it is confirmed.",
     "دوّن اسم اللوحة والمؤشر والنطاق الزمني وما كنت تتوقعه. تنتج معظم المشكلات عن تأخر تشغيل مسار البيانات "
     "أو تغيّر في النظام المصدر؛ يفحص فريق البيانات سجلات المسار واتصال المصدر. لا تتخذ قرارات أعمال على "
     "المؤشر المتأثر حتى يتم تأكيده.",
     ["dashboard", "data", "report", "pipeline"]),
    ("billing", "medium", "Question about an invoice or payment", "سؤال حول فاتورة أو دفعة",
     "Client has a question about an invoice, payment terms or a receipt.",
     "لدى العميل سؤال حول فاتورة أو شروط الدفع أو إيصال.",
     "The assistant never handles payments. Share the invoice number and your question; a manager reviews it "
     f"and the finance contact replies from {EMAIL}. Never send card details or credentials in chat.",
     "لا يتعامل المساعد مع المدفوعات أبدًا. شارك رقم الفاتورة وسؤالك؛ يراجعه مدير ويردّ مسؤول المالية من "
     f"{EMAIL}. لا ترسل أبدًا بيانات البطاقة أو كلمات المرور في المحادثة.",
     ["invoice", "payment", "billing"]),
]


def troubleshooting() -> list[dict]:
    rows = []
    for cat, sev, t_en, t_ar, d_en, d_ar, s_en, s_ar, tags in GUIDES:
        rows.append(
            {
                "id": uid("guide", t_en),
                "title_ar": t_ar,
                "title_en": t_en,
                "description_ar": d_ar,
                "description_en": d_en,
                "symptom_ar": d_ar,
                "symptom_en": d_en,
                "problem_ar": d_ar,
                "problem_en": d_en,
                "solution_ar": s_ar,
                "solution_en": s_en,
                "category": cat,
                "severity": sev,
                "tags": tags,
                "is_active": True,
                "hit_count": 0,
            }
        )
    return rows


# ---------------------------------------------------------------------------
# 005 agent soul
# ---------------------------------------------------------------------------


def soul() -> list[dict]:
    return [
        {
            "id": "default",
            "agent_name": "Zenovix",
            "company_name": "Zenovix",
            "role_title": "Digital Operations Manager",
            "mission": (
                "Help clients and the studio team quickly, accurately and politely: answer from the "
                "approved Zenovix knowledge (AI, Cloud & ICT, Web & Mobile, Intelligent Automation, "
                "Data & Analytics, Animation & 3D), capture project enquiries and proposal requests, open "
                "support tickets, and route anything sensitive to a human manager."
            ),
            "personality": (
                "Calm, confident and genuinely helpful. Thinks like an experienced studio operations "
                "manager: practical, organised, curious about the client's goal, honest about what it does "
                "not know. A partner, not a vendor."
            ),
            "tone": "Warm, professional and concise. Short paragraphs. No hype, no jargon, no filler.",
            "languages": (
                "English is the default. If the client writes in Arabic, Persian or another language, "
                "reply fluently in that language and keep technical terms in English where clearer."
            ),
            "greeting": (
                "Hello, I am Zenovix, the digital operations manager at Zenovix — a Dubai studio for AI and "
                "digital technology. How can I help you today?"
            ),
            "boundaries": (
                "Never invent prices, timelines, team sizes, client names or availability - every project is "
                "scoped and quoted in a formal proposal by the team. Never share internal data, credentials "
                "or other clients' information. Never take payment, sign contracts, change prices or delete "
                "data; those always need a manager's approval. If a question is outside the company "
                "knowledge, say so honestly and offer a human follow-up."
            ),
            "style_rules": (
                "Write plain conversational text for chat apps: no Markdown, no asterisks, no hashes, no "
                "code blocks, no JSON. Short paragraphs, simple dash bullets, at most one emoji. Always end "
                "with a clear next step or a question."
            ),
            "signature": "Zenovix - AI & Digital Technology, Dubai",
            "extra": {"currency": "USD", "timezone": "Asia/Dubai"},
            "is_active": True,
            "version": 1,
            "updated_by": "seed",
        }
    ]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files = {
        "001_products.json": products(),
        "002_fallback_templates.json": templates(),
        "003_faq.json": faq(),
        "004_troubleshooting.json": troubleshooting(),
        "005_agent_soul.json": soul(),
        "006_catalog_categories.json": CATEGORIES,
    }
    for name, rows in files.items():
        (OUT / name).write_text(
            json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"wrote db/seed/{name}: {len(rows)} rows")


if __name__ == "__main__":
    main()
