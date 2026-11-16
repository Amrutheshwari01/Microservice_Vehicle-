import math
from datetime import datetime
from typing import Tuple
from app.models.listing import RentalListing

class PricingEngine:
    @classmethod
    def calculate_price(
        cls,
        listing: RentalListing,
        start_time: datetime,
        end_time: datetime
    ) -> Tuple[float, float, float, float]:
        """
        Calculates rental cost based on listing rate card.
        Returns: (duration_hours, base_rent, security_deposit, total_hold_amount)
        """
        duration = end_time - start_time
        duration_seconds = max(duration.total_seconds(), 3600.0) # minimum 1 hour
        duration_hours = duration_seconds / 3600.0
        duration_days = duration_seconds / 86400.0

        # If booking is 24h or more, optimize using daily rate
        if duration_hours >= 24:
            days = math.ceil(duration_days)
            base_rent = days * listing.rate_per_day
        else:
            hours = math.ceil(duration_hours)
            base_rent = min(hours * listing.rate_per_hour, listing.rate_per_day)

        security_deposit = listing.security_deposit
        total_hold = round(base_rent + security_deposit, 2)
        base_rent = round(base_rent, 2)
        
        return round(duration_hours, 2), base_rent, security_deposit, total_hold

    @classmethod
    def calculate_cancellation_refund(
        cls,
        start_time: datetime,
        cancelled_at: datetime,
        total_hold_amount: float,
        deposit_amount: float,
        base_rent_amount: float
    ) -> Tuple[float, float]:
        """
        RTO-FR-11: Cancellation policy
        - > 24 hours before start: 100% refund of hold (0 fee)
        - 12 to 24 hours before start: 10% penalty on base rent, 100% deposit refunded
        - < 12 hours before start: 25% penalty on base rent, 100% deposit refunded
        Returns: (cancellation_fee, refund_amount)
        """
        hours_to_start = (start_time - cancelled_at).total_seconds() / 3600.0
        
        if hours_to_start >= 24.0:
            cancellation_fee = 0.0
            refund_amount = total_hold_amount
        elif hours_to_start >= 12.0:
            cancellation_fee = round(0.10 * base_rent_amount, 2)
            refund_amount = round(total_hold_amount - cancellation_fee, 2)
        else:
            cancellation_fee = round(0.25 * base_rent_amount, 2)
            refund_amount = round(total_hold_amount - cancellation_fee, 2)

        return cancellation_fee, refund_amount

