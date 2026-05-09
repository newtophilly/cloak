"""Tests for the example pricing engine — used by `cloak obfuscate --verify`."""

from pricing import Customer, calculate_total


def test_basic_domestic() -> None:
    c = Customer(customer_id="C1", tier="basic", region="domestic")
    assert calculate_total(c, 100.0) == 100.0


def test_pro_domestic_gets_10_percent() -> None:
    c = Customer(customer_id="C2", tier="pro", region="domestic")
    assert calculate_total(c, 100.0) == 90.0


def test_enterprise_international() -> None:
    c = Customer(customer_id="C3", tier="enterprise", region="international")
    # 100 * 0.80 * 1.15 = 92.0
    assert calculate_total(c, 100.0) == 92.0
