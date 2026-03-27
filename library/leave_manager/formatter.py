"""
Leave Formatter - formats leave data for display and export.
"""

import csv
import io
from datetime import datetime, timedelta
import calendar


class LeaveFormatter:
    """Formats leave requests, balances, and calendars for display."""

    @staticmethod
    def format_request_summary(request):
        """
        Format a leave request into a readable summary string.

        Args:
            request: dict with leaveType, startDate, endDate, status, reason, employeeName

        Returns:
            Formatted summary string
        """
        employee = request.get("employeeName", "Unknown")
        leave_type = request.get("leaveType", "unknown").capitalize()
        start = request.get("startDate", "N/A")
        end = request.get("endDate", "N/A")
        status = request.get("status", "unknown").upper()
        reason = request.get("reason", "No reason provided")

        return (
            f"Leave Request Summary\n"
            f"{'=' * 40}\n"
            f"Employee : {employee}\n"
            f"Type     : {leave_type} Leave\n"
            f"Period   : {start} to {end}\n"
            f"Status   : {status}\n"
            f"Reason   : {reason}\n"
            f"{'=' * 40}"
        )

    @staticmethod
    def format_balance_report(employee_name, balances):
        """
        Format leave balances into a readable report.

        Args:
            employee_name: name of the employee
            balances: dict of leave type to remaining days

        Returns:
            Formatted balance report string
        """
        defaults = {"annual": 20, "sick": 10, "unpaid": 30}

        lines = [
            f"Leave Balance Report - {employee_name}",
            "=" * 45,
            f"{'Type':<15} {'Used':<10} {'Remaining':<10} {'Total':<10}",
            "-" * 45,
        ]

        for leave_type in ["annual", "sick", "unpaid"]:
            total = defaults.get(leave_type, 0)
            remaining = balances.get(leave_type, 0)
            used = total - remaining
            lines.append(
                f"{leave_type.capitalize():<15} {used:<10} {remaining:<10} {total:<10}"
            )

        lines.append("=" * 45)
        return "\n".join(lines)

    @staticmethod
    def format_team_calendar(requests, month):
        """
        Format a simple team calendar showing who is on leave.

        Args:
            requests: list of leave request dicts
            month: month string in YYYY-MM format

        Returns:
            Formatted calendar string
        """
        try:
            year, mon = map(int, month.split("-"))
        except (ValueError, AttributeError):
            return "Invalid month format. Use YYYY-MM"

        cal = calendar.Calendar()
        days_in_month = calendar.monthrange(year, mon)[1]
        month_name = calendar.month_name[mon]

        lines = [
            f"Team Leave Calendar - {month_name} {year}",
            "=" * 50,
        ]

        # Build day-to-employees mapping
        day_leaves = {}
        for req in requests:
            if req.get("status") == "rejected":
                continue
            try:
                start = datetime.strptime(req["startDate"], "%Y-%m-%d").date()
                end = datetime.strptime(req["endDate"], "%Y-%m-%d").date()
            except (ValueError, KeyError):
                continue

            current = start
            while current <= end:
                if current.year == year and current.month == mon and current.weekday() < 5:
                    day_key = current.day
                    if day_key not in day_leaves:
                        day_leaves[day_key] = []
                    name = req.get("employeeName", "Unknown")
                    leave_type = req.get("leaveType", "leave")
                    day_leaves[day_key].append(f"{name} ({leave_type})")
                current += timedelta(days=1)

        for day in range(1, days_in_month + 1):
            date_obj = datetime(year, mon, day).date()
            if date_obj.weekday() >= 5:
                continue
            day_name = date_obj.strftime("%a")
            date_str = f"{day:2d} {day_name}"
            if day in day_leaves:
                people = ", ".join(day_leaves[day])
                lines.append(f"  {date_str} | {people}")
            else:
                lines.append(f"  {date_str} |")

        lines.append("=" * 50)
        return "\n".join(lines)

    @staticmethod
    def to_csv(requests):
        """
        Convert a list of leave requests to CSV format.

        Args:
            requests: list of leave request dicts

        Returns:
            CSV string
        """
        if not requests:
            return ""

        output = io.StringIO()
        fields = [
            "requestId", "employeeName", "leaveType",
            "startDate", "endDate", "status", "reason",
        ]
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()

        for req in requests:
            writer.writerow(req)

        return output.getvalue()

    @staticmethod
    def format_approval_notification(request, action, comments=""):
        """
        Format an approval/rejection notification message.

        Args:
            request: the leave request dict
            action: 'approved' or 'rejected'
            comments: optional manager comments

        Returns:
            Formatted notification string
        """
        employee = request.get("employeeName", "Employee")
        leave_type = request.get("leaveType", "").capitalize()
        start = request.get("startDate", "N/A")
        end = request.get("endDate", "N/A")

        msg = (
            f"Leave Request {action.upper()}\n"
            f"{'-' * 35}\n"
            f"Employee : {employee}\n"
            f"Type     : {leave_type} Leave\n"
            f"Period   : {start} to {end}\n"
            f"Decision : {action.capitalize()}\n"
        )

        if comments:
            msg += f"Comments : {comments}\n"

        msg += f"{'-' * 35}"
        return msg
