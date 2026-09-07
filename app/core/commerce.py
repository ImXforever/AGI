"""Shared commerce primitives.

All credit purchases go through this module so the Telegram bot and Mini App
cannot diverge on balances, ledgers, sales counters, or idempotency.

Converted from SQLite to async PostgreSQL (asyncpg).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import get_config
from app.logging_setup import get_logger

log = get_logger(__name__)

CAPO_OVERRIDE_PCT: float = 0.10
REF_COMMISSION_SHARE: float = 0.05


class CommerceError(Exception):
    """A safe, user-facing commerce failure."""


@dataclass(frozen=True)
class PurchaseResult:
    product: dict
    buyer_id: int
    seller_id: int
    price: int
    commission: int
    seller_earning: int
    payment_method: str


async def _get_product(pool, product_id: int) -> dict | None:
    row = await pool.fetchrow(
        "SELECT id, creator_id, price_credits, title, is_active, status "
        "FROM products WHERE id = $1",
        product_id,
    )
    return dict(row) if row else None


async def _get_seller_info(pool, seller_id: int) -> tuple:
    row = await pool.fetchrow(
        "SELECT user_id, COALESCE(is_banned, FALSE), COALESCE(seller_plan, 'free') "
        "FROM users WHERE user_id = $1",
        seller_id,
    )
    return row


async def purchase_with_credits(
    buyer_id: int,
    product_id: int,
    *,
    price_override: int | None = None,
    payment_method: str = "credits",
    coupon_id: int | None = None,
) -> PurchaseResult:
    """Atomically purchase a product with credits.

    The unique purchase index makes retries idempotent. The balance check and
    all ledger/counter updates happen in one PostgreSQL transaction. A caller
    must perform non-financial notifications after this function returns.
    """
    from app.storage.pg import get_pool

    pool = await get_pool()

    product = await _get_product(pool, product_id)
    if not product or not product.get("is_active") or product.get("status") != "approved":
        raise CommerceError("محصول در دسترس نیست")
    if product["creator_id"] == buyer_id:
        raise CommerceError("محصول خودت است")

    seller_id = int(product["creator_id"])
    original_price = int(product["price_credits"])
    price = int(price_override if price_override is not None else original_price)
    if price < 1:
        raise CommerceError("قیمت محصول نامعتبر است")
    if payment_method not in {"credits", "stars"}:
        raise CommerceError("روش پرداخت نامعتبر است")

    seller_plan = "free"
    async with pool.acquire() as conn:
        async with conn.transaction():
            seller_row = await conn.fetchrow(
                "SELECT user_id, COALESCE(is_banned, FALSE), COALESCE(seller_plan, 'free') "
                "FROM users WHERE user_id = $1",
                seller_id,
            )
            if not seller_row:
                raise CommerceError("فروشنده معتبر نیست")
            if seller_row[1]:
                raise CommerceError("فروشنده مسدود است")
            seller_plan = seller_row[2]

            if coupon_id is not None:
                coupon_row = await conn.fetchrow(
                    "SELECT percent FROM coupons WHERE id = $1 AND owner_id = $2 AND active = TRUE "
                    "AND (max_uses = 0 OR uses < max_uses)",
                    coupon_id,
                    seller_id,
                )
                if not coupon_row:
                    raise CommerceError("کد تخفیف منقضی یا نامعتبر است")
                calculated = max(1, round(original_price * (100 - coupon_row[0]) / 100))
                if price != calculated:
                    price = calculated
                result = await conn.execute(
                    "UPDATE coupons SET uses = uses + 1 WHERE id = $1 AND active = TRUE "
                    "AND (max_uses = 0 OR uses < max_uses)",
                    coupon_id,
                )
                if result == "UPDATE 0":
                    raise CommerceError("ظرفیت کد تخفیف همین الان تمام شد")

            comm_rate = 0.05 if seller_plan == "pro" else 0.15
            commission = int(price * comm_rate)
            earning = price - commission

            buyer_row = await conn.fetchrow(
                "SELECT credits, COALESCE(is_banned, FALSE) FROM users WHERE user_id = $1",
                buyer_id,
            )
            if not buyer_row or buyer_row[1]:
                raise CommerceError("حساب در دسترس نیست")

            result = await conn.execute(
                "INSERT INTO purchases (buyer_id, product_id, price_credits, payment_method) "
                "VALUES ($1, $2, $3, $4) ON CONFLICT DO NOTHING",
                buyer_id,
                product_id,
                price,
                payment_method,
            )
            if result == "INSERT 0 0":
                raise CommerceError("قبلاً این محصول را خریده‌ای")

            if payment_method == "credits":
                result = await conn.execute(
                    "UPDATE users SET credits = credits - $1, total_spent = total_spent + $1 "
                    "WHERE user_id = $2 AND credits >= $1",
                    price,
                    buyer_id,
                )
                if result == "UPDATE 0":
                    raise CommerceError("کردیت کافی نداری")
                buyer_amount = -price
            else:
                buyer_amount = 0

            await conn.execute(
                "UPDATE users SET credits = credits + $1, total_earned = total_earned + $1, "
                "products_sold = products_sold + 1 WHERE user_id = $2",
                earning,
                seller_id,
            )
            await conn.execute(
                "UPDATE products SET sales_count = sales_count + 1 WHERE id = $1",
                product_id,
            )
            await conn.execute(
                "INSERT INTO transactions (user_id, amount, tx_type, reference_id, description) "
                "VALUES ($1, $2, 'purchase', $3, $4)",
                buyer_id,
                buyer_amount,
                product_id,
                f"Purchased: {product['title']}",
            )
            await conn.execute(
                "INSERT INTO transactions (user_id, amount, tx_type, reference_id, description) "
                "VALUES ($1, $2, 'sale', $3, $4)",
                seller_id,
                earning,
                product_id,
                f"Sold: {product['title']}",
            )

    log.info(
        "purchase_completed",
        extra={
            "buyer_id": buyer_id,
            "seller_id": seller_id,
            "product_id": product_id,
            "price": price,
            "commission": commission,
            "earning": earning,
        },
    )
    return PurchaseResult(
        product=product,
        buyer_id=buyer_id,
        seller_id=seller_id,
        price=price,
        commission=commission,
        seller_earning=earning,
        payment_method=payment_method,
    )


async def apply_sale_network_effects(result: PurchaseResult, bot=None) -> None:
    """Apply first-sale promotion and referral/upline rewards once.

    This is deliberately outside the money transaction: a notification or
    referral side effect can fail without rolling back the actual purchase.
    """
    from app.storage.pg import get_pool

    pool = await get_pool()
    seller = result.seller_id

    role_row = await pool.fetchrow(
        "SELECT role FROM user_roles WHERE user_id = $1",
        seller,
    )
    current_role = role_row["role"] if role_row else "associate"

    if current_role == "associate":
        await pool.execute(
            "UPDATE user_roles SET role = 'soldier', granted_by = 0 WHERE user_id = $1",
            seller,
        )
        if bot:
            try:
                await bot.send_message(
                    seller,
                    "🪖 اولین فروشت ثبت شد و از کارآموز به **سرباز** ارتقا گرفتی.",
                    parse_mode="Markdown",
                )
            except Exception:
                pass

    seller_ref_row = await pool.fetchrow(
        "SELECT referrer_id FROM referrals WHERE user_id = $1",
        seller,
    )
    seller_ref = seller_ref_row["referrer_id"] if seller_ref_row else None
    if seller_ref and result.commission > 0:
        ref_role_row = await pool.fetchrow(
            "SELECT role FROM user_roles WHERE user_id = $1",
            seller_ref,
        )
        ref_role = ref_role_row["role"] if ref_role_row else "associate"
        if ref_role in ("capo", "underboss", "godfather"):
            override = int(result.commission * CAPO_OVERRIDE_PCT)
            if override > 0:
                await pool.execute(
                    "UPDATE users SET credits = credits + $1, total_earned = total_earned + $1 "
                    "WHERE user_id = $2",
                    override,
                    seller_ref,
                )
                await pool.execute(
                    "INSERT INTO transactions (user_id, amount, tx_type, reference_id, description) "
                    "VALUES ($1, $2, 'capo_override', $3, $4)",
                    seller_ref,
                    override,
                    result.product["id"],
                    f"Override on sale: {result.product['title']}",
                )

    referrer_row = await pool.fetchrow(
        "SELECT referrer_id FROM referrals WHERE user_id = $1",
        result.buyer_id,
    )
    referrer_id = referrer_row["referrer_id"] if referrer_row else None
    if referrer_id and result.commission > 0:
        share = int(result.commission * REF_COMMISSION_SHARE)
        if share > 0:
            await pool.execute(
                "UPDATE users SET credits = credits + $1, total_earned = total_earned + $1 "
                "WHERE user_id = $2",
                share,
                referrer_id,
            )
            await pool.execute(
                "INSERT INTO transactions (user_id, amount, tx_type, reference_id, description) "
                "VALUES ($1, $2, 'ref_commission', $3, $4)",
                referrer_id,
                share,
                result.product["id"],
                f"Lifetime share on sale to user {result.buyer_id}",
            )

    try:
        from app.core.referral import maybe_qualify_referral

        await maybe_qualify_referral(bot, result.buyer_id)
    except Exception:
        pass


async def refund_credits(
    user_id: int, amount: int, description: str, reference_id: int | None = None
) -> None:
    """Ledgered refund helper used by failed/manual withdrawal flows."""
    from app.storage.pg import get_pool

    if amount <= 0:
        return

    pool = await get_pool()
    await pool.execute(
        "UPDATE users SET credits = credits + $1, total_earned = total_earned + $1 "
        "WHERE user_id = $2",
        amount,
        user_id,
    )
    await pool.execute(
        "INSERT INTO transactions (user_id, amount, tx_type, reference_id, description) "
        "VALUES ($1, $2, 'refund', $3, $4)",
        user_id,
        amount,
        reference_id,
        description,
    )
    log.info(
        "refund_completed",
        extra={"user_id": user_id, "amount": amount, "description": description},
    )
