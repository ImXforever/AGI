"""English-first catalog with per-language display (1.4.0).

The database reference language is English: ``products.name_en`` /
``title_en`` and ``catalog_categories.name_en`` are canonical.  Every other
language lives in the ``names`` / ``titles`` JSON columns and is *only* a
display layer.  A Turkish customer therefore sees a Turkish list, a Persian
customer a Persian list, and the manager edits one English row plus optional
translations — never Arabic-first strings scattered through the code.

Everything here is pure (no DB, no Telegram) so it is unit-testable; the
orchestrator and the admin API are thin callers.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

RTL_LANGUAGES = frozenset({"fa", "ar", "he"})

# Customer-facing labels for the catalog + purchase flow. English is the
# fallback for every key; other languages may be partial.
CATALOG_TEXT: dict[str, dict[str, str]] = {
    "en": {
        "pick_category": "Choose a category:",
        "pick_product": "Choose a product:",
        "pick_qty": "How much do you need?",
        "qty_custom": "Other quantity",
        "qty_prompt": "Send the quantity as a number (for example 500).",
        "qty_invalid": "Please send a number, for example 500.",
        "confirm": "Please confirm your request:",
        "confirm_btn": "Send request",
        "cancel_btn": "Cancel",
        "back": "Back",
        "main_menu": "Main menu",
        "details_btn": "Details",
        "order_btn": "Request a quote",
        "sent": "Thank you. Your request {ref} was sent to our commercial team. A manager will confirm the price shortly.",
        "cancelled": "Request cancelled. You can start again from the menu.",
        "price_on_request": "price on request",
        "code": "Code",
        "product": "Product",
        "quantity": "Quantity",
        "price": "Price",
        "unit": "Unit",
        "empty": "No products are available right now.",
        "list_title": "Products & services",
        "list_hint": "Tap a category to see products, or send a product code (for example 101).",
        "approved": "Good news. Your request {ref} was approved by our manager:\n{summary}\nOur team will contact you to finalise.",
        "rejected": "Your request {ref} could not be approved as submitted. Our team will contact you with alternatives.",
        "expired": "Your request {ref} is still under review. We will get back to you during business hours.",
        "my_requests_title": "Your recent requests:",
        "no_requests": "You have no requests yet. Choose a product from the menu to send one.",
        "unit_service": "service",
        "unit_kg": "kg",
        "unit_liter": "L",
        "unit_barrel": "bbl",
        "unit_metric ton": "MT",
        "unit_ton": "MT",
        "unit_piece": "pcs",
    },
    "fa": {
        "pick_category": "یک دسته را انتخاب کنید:",
        "pick_product": "یک محصول را انتخاب کنید:",
        "pick_qty": "چه مقدار نیاز دارید؟",
        "qty_custom": "مقدار دیگر",
        "qty_prompt": "مقدار را به صورت عدد بفرستید (مثلاً 500).",
        "qty_invalid": "لطفاً فقط عدد بفرستید، مثلاً 500.",
        "confirm": "لطفاً درخواست خود را تأیید کنید:",
        "confirm_btn": "ارسال درخواست",
        "cancel_btn": "انصراف",
        "back": "بازگشت",
        "main_menu": "منوی اصلی",
        "details_btn": "جزئیات",
        "order_btn": "درخواست پیش‌فاکتور",
        "sent": "متشکریم. درخواست {ref} برای تیم بازرگانی ارسال شد. مدیر به‌زودی قیمت را تأیید می‌کند.",
        "cancelled": "درخواست لغو شد. می‌توانید دوباره از منو شروع کنید.",
        "price_on_request": "قیمت با استعلام",
        "code": "کد",
        "product": "محصول",
        "quantity": "مقدار",
        "price": "قیمت",
        "unit": "واحد",
        "empty": "در حال حاضر محصولی موجود نیست.",
        "list_title": "محصولات و خدمات",
        "list_hint": "روی یک دسته بزنید تا محصولات را ببینید، یا کد محصول را بفرستید (مثلاً 101).",
        "approved": "خبر خوب. درخواست {ref} توسط مدیر تأیید شد:\n{summary}\nتیم ما برای نهایی‌سازی با شما تماس می‌گیرد.",
        "rejected": "درخواست {ref} به همین شکل قابل تأیید نبود. تیم ما با گزینه‌های جایگزین با شما تماس می‌گیرد.",
        "expired": "درخواست {ref} هنوز در حال بررسی است. در ساعات کاری به شما پاسخ می‌دهیم.",
        "my_requests_title": "درخواست‌های اخیر شما:",
        "no_requests": "هنوز درخواستی ثبت نکرده‌اید. از منو یک محصول انتخاب کنید.",
        "unit_service": "خدمت",
        "unit_kg": "کیلوگرم",
        "unit_liter": "لیتر",
        "unit_barrel": "بشکه",
        "unit_metric ton": "تن",
        "unit_ton": "تن",
        "unit_piece": "عدد",
    },
    "ar": {
        "pick_category": "اختر فئة:",
        "pick_product": "اختر منتجاً:",
        "pick_qty": "ما الكمية المطلوبة؟",
        "qty_custom": "كمية أخرى",
        "qty_prompt": "أرسل الكمية كرقم (مثلاً 500).",
        "qty_invalid": "يرجى إرسال رقم فقط، مثلاً 500.",
        "confirm": "يرجى تأكيد طلبك:",
        "confirm_btn": "إرسال الطلب",
        "cancel_btn": "إلغاء",
        "back": "رجوع",
        "main_menu": "القائمة الرئيسية",
        "details_btn": "التفاصيل",
        "order_btn": "طلب عرض سعر",
        "sent": "شكراً لك. أُرسل طلبك {ref} إلى فريقنا التجاري وسيؤكد المدير السعر قريباً.",
        "cancelled": "تم إلغاء الطلب. يمكنك البدء من جديد من القائمة.",
        "price_on_request": "السعر عند الطلب",
        "code": "الرمز",
        "product": "المنتج",
        "quantity": "الكمية",
        "price": "السعر",
        "unit": "الوحدة",
        "empty": "لا توجد منتجات متاحة حالياً.",
        "list_title": "المنتجات والخدمات",
        "list_hint": "اضغط على فئة لعرض المنتجات أو أرسل رمز المنتج (مثلاً 101).",
        "approved": "خبر سار. وافق المدير على طلبك {ref}:\n{summary}\nسيتواصل فريقنا معك لإتمام الإجراءات.",
        "rejected": "تعذر اعتماد الطلب {ref} بصيغته الحالية. سيتواصل فريقنا معك بخيارات بديلة.",
        "expired": "طلبك {ref} ما زال قيد المراجعة. سنعود إليك خلال ساعات العمل.",
        "my_requests_title": "طلباتك الأخيرة:",
        "no_requests": "لا توجد طلبات بعد. اختر منتجاً من القائمة لإرسال طلب.",
        "unit_service": "خدمة",
        "unit_kg": "كجم",
        "unit_liter": "لتر",
        "unit_barrel": "برميل",
        "unit_metric ton": "طن",
        "unit_ton": "طن",
        "unit_piece": "قطعة",
    },
    "tr": {
        "pick_category": "Bir kategori seçin:",
        "pick_product": "Bir ürün seçin:",
        "pick_qty": "Ne kadar ihtiyacınız var?",
        "qty_custom": "Başka miktar",
        "qty_prompt": "Miktarı sayı olarak gönderin (örneğin 500).",
        "qty_invalid": "Lütfen yalnızca sayı gönderin, örneğin 500.",
        "confirm": "Lütfen talebinizi onaylayın:",
        "confirm_btn": "Talebi gönder",
        "cancel_btn": "İptal",
        "back": "Geri",
        "main_menu": "Ana menü",
        "details_btn": "Ayrıntılar",
        "order_btn": "Teklif iste",
        "sent": "Teşekkürler. {ref} numaralı talebiniz ticari ekibimize iletildi. Yönetici fiyatı kısa süre içinde onaylayacak.",
        "cancelled": "Talep iptal edildi. Menüden yeniden başlayabilirsiniz.",
        "price_on_request": "fiyat talep üzerine",
        "code": "Kod",
        "product": "Ürün",
        "quantity": "Miktar",
        "price": "Fiyat",
        "unit": "Birim",
        "empty": "Şu anda ürün bulunmuyor.",
        "list_title": "Ürünler ve hizmetler",
        "list_hint": "Ürünleri görmek için bir kategoriye dokunun veya ürün kodunu gönderin (örneğin 101).",
        "approved": "İyi haber. {ref} numaralı talebiniz yöneticimiz tarafından onaylandı:\n{summary}\nEkibimiz sizinle iletişime geçecek.",
        "rejected": "{ref} numaralı talebiniz bu haliyle onaylanamadı. Ekibimiz alternatiflerle sizinle iletişime geçecek.",
        "expired": "{ref} numaralı talebiniz hâlâ inceleniyor. Çalışma saatleri içinde size döneceğiz.",
        "my_requests_title": "Son talepleriniz:",
        "no_requests": "Henüz talebiniz yok. Menüden bir ürün seçin.",
        "unit_service": "hizmet",
        "unit_kg": "kg",
        "unit_liter": "L",
        "unit_barrel": "varil",
        "unit_metric ton": "ton",
        "unit_ton": "ton",
        "unit_piece": "adet",
    },
    "de": {
        "pick_category": "Wählen Sie eine Kategorie:",
        "pick_product": "Wählen Sie ein Produkt:",
        "pick_qty": "Welche Menge benötigen Sie?",
        "qty_custom": "Andere Menge",
        "qty_prompt": "Senden Sie die Menge als Zahl (z. B. 500).",
        "qty_invalid": "Bitte nur eine Zahl senden, z. B. 500.",
        "confirm": "Bitte bestätigen Sie Ihre Anfrage:",
        "confirm_btn": "Anfrage senden",
        "cancel_btn": "Abbrechen",
        "back": "Zurück",
        "main_menu": "Hauptmenü",
        "details_btn": "Details",
        "order_btn": "Angebot anfordern",
        "sent": "Vielen Dank. Ihre Anfrage {ref} wurde an unser Vertriebsteam gesendet. Ein Manager bestätigt den Preis in Kürze.",
        "cancelled": "Anfrage abgebrochen. Sie können im Menü neu beginnen.",
        "price_on_request": "Preis auf Anfrage",
        "code": "Code",
        "product": "Produkt",
        "quantity": "Menge",
        "price": "Preis",
        "unit": "Einheit",
        "empty": "Derzeit sind keine Produkte verfügbar.",
        "list_title": "Produkte & Dienstleistungen",
        "list_hint": "Tippen Sie auf eine Kategorie oder senden Sie einen Produktcode (z. B. 101).",
        "approved": "Gute Nachricht. Ihre Anfrage {ref} wurde von unserem Manager genehmigt:\n{summary}\nUnser Team meldet sich zur Abwicklung.",
        "rejected": "Ihre Anfrage {ref} konnte so nicht genehmigt werden. Unser Team meldet sich mit Alternativen.",
        "expired": "Ihre Anfrage {ref} wird noch geprüft. Wir melden uns während der Geschäftszeiten.",
        "my_requests_title": "Ihre letzten Anfragen:",
        "no_requests": "Noch keine Anfragen. Wählen Sie ein Produkt im Menü.",
        "unit_service": "Leistung",
        "unit_metric ton": "t",
        "unit_ton": "t",
        "unit_barrel": "bbl",
        "unit_piece": "Stk.",
    },
    "fr": {
        "pick_category": "Choisissez une catégorie :",
        "pick_product": "Choisissez un produit :",
        "pick_qty": "Quelle quantité vous faut-il ?",
        "qty_custom": "Autre quantité",
        "qty_prompt": "Envoyez la quantité en chiffres (par exemple 500).",
        "qty_invalid": "Veuillez envoyer un nombre, par exemple 500.",
        "confirm": "Veuillez confirmer votre demande :",
        "confirm_btn": "Envoyer la demande",
        "cancel_btn": "Annuler",
        "back": "Retour",
        "main_menu": "Menu principal",
        "details_btn": "Détails",
        "order_btn": "Demander un devis",
        "sent": "Merci. Votre demande {ref} a été transmise à notre équipe commerciale. Un responsable confirmera le prix rapidement.",
        "cancelled": "Demande annulée. Vous pouvez recommencer depuis le menu.",
        "price_on_request": "prix sur demande",
        "code": "Code",
        "product": "Produit",
        "quantity": "Quantité",
        "price": "Prix",
        "unit": "Unité",
        "empty": "Aucun produit disponible pour le moment.",
        "list_title": "Produits & services",
        "list_hint": "Touchez une catégorie ou envoyez un code produit (par exemple 101).",
        "approved": "Bonne nouvelle. Votre demande {ref} a été approuvée par notre responsable :\n{summary}\nNotre équipe vous contactera pour finaliser.",
        "rejected": "Votre demande {ref} n'a pas pu être approuvée en l'état. Notre équipe vous proposera des alternatives.",
        "expired": "Votre demande {ref} est toujours en cours d'examen. Nous reviendrons vers vous pendant les heures ouvrées.",
        "my_requests_title": "Vos demandes récentes :",
        "no_requests": "Aucune demande pour l'instant. Choisissez un produit dans le menu.",
        "unit_service": "service",
        "unit_metric ton": "t",
        "unit_ton": "t",
        "unit_barrel": "bbl",
        "unit_piece": "pcs",
    },
    "es": {
        "pick_category": "Elija una categoría:",
        "pick_product": "Elija un producto:",
        "pick_qty": "¿Qué cantidad necesita?",
        "qty_custom": "Otra cantidad",
        "qty_prompt": "Envíe la cantidad como número (por ejemplo 500).",
        "qty_invalid": "Envíe solo un número, por ejemplo 500.",
        "confirm": "Confirme su solicitud:",
        "confirm_btn": "Enviar solicitud",
        "cancel_btn": "Cancelar",
        "back": "Atrás",
        "main_menu": "Menú principal",
        "details_btn": "Detalles",
        "order_btn": "Solicitar cotización",
        "sent": "Gracias. Su solicitud {ref} fue enviada a nuestro equipo comercial. Un gerente confirmará el precio en breve.",
        "cancelled": "Solicitud cancelada. Puede empezar de nuevo desde el menú.",
        "price_on_request": "precio a consultar",
        "code": "Código",
        "product": "Producto",
        "quantity": "Cantidad",
        "price": "Precio",
        "unit": "Unidad",
        "empty": "No hay productos disponibles ahora mismo.",
        "list_title": "Productos y servicios",
        "list_hint": "Toque una categoría o envíe un código de producto (por ejemplo 101).",
        "approved": "Buenas noticias. Su solicitud {ref} fue aprobada por nuestro gerente:\n{summary}\nNuestro equipo le contactará para finalizar.",
        "rejected": "Su solicitud {ref} no pudo aprobarse tal como se envió. Nuestro equipo le contactará con alternativas.",
        "expired": "Su solicitud {ref} sigue en revisión. Le responderemos en horario laboral.",
        "my_requests_title": "Sus solicitudes recientes:",
        "no_requests": "Aún no tiene solicitudes. Elija un producto del menú.",
        "unit_service": "servicio",
        "unit_metric ton": "t",
        "unit_ton": "t",
        "unit_barrel": "bbl",
        "unit_piece": "uds",
    },
    "ru": {
        "pick_category": "Выберите категорию:",
        "pick_product": "Выберите продукт:",
        "pick_qty": "Какой объём вам нужен?",
        "qty_custom": "Другое количество",
        "qty_prompt": "Отправьте количество числом (например 500).",
        "qty_invalid": "Пожалуйста, отправьте только число, например 500.",
        "confirm": "Пожалуйста, подтвердите запрос:",
        "confirm_btn": "Отправить запрос",
        "cancel_btn": "Отмена",
        "back": "Назад",
        "main_menu": "Главное меню",
        "details_btn": "Подробнее",
        "order_btn": "Запросить цену",
        "sent": "Спасибо. Ваш запрос {ref} передан коммерческому отделу. Менеджер подтвердит цену в ближайшее время.",
        "cancelled": "Запрос отменён. Вы можете начать заново из меню.",
        "price_on_request": "цена по запросу",
        "code": "Код",
        "product": "Продукт",
        "quantity": "Количество",
        "price": "Цена",
        "unit": "Ед.",
        "empty": "Сейчас нет доступных продуктов.",
        "list_title": "Продукты и услуги",
        "list_hint": "Нажмите на категорию или отправьте код продукта (например 101).",
        "approved": "Хорошие новости. Ваш запрос {ref} одобрен менеджером:\n{summary}\nНаша команда свяжется с вами для оформления.",
        "rejected": "Запрос {ref} не может быть одобрен в текущем виде. Наша команда предложит альтернативы.",
        "expired": "Запрос {ref} всё ещё на рассмотрении. Мы ответим в рабочее время.",
        "my_requests_title": "Ваши последние запросы:",
        "no_requests": "Запросов пока нет. Выберите продукт в меню.",
        "unit_service": "услуга",
        "unit_metric ton": "т",
        "unit_ton": "т",
        "unit_barrel": "барр.",
        "unit_piece": "шт.",
    },
}

# Quantity presets per unit family. Services are "1 request"; bulk products
# use industry-typical lot sizes.
QTY_PRESETS: dict[str, tuple[int, ...]] = {
    "service": (1,),
    "metric ton": (100, 500, 1000, 5000),
    "ton": (100, 500, 1000, 5000),
    "barrel": (1000, 5000, 10000, 50000),
    "liter": (1000, 5000, 20000, 50000),
    "kg": (100, 500, 1000, 5000),
    "piece": (1, 5, 10, 50),
}
DEFAULT_QTY_PRESETS: tuple[int, ...] = (1, 10, 100, 1000)
MAX_QUANTITY = 10_000_000

_QTY_RE = re.compile(r"[-+]?\d[\d,\.\s]*")
_ARABIC_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def t(lang: str, key: str, **kwargs: Any) -> str:
    """Customer text for the catalog / order flow. English fallback per key."""
    code = (lang or "en").lower().strip()
    table = CATALOG_TEXT.get(code) or {}
    text = table.get(key) or CATALOG_TEXT["en"].get(key) or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text


def _as_dict(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, (str, bytes)) and raw:
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except (ValueError, TypeError):
            return {}
    return {}


def product_name(row: dict[str, Any], lang: str) -> str:
    """Display name for *lang*: names[lang] → name_en → legacy name_ar → sku."""
    code = (lang or "en").lower().strip()
    names = _as_dict(row.get("names"))
    picked = str(names.get(code) or "").strip()
    if picked:
        return picked
    en = str(row.get("name_en") or "").strip()
    if en:
        return en
    if code == "ar":
        legacy = str(row.get("name_ar") or "").strip()
        if legacy:
            return legacy
    return str(row.get("sku") or row.get("code") or "").strip()


def product_title(row: dict[str, Any], lang: str) -> str:
    """One-line marketing title (subtitle) for *lang*; may be empty."""
    code = (lang or "en").lower().strip()
    titles = _as_dict(row.get("titles"))
    picked = str(titles.get(code) or "").strip()
    if picked:
        return picked
    return str(row.get("title_en") or "").strip()


def product_description(row: dict[str, Any], lang: str) -> str:
    code = (lang or "en").lower().strip()
    descs = _as_dict(row.get("descriptions"))
    picked = str(descs.get(code) or "").strip()
    if picked:
        return picked
    if code == "ar":
        legacy = str(row.get("description_ar") or "").strip()
        if legacy:
            return legacy
    return str(row.get("description_en") or "").strip()


def category_name(cat: dict[str, Any] | None, key: str, lang: str) -> str:
    code = (lang or "en").lower().strip()
    if cat:
        names = _as_dict(cat.get("names"))
        picked = str(names.get(code) or "").strip()
        if picked:
            return picked
        en = str(cat.get("name_en") or "").strip()
        if en:
            return en
    return key.replace("-", " ").strip().title() or "Other"


def unit_label(unit: str, lang: str) -> str:
    u = (unit or "").strip().lower()
    if not u:
        return ""
    return t(lang, f"unit_{u}") if f"unit_{u}" in CATALOG_TEXT["en"] else u


def format_money(amount: Any, currency: str, lang: str) -> str:
    """``1,250.00 USD`` or the localized *price on request* when zero/empty."""
    try:
        value = float(amount or 0)
    except (TypeError, ValueError):
        value = 0.0
    if value <= 0:
        return t(lang, "price_on_request")
    text = f"{value:,.2f}".rstrip("0").rstrip(".") if value != int(value) else f"{int(value):,}"
    return f"{text} {currency or 'USD'}".strip()


def product_price(row: dict[str, Any]) -> float:
    for key in ("unit_price", "base_price"):
        try:
            value = float(row.get(key) or 0)
        except (TypeError, ValueError):
            value = 0.0
        if value > 0:
            return value
    return 0.0


def product_code(row: dict[str, Any]) -> str:
    return str(row.get("code") or row.get("sku") or "").strip()


def parse_quantity(text: str) -> int | None:
    """``"500"``, ``"1,000"``, ``"۵۰۰"`` → int; anything else → None."""
    raw = (text or "").translate(_ARABIC_DIGITS).replace("٫", ".").strip()
    match = _QTY_RE.search(raw)
    if not match:
        return None
    if match.group(0).lstrip().startswith("-"):
        return None
    digits = re.sub(r"[^\d]", "", match.group(0))
    if not digits:
        return None
    value = int(digits)
    if value <= 0 or value > MAX_QUANTITY:
        return None
    return value


def qty_presets(unit: str) -> tuple[int, ...]:
    return QTY_PRESETS.get((unit or "").strip().lower(), DEFAULT_QTY_PRESETS)


def format_quantity(qty: int, unit: str, lang: str) -> str:
    label = unit_label(unit, lang)
    return f"{qty:,} {label}".strip()


# ---------------------------------------------------------------------------
# Rendering — plain text lines, no Markdown, at most one emoji per line.
# ---------------------------------------------------------------------------


def group_by_category(products: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in products:
        key = str(row.get("category") or "other").strip() or "other"
        grouped.setdefault(key, []).append(row)
    return grouped


def order_categories(
    keys: list[str], categories: dict[str, dict[str, Any]] | None = None
) -> list[str]:
    cats = categories or {}

    def sort_key(k: str) -> tuple[int, str]:
        meta = cats.get(k) or {}
        try:
            order = int(meta.get("sort_order", 100))
        except (TypeError, ValueError):
            order = 100
        return (order, k)

    return sorted(keys, key=sort_key)


def render_product_line(row: dict[str, Any], lang: str) -> str:
    """``203 · Diesel 10 PPM — 640 USD / MT`` (or price on request)."""
    code = product_code(row)
    name = product_name(row, lang)
    price = product_price(row)
    unit = unit_label(str(row.get("unit") or ""), lang)
    price_text = format_money(price, str(row.get("currency") or "USD"), lang)
    if price > 0 and unit:
        price_text = f"{price_text} / {unit}"
    return f"{code} · {name} — {price_text}" if code else f"{name} — {price_text}"


def render_catalog(
    products: list[dict[str, Any]],
    *,
    language: str = "en",
    categories: dict[str, dict[str, Any]] | None = None,
) -> str:
    """Clean per-language text list (used when buttons are unavailable)."""
    lang = (language or "en").lower().strip()
    if not products:
        return t(lang, "empty")
    grouped = group_by_category(products)
    lines: list[str] = [t(lang, "list_title")]
    for key in order_categories(list(grouped), categories):
        meta = (categories or {}).get(key)
        icon = str((meta or {}).get("icon") or "").strip()
        header = category_name(meta, key, lang)
        lines.append("")
        lines.append(f"{icon} {header}".strip())
        for row in grouped[key]:
            lines.append("- " + render_product_line(row, lang))
    lines.append("")
    lines.append(t(lang, "list_hint"))
    return "\n".join(lines)


def render_product_card(row: dict[str, Any], lang: str) -> str:
    """Detail text shown above the Request-a-quote button."""
    lines = [product_name(row, lang)]
    title = product_title(row, lang)
    if title:
        lines.append(title)
    lines.append("")
    lines.append(f"{t(lang, 'code')}: {product_code(row)}")
    price = product_price(row)
    unit = unit_label(str(row.get("unit") or ""), lang)
    price_text = format_money(price, str(row.get("currency") or "USD"), lang)
    if price > 0 and unit:
        price_text = f"{price_text} / {unit}"
    lines.append(f"{t(lang, 'price')}: {price_text}")
    desc = product_description(row, lang)
    if desc:
        lines.append("")
        lines.append(desc[:600])
    return "\n".join(lines)


def order_summary(row: dict[str, Any], qty: int, lang: str) -> str:
    unit = str(row.get("unit") or "")
    price = product_price(row)
    currency = str(row.get("currency") or "USD")
    lines = [
        f"{t(lang, 'product')}: {product_name(row, lang)} ({t(lang, 'code')} {product_code(row)})",
        f"{t(lang, 'quantity')}: {format_quantity(qty, unit, lang)}",
    ]
    if price > 0:
        lines.append(f"{t(lang, 'price')}: {format_money(price * qty, currency, lang)}")
    else:
        lines.append(f"{t(lang, 'price')}: {t(lang, 'price_on_request')}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Purchase flow — callback protocol
# ---------------------------------------------------------------------------
# cat_<key>            show products of a category
# prod_<code>          show product card
# qty_<code>_<n>       pick a preset quantity
# qty_<code>_custom    ask for a typed quantity
# ord_<code>_<n>       confirm → create quote request (HITL)
# ord_cancel           cancel
# shop                 back to categories


@dataclass(frozen=True)
class FlowAction:
    kind: str  # categories | products | product | quantity | ask_qty | confirm | submit | cancel | unknown
    code: str = ""
    category: str = ""
    quantity: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


def parse_callback(data: str) -> FlowAction:
    raw = (data or "").strip()
    if raw in ("shop", "menu_shop", "menu_prices", "prices"):
        return FlowAction("categories")
    if raw == "ord_cancel":
        return FlowAction("cancel")
    if raw.startswith("cat_"):
        return FlowAction("products", category=raw[4:])
    if raw.startswith("prod_"):
        return FlowAction("product", code=raw[5:])
    if raw.startswith("qty_"):
        parts = raw.split("_")
        if len(parts) >= 3:
            code = "_".join(parts[1:-1])
            tail = parts[-1]
            if tail == "custom":
                return FlowAction("ask_qty", code=code)
            if tail.isdigit():
                return FlowAction("confirm", code=code, quantity=int(tail))
    if raw.startswith("ord_"):
        parts = raw.split("_")
        if len(parts) >= 3 and parts[-1].isdigit():
            return FlowAction("submit", code="_".join(parts[1:-1]), quantity=int(parts[-1]))
    return FlowAction("unknown")


def category_buttons(
    grouped: dict[str, list[dict[str, Any]]],
    lang: str,
    categories: dict[str, dict[str, Any]] | None = None,
) -> list[list[tuple[str, str]]]:
    """[(label, callback_data)] rows for the category picker."""
    rows: list[list[tuple[str, str]]] = []
    for key in order_categories(list(grouped), categories):
        meta = (categories or {}).get(key)
        icon = str((meta or {}).get("icon") or "").strip()
        label = f"{icon} {category_name(meta, key, lang)} ({len(grouped[key])})".strip()
        rows.append([(label, f"cat_{key}"[:64])])
    rows.append([(t(lang, "main_menu"), "menu_home")])
    return rows


def product_buttons(products: list[dict[str, Any]], lang: str) -> list[list[tuple[str, str]]]:
    rows: list[list[tuple[str, str]]] = []
    for row in products:
        code = product_code(row)
        label = f"{code} · {product_name(row, lang)}"[:60]
        rows.append([(label, f"prod_{code}"[:64])])
    rows.append([(t(lang, "back"), "shop"), (t(lang, "main_menu"), "menu_home")])
    return rows


def quantity_buttons(row: dict[str, Any], lang: str) -> list[list[tuple[str, str]]]:
    code = product_code(row)
    unit = str(row.get("unit") or "")
    presets = qty_presets(unit)
    line: list[tuple[str, str]] = []
    rows: list[list[tuple[str, str]]] = []
    for qty in presets:
        line.append((format_quantity(qty, unit, lang), f"qty_{code}_{qty}"))
        if len(line) == 2:
            rows.append(line)
            line = []
    if line:
        rows.append(line)
    if unit.strip().lower() != "service":
        rows.append([(t(lang, "qty_custom"), f"qty_{code}_custom")])
    rows.append(
        [
            (t(lang, "back"), f"cat_{row.get('category') or 'other'}"[:64]),
            (t(lang, "main_menu"), "menu_home"),
        ]
    )
    return rows


def confirm_buttons(row: dict[str, Any], qty: int, lang: str) -> list[list[tuple[str, str]]]:
    code = product_code(row)
    return [
        [(t(lang, "confirm_btn"), f"ord_{code}_{qty}")],
        [(t(lang, "back"), f"prod_{code}"), (t(lang, "cancel_btn"), "ord_cancel")],
    ]
