"""Tiny example pricing engine — public API + private helpers + 'proprietary tables'.

This file exists to demonstrate how `cloak context` and `cloak obfuscate` treat each kind
of definition. It is intentionally small and self-contained.
"""

from dataclasses import dataclass


_TIER_DISCOUNTS = {
    "basic": 0.00,
    "pro": 0.10,
    "enterprise": 0.20,
}

_REGIONAL_MARKUPS = {
    "domestic": 1.00,
    "international": 1.15,
}


@dataclass
class Customer:
    customer_id: str
    tier: str
    region: str


def calculate_total(customer: Customer, subtotal: float) -> float:
    """Public API: produce a final price for a customer + subtotal."""
    discount = _apply_tier(customer.tier)
    markup = _apply_region(customer.region)
    return subtotal * (1 - discount) * markup


def _apply_tier(tier: str) -> float:
    """Return the discount fraction for a tier."""
    return _TIER_DISCOUNTS.get(tier, 0.0)


def _apply_region(region: str) -> float:
    """Return the price multiplier for a region."""
    return _REGIONAL_MARKUPS.get(region, 1.0)
