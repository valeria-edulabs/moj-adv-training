"""
Unit tests for OrderService.
Demonstrates a mix of solid tests, flawed/brittle tests, and gaps for the tests_agent to review.
"""

import sys
import os
import pytest

# Ensure src is on sys.path for direct testing
dummy_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if dummy_src not in sys.path:
    sys.path.insert(0, dummy_src)

from order_service import (
    OrderService,
    OrderItem,
    CustomerTier
)


# ============================================================================
# Test 1: Solid Test (Should be PRESERVED)
# ============================================================================
def test_process_order_standard_tier():
    """Validates standard order calculations without discounts."""
    service = OrderService()
    items = [
        OrderItem(item_id="item-1", name="Wireless Mouse", unit_price=25.0, quantity=2),
        OrderItem(item_id="item-2", name="Keyboard", unit_price=50.0, quantity=1)
    ]
    receipt = service.process_order("ORD-101", items, tier=CustomerTier.STANDARD)

    assert receipt.order_id == "ORD-101"
    assert receipt.subtotal == 100.0
    assert receipt.discount_amount == 0.0
    assert receipt.tax_amount == 8.0  # 8% of 100
    assert receipt.total == 108.0


# ============================================================================
# Test 2: Weak / Poor Assertions (Should be EDITED)
# ============================================================================
def test_calculate_discount_weak():
    """
    WEAK TEST: Only checks that discount >= 0.
    Does not verify actual tier rates (e.g. 10% for Gold, 20% for Platinum),
    coupons, or the 50% max discount cap!
    """
    service = OrderService()
    discount = service.calculate_discount(100.0, tier=CustomerTier.GOLD)
    # Poor assertion: passes even if discount is completely wrong or 0!
    assert discount >= 0


# ============================================================================
# Test 3: Brittle Implementation Detail Test (Should be DELETED)
# ============================================================================
def test_private_internal_hash_exact_sha256():
    """
    BRITTLE ANTI-PATTERN TEST:
    Directly invokes and asserts private internal helper `_generate_internal_hash`.
    Coupled to private implementation details and secret salt string.
    Breaks if internal hashing algorithm changes.
    """
    service = OrderService()
    h = service._generate_internal_hash("ORD-999", 50.0)
    assert len(h) == 16
    assert isinstance(h, str)


# ============================================================================
# Test 4: Useless / Dummy Test (Should be DELETED)
# ============================================================================
def test_always_passes_dummy():
    """Trivial test that tests nothing."""
    assert True
