"""
Dummy Order Management Service for testing and demonstration purposes.
Contains business logic for processing orders, applying discounts, and issuing refunds.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict
import hashlib
from datetime import datetime


class CustomerTier(str, Enum):
    STANDARD = "standard"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


@dataclass
class OrderItem:
    item_id: str
    name: str
    unit_price: float
    quantity: int


@dataclass
class OrderReceipt:
    order_id: str
    subtotal: float
    discount_amount: float
    tax_amount: float
    total: float
    customer_tier: CustomerTier
    timestamp: str
    tracking_hash: str


class OrderService:
    TAX_RATE = 0.08  # 8% sales tax
    MAX_DISCOUNT_PERCENT = 0.50  # Max 50% discount cap

    def __init__(self, inventory: Optional[Dict[str, int]] = None):
        self.inventory = inventory or {}
        self.refund_log: List[Dict] = []

    def calculate_discount(
        self,
        subtotal: float,
        tier: CustomerTier = CustomerTier.STANDARD,
        coupon_code: Optional[str] = None
    ) -> float:
        """
        Calculates discount amount based on customer tier and coupons.
        Capped at MAX_DISCOUNT_PERCENT of subtotal.
        """
        if subtotal <= 0:
            return 0.0

        rate = 0.0
        if tier == CustomerTier.SILVER:
            rate += 0.05
        elif tier == CustomerTier.GOLD:
            rate += 0.10
        elif tier == CustomerTier.PLATINUM:
            rate += 0.20

        # Optional promo coupon
        if coupon_code:
            coupon = coupon_code.strip().upper()
            if coupon == "PROMO15":
                rate += 0.15
            elif coupon == "VIP30":
                rate += 0.30
            elif coupon == "EXPIRED2020":
                # Invalid coupon
                pass

        # Apply maximum discount cap
        effective_rate = min(rate, self.MAX_DISCOUNT_PERCENT)
        return round(subtotal * effective_rate, 2)

    def process_order(
        self,
        order_id: str,
        items: List[OrderItem],
        tier: CustomerTier = CustomerTier.STANDARD,
        coupon_code: Optional[str] = None
    ) -> OrderReceipt:
        """
        Processes an order, deducts stock, and generates an OrderReceipt.
        Raises ValueError on invalid inputs or inventory depletion.
        """
        if not order_id:
            raise ValueError("order_id is required")
        if not items:
            raise ValueError("Order must contain at least one item")

        subtotal = 0.0
        for item in items:
            if item.quantity <= 0:
                raise ValueError(f"Invalid quantity for item {item.item_id}: {item.quantity}")
            if item.unit_price < 0:
                raise ValueError(f"Invalid price for item {item.item_id}: {item.unit_price}")

            # Check and deduct inventory if tracked
            if item.item_id in self.inventory:
                if self.inventory[item.item_id] < item.quantity:
                    raise ValueError(f"Insufficient stock for item {item.item_id}")
                self.inventory[item.item_id] -= item.quantity

            subtotal += item.unit_price * item.quantity

        discount = self.calculate_discount(subtotal, tier, coupon_code)
        taxable_amount = max(0.0, subtotal - discount)
        tax = round(taxable_amount * self.TAX_RATE, 2)
        total = round(taxable_amount + tax, 2)

        tracking_hash = self._generate_internal_hash(order_id, total)

        return OrderReceipt(
            order_id=order_id,
            subtotal=round(subtotal, 2),
            discount_amount=discount,
            tax_amount=tax,
            total=total,
            customer_tier=tier,
            timestamp=datetime.utcnow().isoformat(),
            tracking_hash=tracking_hash
        )

    def process_refund(self, order_id: str, amount: float, reason: str) -> Dict:
        """
        CRITICAL FINANCIAL METHOD: Currently has ZERO tests!
        Issues a refund and records it in the internal refund log.
        """
        if not order_id:
            raise ValueError("Order ID required for refund")
        if amount <= 0:
            raise ValueError("Refund amount must be positive")
        if not reason or len(reason.strip()) < 3:
            raise ValueError("A valid refund reason must be supplied")

        record = {
            "order_id": order_id,
            "refund_amount": round(amount, 2),
            "reason": reason.strip(),
            "status": "APPROVED",
            "refund_date": datetime.utcnow().isoformat()
        }
        self.refund_log.append(record)
        return record

    def _generate_internal_hash(self, order_id: str, amount: float) -> str:
        """Private helper function (implementation detail)."""
        raw = f"{order_id}:{amount}:SECRET_SALT_2026"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
