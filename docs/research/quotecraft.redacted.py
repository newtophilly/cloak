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
# [REDACTED BY CLOAK]


# ---------- public API ----------


class QuoteEngine:
    """Compute customer-specific quotes by composing volume, regional, bundle, and legacy rules."""

    def calculate_quote(self, customer: Customer, items: list[LineItem]) -> Quote:
        """Generate a quote for a customer on a list of line items.

        Applies, in order: list-price subtotal, volume tier discount, regional markup,
        bundle stacking discount, legacy contractual override (if any), and a per-category
        margin floor check. Returns a Quote with breakdowns and any margin warnings.
        """
        # [REDACTED BY CLOAK]
        ...

    def _apply_tier_discount(self, annual_volume: Decimal) -> Decimal:
        """Return the discount fraction for a customer's annual volume tier."""
        # [REDACTED BY CLOAK]
        ...

    def _apply_regional_markup(self, region: Region) -> Decimal:
        """Return the price multiplier for a customer's territory."""
        # [REDACTED BY CLOAK]
        ...

    def _apply_bundle_rules(self, items: list[LineItem]) -> Decimal:
        """Return the bundle discount fraction when item categories satisfy a known bundle."""
        # [REDACTED BY CLOAK]
        ...

    def _apply_legacy_overrides(self, adjusted_total: Decimal, override_code: str) -> Decimal:
        """Apply contractual overrides for grandfathered legacy accounts.

        Override codes correspond to historical contracts that pre-date current pricing.
        Unknown codes pass through unchanged.
        """
        # [REDACTED BY CLOAK]
        ...

    def _check_margin_floor(
        self, item: LineItem, adjusted_total: Decimal, subtotal: Decimal
    ) -> tuple[bool, str]:
        """Return (ok, message) indicating whether a line item respects its category margin floor."""
        # [REDACTED BY CLOAK]
        ...

    def quote_is_competitive(self, quote: Quote, competitor_total: Decimal) -> bool:
        """Return True if the quote is within the configured competitive-match threshold."""
        # [REDACTED BY CLOAK]
        ...
