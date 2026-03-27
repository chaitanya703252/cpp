"""
Tests for the leave_manager library.
30+ test cases covering balance, overlap, validator, and formatter modules.
"""

import unittest
from datetime import datetime, timedelta

from leave_manager.balance import LeaveBalanceManager
from leave_manager.overlap import OverlapDetector
from leave_manager.validator import LeaveValidator
from leave_manager.formatter import LeaveFormatter


class TestLeaveBalanceManager(unittest.TestCase):
    """Tests for LeaveBalanceManager."""

    def test_get_default_balances(self):
        balances = LeaveBalanceManager.get_default_balances()
        self.assertEqual(balances["annual"], 20)
        self.assertEqual(balances["sick"], 10)
        self.assertEqual(balances["unpaid"], 30)

    def test_deduct_leave_annual(self):
        balances = LeaveBalanceManager.get_default_balances()
        result = LeaveBalanceManager.deduct_leave(balances, "annual", 5)
        self.assertEqual(result["annual"], 15)

    def test_deduct_leave_sick(self):
        balances = LeaveBalanceManager.get_default_balances()
        result = LeaveBalanceManager.deduct_leave(balances, "sick", 3)
        self.assertEqual(result["sick"], 7)

    def test_deduct_leave_insufficient_balance(self):
        balances = LeaveBalanceManager.get_default_balances()
        with self.assertRaises(ValueError):
            LeaveBalanceManager.deduct_leave(balances, "annual", 25)

    def test_deduct_leave_invalid_type(self):
        balances = LeaveBalanceManager.get_default_balances()
        with self.assertRaises(ValueError):
            LeaveBalanceManager.deduct_leave(balances, "vacation", 5)

    def test_deduct_leave_zero_days(self):
        balances = LeaveBalanceManager.get_default_balances()
        with self.assertRaises(ValueError):
            LeaveBalanceManager.deduct_leave(balances, "annual", 0)

    def test_check_balance_sufficient(self):
        balances = LeaveBalanceManager.get_default_balances()
        self.assertTrue(LeaveBalanceManager.check_balance(balances, "annual", 10))

    def test_check_balance_insufficient(self):
        balances = LeaveBalanceManager.get_default_balances()
        self.assertFalse(LeaveBalanceManager.check_balance(balances, "sick", 15))

    def test_check_balance_invalid_type(self):
        balances = LeaveBalanceManager.get_default_balances()
        self.assertFalse(LeaveBalanceManager.check_balance(balances, "vacation", 5))

    def test_calculate_days_weekdays_only(self):
        # Mon 2026-01-05 to Fri 2026-01-09 = 5 days
        days = LeaveBalanceManager.calculate_days("2026-01-05", "2026-01-09")
        self.assertEqual(days, 5)

    def test_calculate_days_with_weekend(self):
        # Mon 2026-01-05 to Mon 2026-01-12 = 6 business days
        days = LeaveBalanceManager.calculate_days("2026-01-05", "2026-01-12")
        self.assertEqual(days, 6)

    def test_calculate_days_single_day(self):
        days = LeaveBalanceManager.calculate_days("2026-01-05", "2026-01-05")
        self.assertEqual(days, 1)

    def test_calculate_days_invalid_range(self):
        with self.assertRaises(ValueError):
            LeaveBalanceManager.calculate_days("2026-01-10", "2026-01-05")

    def test_restore_balance(self):
        balances = {"annual": 15, "sick": 10, "unpaid": 30}
        result = LeaveBalanceManager.restore_balance(balances, "annual", 3)
        self.assertEqual(result["annual"], 18)

    def test_restore_balance_capped_at_max(self):
        balances = {"annual": 19, "sick": 10, "unpaid": 30}
        result = LeaveBalanceManager.restore_balance(balances, "annual", 5)
        self.assertEqual(result["annual"], 20)

    def test_restore_balance_invalid_type(self):
        balances = LeaveBalanceManager.get_default_balances()
        with self.assertRaises(ValueError):
            LeaveBalanceManager.restore_balance(balances, "vacation", 5)


class TestOverlapDetector(unittest.TestCase):
    """Tests for OverlapDetector."""

    def test_check_overlap_true(self):
        new = {"startDate": "2026-03-10", "endDate": "2026-03-15"}
        existing = [{"startDate": "2026-03-12", "endDate": "2026-03-18"}]
        self.assertTrue(OverlapDetector.check_overlap(new, existing))

    def test_check_overlap_false(self):
        new = {"startDate": "2026-03-10", "endDate": "2026-03-12"}
        existing = [{"startDate": "2026-03-15", "endDate": "2026-03-18"}]
        self.assertFalse(OverlapDetector.check_overlap(new, existing))

    def test_check_overlap_ignores_rejected(self):
        new = {"startDate": "2026-03-10", "endDate": "2026-03-15"}
        existing = [{"startDate": "2026-03-12", "endDate": "2026-03-18", "status": "rejected"}]
        self.assertFalse(OverlapDetector.check_overlap(new, existing))

    def test_find_conflicts(self):
        request = {"requestId": "1", "startDate": "2026-03-10", "endDate": "2026-03-15"}
        all_requests = [
            {"requestId": "1", "startDate": "2026-03-10", "endDate": "2026-03-15"},
            {"requestId": "2", "startDate": "2026-03-12", "endDate": "2026-03-18"},
            {"requestId": "3", "startDate": "2026-03-20", "endDate": "2026-03-25"},
        ]
        conflicts = OverlapDetector.find_conflicts(request, all_requests)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["requestId"], "2")

    def test_get_busy_dates(self):
        requests = [
            {"startDate": "2026-03-09", "endDate": "2026-03-11"}  # Mon-Wed
        ]
        dates = OverlapDetector.get_busy_dates(requests)
        self.assertIn("2026-03-09", dates)
        self.assertIn("2026-03-10", dates)
        self.assertIn("2026-03-11", dates)

    def test_get_busy_dates_excludes_weekends(self):
        requests = [
            {"startDate": "2026-03-06", "endDate": "2026-03-09"}  # Fri-Mon
        ]
        dates = OverlapDetector.get_busy_dates(requests)
        self.assertIn("2026-03-06", dates)  # Friday
        self.assertNotIn("2026-03-07", dates)  # Saturday
        self.assertNotIn("2026-03-08", dates)  # Sunday
        self.assertIn("2026-03-09", dates)  # Monday

    def test_validate_date_range_valid(self):
        future = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
        future2 = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
        valid, error = OverlapDetector.validate_date_range(future, future2)
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_validate_date_range_invalid_format(self):
        valid, error = OverlapDetector.validate_date_range("bad-date", "2026-03-10")
        self.assertFalse(valid)
        self.assertIn("Invalid", error)

    def test_validate_date_range_start_after_end(self):
        future1 = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
        future2 = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
        valid, error = OverlapDetector.validate_date_range(future1, future2)
        self.assertFalse(valid)


class TestLeaveValidator(unittest.TestCase):
    """Tests for LeaveValidator."""

    def test_validate_leave_request_valid(self):
        data = {
            "leaveType": "annual",
            "startDate": "2026-04-01",
            "endDate": "2026-04-05",
            "reason": "Family vacation planned for April",
        }
        valid, errors = LeaveValidator.validate_leave_request(data)
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)

    def test_validate_leave_request_invalid_type(self):
        data = {
            "leaveType": "holiday",
            "startDate": "2026-04-01",
            "endDate": "2026-04-05",
            "reason": "Some valid reason here",
        }
        valid, errors = LeaveValidator.validate_leave_request(data)
        self.assertFalse(valid)

    def test_validate_leave_request_short_reason(self):
        data = {
            "leaveType": "annual",
            "startDate": "2026-04-01",
            "endDate": "2026-04-05",
            "reason": "Short",
        }
        valid, errors = LeaveValidator.validate_leave_request(data)
        self.assertFalse(valid)

    def test_validate_leave_request_empty_data(self):
        valid, errors = LeaveValidator.validate_leave_request(None)
        self.assertFalse(valid)

    def test_validate_employee_valid(self):
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "role": "employee",
            "password": "password123",
        }
        valid, errors = LeaveValidator.validate_employee(data)
        self.assertTrue(valid)

    def test_validate_employee_invalid_email(self):
        data = {
            "name": "John Doe",
            "email": "not-an-email",
            "role": "employee",
            "password": "password123",
        }
        valid, errors = LeaveValidator.validate_employee(data)
        self.assertFalse(valid)

    def test_validate_approval_approved(self):
        data = {"status": "approved", "comments": ""}
        valid, errors = LeaveValidator.validate_approval(data)
        self.assertTrue(valid)

    def test_validate_approval_rejected_needs_comments(self):
        data = {"status": "rejected"}
        valid, errors = LeaveValidator.validate_approval(data)
        self.assertFalse(valid)

    def test_validate_approval_rejected_with_comments(self):
        data = {"status": "rejected", "comments": "Team capacity issue"}
        valid, errors = LeaveValidator.validate_approval(data)
        self.assertTrue(valid)

    def test_sanitize_input_removes_html(self):
        result = LeaveValidator.sanitize_input("<script>alert('xss')</script>Hello")
        self.assertNotIn("<script>", result)
        self.assertIn("Hello", result)

    def test_sanitize_input_strips_whitespace(self):
        result = LeaveValidator.sanitize_input("  hello  ")
        self.assertEqual(result, "hello")

    def test_sanitize_input_none(self):
        result = LeaveValidator.sanitize_input(None)
        self.assertEqual(result, "")


class TestLeaveFormatter(unittest.TestCase):
    """Tests for LeaveFormatter."""

    def test_format_request_summary(self):
        request = {
            "employeeName": "Jane Doe",
            "leaveType": "annual",
            "startDate": "2026-04-01",
            "endDate": "2026-04-05",
            "status": "pending",
            "reason": "Family vacation",
        }
        result = LeaveFormatter.format_request_summary(request)
        self.assertIn("Jane Doe", result)
        self.assertIn("Annual", result)
        self.assertIn("PENDING", result)

    def test_format_balance_report(self):
        balances = {"annual": 15, "sick": 8, "unpaid": 30}
        result = LeaveFormatter.format_balance_report("John Doe", balances)
        self.assertIn("John Doe", result)
        self.assertIn("Annual", result)
        self.assertIn("15", result)

    def test_format_team_calendar(self):
        requests = [
            {
                "employeeName": "Alice",
                "leaveType": "annual",
                "startDate": "2026-03-09",
                "endDate": "2026-03-11",
                "status": "approved",
            }
        ]
        result = LeaveFormatter.format_team_calendar(requests, "2026-03")
        self.assertIn("Alice", result)
        self.assertIn("March", result)

    def test_format_team_calendar_invalid_month(self):
        result = LeaveFormatter.format_team_calendar([], "bad")
        self.assertIn("Invalid", result)

    def test_to_csv(self):
        requests = [
            {
                "requestId": "1",
                "employeeName": "Bob",
                "leaveType": "sick",
                "startDate": "2026-03-10",
                "endDate": "2026-03-12",
                "status": "approved",
                "reason": "Not feeling well",
            }
        ]
        result = LeaveFormatter.to_csv(requests)
        self.assertIn("requestId", result)
        self.assertIn("Bob", result)

    def test_to_csv_empty(self):
        result = LeaveFormatter.to_csv([])
        self.assertEqual(result, "")

    def test_format_approval_notification_approved(self):
        request = {
            "employeeName": "Alice",
            "leaveType": "annual",
            "startDate": "2026-04-01",
            "endDate": "2026-04-05",
        }
        result = LeaveFormatter.format_approval_notification(request, "approved")
        self.assertIn("APPROVED", result)
        self.assertIn("Alice", result)

    def test_format_approval_notification_rejected_with_comments(self):
        request = {
            "employeeName": "Bob",
            "leaveType": "sick",
            "startDate": "2026-04-01",
            "endDate": "2026-04-03",
        }
        result = LeaveFormatter.format_approval_notification(
            request, "rejected", "Team needs you"
        )
        self.assertIn("REJECTED", result)
        self.assertIn("Team needs you", result)


if __name__ == "__main__":
    unittest.main()
