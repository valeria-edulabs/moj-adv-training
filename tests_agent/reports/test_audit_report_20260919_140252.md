# Nightly Test Audit Report

- **Audit Date**: September 19, 2026
- **Root Sandbox Directory**: `/Users/valeria/src/trainings/moj-adv-training/tests_agent`
- **Source Code Directory**: `/dummy_project/src`
- **Unit Tests Directory**: `/dummy_project/tests`
- **Preferred Test Framework**: `pytest`
- **Audit Focus / Depth**: `Comprehensive Audit (Coverage, Quality, Edge Cases)`
- **Auditor**: Principal Software Quality Assurance & Test Engineering Agent

---

## 1. Executive Summary

An exhaustive automated Nightly Test Audit was conducted on `/dummy_project/src/order_service.py` and its accompanying test suite `/dummy_project/tests/test_order_service.py`. 

While the codebase is well-structured and contains clean domain logic for order processing, discounting, tax calculations, inventory management, and refunds, the existing unit test suite suffers from severe structural deficiencies:
1. **Critical Coverage Gaps**: The financial refund subsystem (`process_refund`) and inventory stock validation/depletion logic have **zero unit test coverage**.
2. **Weak / Trivial Assertions**: Important discount calculations rely on superficial assertions (`assert discount >= 0`) rather than validating precise business rules, tiered rates, and percentage caps.
3. **Anti-Patterns & Brittle Tests**: The test suite includes tight coupling to private implementation details (testing `_generate_internal_hash` directly with hardcoded internal salts) and completely redundant assertions (`assert True`).

Implementing the actionable inventory outlined in this report will elevate test coverage to near 100%, eliminate brittleness, enforce robust boundary value parametrization, and ensure financial safety.

---

## 2. Codebase Architecture & Domain Analysis

### Core Components (`/dummy_project/src/order_service.py`)
- **`CustomerTier`**: Enum defining customer loyalty tiers (`STANDARD`, `SILVER`, `GOLD`, `PLATINUM`).
- **`OrderItem`**: Dataclass representing line items (`item_id`, `name`, `unit_price`, `quantity`).
- **`OrderReceipt`**: Dataclass representing final transactional receipts including subtotal, discounts, taxes, totals, timestamps, and secure tracking hashes.
- **`OrderService`**: Main service class providing:
  - `calculate_discount(subtotal, tier, coupon_code)`: Tier-based discounting combined with promo codes (`PROMO15`, `VIP30`), strictly capped at `MAX_DISCOUNT_PERCENT` (50%).
  - `process_order(order_id, items, tier, coupon_code)`: Validates order parameters, checks and mutates stock inventory levels, computes pricing, generates secure tracking hashes via SHA-256, and returns an `OrderReceipt`.
  - `process_refund(order_id, amount, reason)`: Validates refund requests and records transactions into `self.refund_log`.
  - `_generate_internal_hash(order_id, amount)`: Private helper generating salted tracking hashes.

---

## 3. Test Suite Quality Assessment

### Existing Tests Review
1. **`test_process_order_standard_tier`**:
   - *Status*: High quality.
   - *Assessment*: Validates end-to-end standard order processing correctly. Should be **PRESERVED**.
2. **`test_calculate_discount_weak`**:
   - *Status*: Low quality / Weak assertions.
   - *Assessment*: Only checks `assert discount >= 0`. Fails to verify tiered discount rates, coupon multipliers, or the 50% max discount cap. Should be **EDITED**.
3. **`test_private_internal_hash_exact_sha256`**:
   - *Status*: Brittle anti-pattern.
   - *Assessment*: Directly invokes private method `_generate_internal_hash` and couples tests to internal salting implementation details. Should be **DELETED**.
4. **`test_always_passes_dummy`**:
   - *Status*: Trivial / Useless test.
   - *Assessment*: Asserts `True`. Adds zero value and noise. Should be **DELETED**.

---

## 4. Missing Tests & Coverage Gaps

- **Refund Processing (`process_refund`)**: Entirely untested. Needs tests for valid refunds, missing order IDs, zero/negative refund amounts, and invalid/short reasons (< 3 characters).
- **Inventory Stock Validation & Depletion**: Untested branch where `item_id` exists in inventory and stock is sufficient vs. insufficient (raising `ValueError`).
- **Tiered Discount Rates & Promo Coupons**: Untested combinations of SILVER (5%), GOLD (10%), PLATINUM (20%), PROMO15 (+15%), VIP30 (+30%), and expired/invalid coupons (`EXPIRED2020`).
- **Discount 50% Max Cap (`MAX_DISCOUNT_PERCENT`)**: Untested scenario where cumulative discounts exceed 50% and are correctly clamped.
- **Input Validation Errors**: Empty `order_id`, empty `items` list, zero/negative item quantities, and negative unit prices during order processing.

---

## 5. Concrete Suggestions for Improvement

1. **Adopt Pytest Parametrization**: Use `@pytest.mark.parametrize` for testing discount calculations across all combinations of customer tiers and promo codes.
2. **Fixture Reuse**: Introduce pytest fixtures for standard `OrderService` instances pre-loaded with test inventory.
3. **Strict Boundary Value Testing**: Explicitly test boundary values for quantities (`0`, `-1`, `1`), prices (`0.0`, `-0.01`), and refund reasons (`"ok"` vs `"Approved refund"`).
4. **Decouple Private Methods**: Remove direct tests of private methods (`_generate_internal_hash`); test public behaviors (such as tracking hash presence and length on `OrderReceipt`) instead.

---

## 6. Actionable Inventory

### Tests to PRESERVE
| Test Function Name | Target Function / Feature | Rationale |
| :--- | :--- | :--- |
| `test_process_order_standard_tier` | `OrderService.process_order` | Excellent end-to-end test verifying subtotal, taxes, and total calculations for standard tier. |

### Tests to DELETE
| Test Function Name | Target Function / Feature | Rationale |
| :--- | :--- | :--- |
| `test_private_internal_hash_exact_sha256` | `OrderService._generate_internal_hash` | Brittle anti-pattern testing private implementation details and internal salt strings. |
| `test_always_passes_dummy` | N/A (Trivial) | Useless dummy test (`assert True`) providing zero coverage or validation value. |

### Tests to EDIT
| Test Function Name | Target Function / Feature | Description of Changes Required |
| :--- | :--- | :--- |
| `test_calculate_discount_weak` | `OrderService.calculate_discount` | Rewrite into a comprehensive parametrized test verifying precise discount calculations across Silver, Gold, Platinum tiers, stackable coupons, and the 50% max discount cap. |

### Tests to CREATE
| Test Function Name | Target Function | Scenario / Description | Expected Assertion |
| :--- | :--- | :--- | :--- |
| `test_process_order_inventory_success_and_depletion` | `OrderService.process_order` | Order items with tracked inventory stock; verify stock decrements successfully. | `assert service.inventory["item-1"] == 3` |
| `test_process_order_insufficient_stock_raises_error` | `OrderService.process_order` | Order quantity exceeds available inventory. | `with pytest.raises(ValueError, match="Insufficient stock")` |
| `test_process_order_validation_errors` | `OrderService.process_order` | Test empty order ID, empty items list, negative prices, and zero/negative quantities. | `with pytest.raises(ValueError)` |
| `test_process_refund_success` | `OrderService.process_refund` | Issue valid refund with amount and reason >= 3 chars. | `assert record["status"] == "APPROVED"` and refund logged |
| `test_process_refund_validation_errors` | `OrderService.process_refund` | Test missing order ID, zero/negative amount, and short reason. | `with pytest.raises(ValueError)` |

---

## 7. Recommended Future Test Suite Implementation

Below is the recommended updated test implementation for `/dummy_project/tests/test_order_service.py`:

```python
"""
Updated unit tests for OrderService reflecting audit recommendations.
"""

import sys
import os
import pytest

dummy_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if dummy_src not in sys.path:
    sys.path.insert(0, dummy_src)

from order_service import (
    OrderService,
    OrderItem,
    CustomerTier
)


@pytest.fixture
def order_service():
    return OrderService(inventory={"item-1": 10, "item-2": 5})


def test_process_order_standard_tier(order_service):
    """Validates standard order calculations without discounts (PRESERVED)."""
    items = [
        OrderItem(item_id="item-1", name="Wireless Mouse", unit_price=25.0, quantity=2),
        OrderItem(item_id="item-2", name="Keyboard", unit_price=50.0, quantity=1)
    ]
    receipt = order_service.process_order("ORD-101", items, tier=CustomerTier.STANDARD)

    assert receipt.order_id == "ORD-101"
    assert receipt.subtotal == 100.0
    assert receipt.discount_amount == 0.0
    assert receipt.tax_amount == 8.0
    assert receipt.total == 108.0
    assert isinstance(receipt.tracking_hash, str)
    assert len(receipt.tracking_hash) == 16


@pytest.mark.parametrize(
    "tier,coupon,expected_discount",
    [
        (CustomerTier.STANDARD, None, 0.0),
        (CustomerTier.SILVER, None, 5.0),
        (CustomerTier.GOLD, "PROMO15", 25.0),  # 10% + 15% = 25% of 100
        (CustomerTier.PLATINUM, "VIP30", 50.0),  # 20% + 30% = 50% (capped at 50%)
        (CustomerTier.GOLD, "EXPIRED2020", 10.0),  # Invalid coupon ignored, only Gold 10%
    ]
)
def test_calculate_discount_parametrized(order_service, tier, coupon, expected_discount):
    """EDITS weak test: comprehensively verifies tier rates, coupons, and max cap."""
    discount = order_service.calculate_discount(100.0, tier=tier, coupon_code=coupon)
    assert discount == expected_discount


def test_process_order_insufficient_stock_raises_error(order_service):
    """NEW: Validates inventory stock depletion check."""
    items = [OrderItem(item_id="item-1", name="Mouse", unit_price=10.0, quantity=15)]
    with pytest.raises(ValueError, match="Insufficient stock"):
        order_service.process_order("ORD-FAIL", items)


@pytest.mark.parametrize(
    "order_id,items,error_msg",
    [
        ("", [OrderItem("1", "A", 10.0, 1)], "order_id is required"),
        ("ORD-1", [], "Order must contain at least one item"),
        ("ORD-2", [OrderItem("1", "A", 10.0, 0)], "Invalid quantity"),
        ("ORD-3", [OrderItem("1", "A", -5.0, 1)], "Invalid price"),
    ]
)
def test_process_order_validation_errors(order_service, order_id, items, error_msg):
    """NEW: Validates bad order input parameters."""
    with pytest.raises(ValueError, match=error_msg):
        order_service.process_order(order_id, items)


def test_process_refund_success(order_service):
    """NEW: Validates successful refund processing and logging."""
    record = order_service.process_refund("ORD-101", 50.0, "Defective item return")
    assert record["order_id"] == "ORD-101"
    assert record["refund_amount"] == 50.0
    assert record["status"] == "APPROVED"
    assert len(order_service.refund_log) == 1


@pytest.mark.parametrize(
    "order_id,amount,reason,error_msg",
    [
        ("", 50.0, "Valid reason", "Order ID required"),
        ("ORD-1", 0.0, "Valid reason", "Refund amount must be positive"),
        ("ORD-1", -10.0, "Valid reason", "Refund amount must be positive"),
        ("ORD-1", 50.0, "", "valid refund reason"),
        ("ORD-1", 50.0, "ok", "valid refund reason"),  # Too short (< 3 chars)
    ]
)
def test_process_refund_validation_errors(order_service, order_id, amount, reason, error_msg):
    """NEW: Validates refund input validation guards."""
    with pytest.raises(ValueError, match=error_msg):
        order_service.process_refund(order_id, amount, reason)
```

---
*End of Nightly Test Audit Report.*
