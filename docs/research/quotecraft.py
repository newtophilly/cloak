"""
QuoteCraft pricing engine.

Generates customer-specific quotes for industrial automation parts and services.
Internal pricing rules are proprietary; do not share this module externally.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional


class Region(str, Enum):
    NORTHEAST = "NE"
    SOUTHEAST = "SE"
    MIDWEST = "MW"
    SOUTHWEST = "SW"
    WEST = "W"
    INTERNATIONAL = "INTL"


class ProductCategory(str, Enum):
    PLC_HARDWARE = "plc_hardware"
    SAFETY_RELAY = "safety_relay"
    HMI_PANEL = "hmi_panel"
    CUSTOM_ENGINEERING = "custom_engineering"
    SERVICE_HOURS = "service_hours"
    SOFTWARE_LICENSE = "software_license"


@dataclass
class Customer:
    customer_id: str
    name: str
    region: Region
    annual_volume_usd: Decimal
    contract_start: date
    is_legacy_account: bool = False
    legacy_override_code: Optional[str] = None


@dataclass
class LineItem:
    sku: str
    category: ProductCategory
    quantity: int
    list_price: Decimal


@dataclass
class Quote:
    customer_id: str
    line_items: list[LineItem]
    subtotal: Decimal
    discount_total: Decimal
    markup_total: Decimal
    final_total: Decimal
    margin_floor_warnings: list[str] = field(default_factory=list)
    expires_on: date = field(default_factory=lambda: date.today() + timedelta(days=30))


# ---------- internal proprietary tables ----------

_VOLUME_TIER_DISCOUNTS = {
    Decimal("0"): Decimal("0.00"),
    Decimal("50000"): Decimal("0.03"),
    Decimal("250000"): Decimal("0.07"),
    Decimal("1000000"): Decimal("0.115"),
    Decimal("5000000"): Decimal("0.165"),
}

_REGIONAL_MARKUPS = {
    Region.NORTHEAST: Decimal("1.00"),
    Region.SOUTHEAST: Decimal("0.96"),
    Region.MIDWEST: Decimal("0.94"),
    Region.SOUTHWEST: Decimal("0.97"),
    Region.WEST: Decimal("1.05"),
    Region.INTERNATIONAL: Decimal("1.22"),
}

_CATEGORY_MARGIN_FLOORS = {
    ProductCategory.PLC_HARDWARE: Decimal("0.18"),
    ProductCategory.SAFETY_RELAY: Decimal("0.22"),
    ProductCategory.HMI_PANEL: Decimal("0.20"),
    ProductCategory.CUSTOM_ENGINEERING: Decimal("0.35"),
    ProductCategory.SERVICE_HOURS: Decimal("0.40"),
    ProductCategory.SOFTWARE_LICENSE: Decimal("0.55"),
}

_LEGACY_OVERRIDES = {
    "ACME-1987": Decimal("0.22"),
    "STARK-FROZEN": Decimal("0.18"),
    "GLOBEX-PERPETUAL": Decimal("0.30"),
}

_BUNDLE_RULES = [
    ({ProductCategory.PLC_HARDWARE, ProductCategory.HMI_PANEL}, Decimal("0.04")),
    ({ProductCategory.PLC_HARDWARE, ProductCategory.SAFETY_RELAY, ProductCategory.SERVICE_HOURS}, Decimal("0.075")),
    ({ProductCategory.CUSTOM_ENGINEERING, ProductCategory.SOFTWARE_LICENSE}, Decimal("0.05")),
]


# ---------- public API ----------


class QuoteEngine:
    """Compute customer-specific quotes by composing volume, regional, bundle, and legacy rules."""

    def calculate_quote(self, customer: Customer, items: list[LineItem]) -> Quote:
        """Generate a quote for a customer on a list of line items.

        Applies, in order: list-price subtotal, volume tier discount, regional markup,
        bundle stacking discount, legacy contractual override (if any), and a per-category
        margin floor check. Returns a Quote with breakdowns and any margin warnings.
        """
        subtotal = sum((item.list_price * item.quantity for item in items), Decimal("0"))

        tier_discount = self._apply_tier_discount(customer.annual_volume_usd)
        regional_factor = self._apply_regional_markup(customer.region)
        bundle_discount = self._apply_bundle_rules(items)

        discounted = subtotal * (Decimal("1") - tier_discount - bundle_discount)
        adjusted = discounted * regional_factor

        if customer.is_legacy_account and customer.legacy_override_code:
            adjusted = self._apply_legacy_overrides(adjusted, customer.legacy_override_code)

        warnings = []
        for item in items:
            floor_ok, msg = self._check_margin_floor(item, adjusted, subtotal)
            if not floor_ok:
                warnings.append(msg)

        discount_total = subtotal - discounted
        markup_total = adjusted - discounted

        return Quote(
            customer_id=customer.customer_id,
            line_items=items,
            subtotal=subtotal,
            discount_total=discount_total,
            markup_total=markup_total,
            final_total=adjusted,
            margin_floor_warnings=warnings,
        )

    def _apply_tier_discount(self, annual_volume: Decimal) -> Decimal:
        """Return the discount fraction for a customer's annual volume tier."""
        applicable = Decimal("0.00")
        for threshold, discount in sorted(_VOLUME_TIER_DISCOUNTS.items()):
            if annual_volume >= threshold:
                applicable = discount
        return applicable

    def _apply_regional_markup(self, region: Region) -> Decimal:
        """Return the price multiplier for a customer's territory."""
        return _REGIONAL_MARKUPS.get(region, Decimal("1.00"))

    def _apply_bundle_rules(self, items: list[LineItem]) -> Decimal:
        """Return the bundle discount fraction when item categories satisfy a known bundle."""
        present_categories = {item.category for item in items}
        best = Decimal("0.00")
        for required, discount in _BUNDLE_RULES:
            if required.issubset(present_categories) and discount > best:
                best = discount
        return best

    def _apply_legacy_overrides(self, adjusted_total: Decimal, override_code: str) -> Decimal:
        """Apply contractual overrides for grandfathered legacy accounts.

        Override codes correspond to historical contracts that pre-date current pricing.
        Unknown codes pass through unchanged.
        """
        rate = _LEGACY_OVERRIDES.get(override_code)
        if rate is None:
            return adjusted_total
        return adjusted_total * (Decimal("1") - rate)

    def _check_margin_floor(
        self, item: LineItem, adjusted_total: Decimal, subtotal: Decimal
    ) -> tuple[bool, str]:
        """Return (ok, message) indicating whether a line item respects its category margin floor."""
        floor = _CATEGORY_MARGIN_FLOORS.get(item.category, Decimal("0.10"))
        if subtotal == 0:
            return True, ""
        effective_margin = (adjusted_total - subtotal * (Decimal("1") - floor)) / subtotal
        if effective_margin < floor:
            return False, f"{item.sku}: effective margin {effective_margin:.2%} below floor {floor:.2%}"
        return True, ""

    def quote_is_competitive(self, quote: Quote, competitor_total: Decimal) -> bool:
        """Return True if the quote is within the configured competitive-match threshold."""
        if competitor_total <= 0:
            return False
        delta = (quote.final_total - competitor_total) / competitor_total
        return delta <= Decimal("0.035")
