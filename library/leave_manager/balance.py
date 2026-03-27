"""
Leave Balance Manager - handles leave balance calculations and tracking.
"""

from datetime import datetime, timedelta


class LeaveBalanceManager:
    """Manages employee leave balances including deductions and restorations."""

    LEAVE_TYPES = ["annual", "sick", "unpaid"]

    @staticmethod
    def get_default_balances():
        """Return default leave balances for a new employee."""
        return {
            "annual": 20,
            "sick": 10,
            "unpaid": 30,
        }

    @staticmethod
    def deduct_leave(balances, leave_type, days):
        """
        Deduct days from the specified leave type balance.

        Args:
            balances: dict of leave type to remaining days
            leave_type: one of annual, sick, unpaid
            days: number of days to deduct

        Returns:
            Updated balances dict

        Raises:
            ValueError: if leave type is invalid or insufficient balance
        """
        if leave_type not in LeaveBalanceManager.LEAVE_TYPES:
            raise ValueError(f"Invalid leave type: {leave_type}")
        if days <= 0:
            raise ValueError("Days must be a positive number")
        if balances.get(leave_type, 0) < days:
            raise ValueError(
                f"Insufficient {leave_type} leave balance. "
                f"Available: {balances.get(leave_type, 0)}, Requested: {days}"
            )
        balances[leave_type] -= days
        return balances

    @staticmethod
    def check_balance(balances, leave_type, days):
        """
        Check if enough balance is available for the requested leave.

        Args:
            balances: dict of leave type to remaining days
            leave_type: one of annual, sick, unpaid
            days: number of days requested

        Returns:
            True if sufficient balance, False otherwise
        """
        if leave_type not in LeaveBalanceManager.LEAVE_TYPES:
            return False
        return balances.get(leave_type, 0) >= days

    @staticmethod
    def calculate_days(start_date, end_date):
        """
        Calculate the number of business days (excluding weekends) between two dates.

        Args:
            start_date: start date string in YYYY-MM-DD format
            end_date: end date string in YYYY-MM-DD format

        Returns:
            Number of business days (int)

        Raises:
            ValueError: if dates are invalid or start > end
        """
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        if start_date > end_date:
            raise ValueError("Start date must be before or equal to end date")

        business_days = 0
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:  # Monday=0 to Friday=4
                business_days += 1
            current += timedelta(days=1)

        return business_days

    @staticmethod
    def restore_balance(balances, leave_type, days):
        """
        Restore days to the specified leave type balance.

        Args:
            balances: dict of leave type to remaining days
            leave_type: one of annual, sick, unpaid
            days: number of days to restore

        Returns:
            Updated balances dict

        Raises:
            ValueError: if leave type is invalid or days is not positive
        """
        if leave_type not in LeaveBalanceManager.LEAVE_TYPES:
            raise ValueError(f"Invalid leave type: {leave_type}")
        if days <= 0:
            raise ValueError("Days must be a positive number")

        defaults = LeaveBalanceManager.get_default_balances()
        max_balance = defaults.get(leave_type, 0)

        balances[leave_type] = min(balances.get(leave_type, 0) + days, max_balance)
        return balances
