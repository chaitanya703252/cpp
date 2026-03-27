"""
Overlap Detector - detects overlapping leave requests and date conflicts.
"""

from datetime import datetime, timedelta


class OverlapDetector:
    """Detects overlapping leave requests and manages date conflict resolution."""

    @staticmethod
    def check_overlap(new_request, existing_requests):
        """
        Check if a new leave request overlaps with any existing requests.

        Args:
            new_request: dict with startDate and endDate (YYYY-MM-DD)
            existing_requests: list of dicts with startDate and endDate

        Returns:
            True if overlap found, False otherwise
        """
        new_start = OverlapDetector._parse_date(new_request["startDate"])
        new_end = OverlapDetector._parse_date(new_request["endDate"])

        for existing in existing_requests:
            if existing.get("status") == "rejected":
                continue
            ex_start = OverlapDetector._parse_date(existing["startDate"])
            ex_end = OverlapDetector._parse_date(existing["endDate"])

            if new_start <= ex_end and new_end >= ex_start:
                return True

        return False

    @staticmethod
    def find_conflicts(request, all_requests):
        """
        Find all requests that conflict with the given request.

        Args:
            request: dict with startDate and endDate
            all_requests: list of all leave request dicts

        Returns:
            List of conflicting request dicts
        """
        conflicts = []
        req_start = OverlapDetector._parse_date(request["startDate"])
        req_end = OverlapDetector._parse_date(request["endDate"])

        for other in all_requests:
            if other.get("requestId") == request.get("requestId"):
                continue
            if other.get("status") == "rejected":
                continue

            other_start = OverlapDetector._parse_date(other["startDate"])
            other_end = OverlapDetector._parse_date(other["endDate"])

            if req_start <= other_end and req_end >= other_start:
                conflicts.append(other)

        return conflicts

    @staticmethod
    def get_busy_dates(requests):
        """
        Get a set of all dates covered by the given leave requests.

        Args:
            requests: list of leave request dicts with startDate and endDate

        Returns:
            Set of date strings (YYYY-MM-DD)
        """
        busy_dates = set()

        for request in requests:
            if request.get("status") == "rejected":
                continue
            start = OverlapDetector._parse_date(request["startDate"])
            end = OverlapDetector._parse_date(request["endDate"])

            current = start
            while current <= end:
                if current.weekday() < 5:
                    busy_dates.add(current.strftime("%Y-%m-%d"))
                current += timedelta(days=1)

        return busy_dates

    @staticmethod
    def validate_date_range(start, end):
        """
        Validate that a date range is valid.

        Args:
            start: start date string YYYY-MM-DD
            end: end date string YYYY-MM-DD

        Returns:
            Tuple of (is_valid: bool, error_message: str or None)
        """
        try:
            start_date = OverlapDetector._parse_date(start)
            end_date = OverlapDetector._parse_date(end)
        except (ValueError, TypeError):
            return False, "Invalid date format. Use YYYY-MM-DD"

        if start_date > end_date:
            return False, "Start date must be before or equal to end date"

        if start_date < datetime.now().date():
            return False, "Start date cannot be in the past"

        return True, None

    @staticmethod
    def _parse_date(date_str):
        """Parse a date string to a date object."""
        if isinstance(date_str, str):
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        return date_str
