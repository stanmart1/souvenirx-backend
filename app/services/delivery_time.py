"""
Delivery-time estimation service.

Pure Python — no database or external dependencies required.
"""
import math
from datetime import date, timedelta

# ── Production-time configuration ────────────────────────────────────────────
# category_slug → {base, per_100, max}
#   base     : minimum production days regardless of quantity
#   per_100  : additional days added per 100 units ordered
#   max      : hard cap on production days
PRODUCTION_DAYS: dict[str, dict] = {
    "mugs":       {"base": 2, "per_100": 0.5, "max": 7},
    "tshirts":    {"base": 3, "per_100": 0.5, "max": 10},
    "tote-bags":  {"base": 3, "per_100": 0.5, "max": 10},
    "plaques":    {"base": 4, "per_100": 1.0, "max": 14},
    "cards":      {"base": 2, "per_100": 0.3, "max": 7},
    "wristbands": {"base": 2, "per_100": 0.2, "max": 7},
    "default":    {"base": 3, "per_100": 0.5, "max": 10},
}


def _add_business_days(start: date, business_days: int) -> date:
    """Return a date that is `business_days` business days after `start`."""
    current = start
    remaining = business_days
    while remaining > 0:
        current += timedelta(days=1)
        # Monday=0 … Friday=4; skip Saturday(5) and Sunday(6)
        if current.weekday() < 5:
            remaining -= 1
    return current


def estimate_production_days(category_slug: str, quantity: int) -> tuple[int, int]:
    """
    Calculate production time for a given category and quantity.

    Returns:
        (min_days, max_days) as a tuple of ints
    """
    cfg = PRODUCTION_DAYS.get(category_slug, PRODUCTION_DAYS["default"])

    base: int = cfg["base"]
    per_100: float = cfg["per_100"]
    max_days: int = cfg["max"]

    # production_days = clamp(base + floor(quantity / 100) * per_100, base, max)
    raw_days: float = base + math.floor(quantity / 100) * per_100
    production_days: int = int(min(max(raw_days, base), max_days))

    min_days: int = max(1, production_days - 1)
    max_days_out: int = production_days

    return min_days, max_days_out


def estimate_delivery_window(
    category_slug: str,
    quantity: int,
    zone_min_days: int,
    zone_max_days: int,
) -> dict:
    """
    Estimate the full delivery window combining production + shipping time.

    Args:
        category_slug: product category slug (e.g. "mugs", "tshirts")
        quantity:      number of units ordered
        zone_min_days: minimum shipping days for the delivery zone
        zone_max_days: maximum shipping days for the delivery zone

    Returns:
        {
            production_min: int,
            production_max: int,
            shipping_min:   int,
            shipping_max:   int,
            total_min:      int,
            total_max:      int,
            earliest_date:  str,   # ISO date string
            latest_date:    str,   # ISO date string
            label:          str,   # e.g. "5–9 business days"
        }
    """
    production_min, production_max = estimate_production_days(category_slug, quantity)

    total_min: int = production_min + zone_min_days
    total_max: int = production_max + zone_max_days

    today = date.today()
    earliest = _add_business_days(today, total_min)
    latest = _add_business_days(today, total_max)

    label = f"{total_min}–{total_max} business days"

    return {
        "production_min": production_min,
        "production_max": production_max,
        "shipping_min": zone_min_days,
        "shipping_max": zone_max_days,
        "total_min": total_min,
        "total_max": total_max,
        "earliest_date": earliest.isoformat(),
        "latest_date": latest.isoformat(),
        "label": label,
    }
