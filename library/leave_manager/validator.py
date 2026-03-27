"""
Leave Validator - validates leave requests, employee data, and approvals.
"""

import re
from datetime import datetime


class LeaveValidator:
    """Validates all leave-related input data."""

    VALID_LEAVE_TYPES = ["annual", "sick", "unpaid"]
    VALID_APPROVAL_STATUSES = ["approved", "rejected"]

    @staticmethod
    def validate_leave_request(data):
        """
        Validate a leave request payload.

        Rules:
            - leaveType must be one of annual, sick, unpaid
            - startDate and endDate required in YYYY-MM-DD format
            - startDate must be <= endDate
            - reason is required with minimum 10 characters

        Args:
            data: dict with leaveType, startDate, endDate, reason

        Returns:
            Tuple of (is_valid: bool, errors: list of str)
        """
        errors = []

        if not data or not isinstance(data, dict):
            return False, ["Request data is required"]

        # Validate leave type
        leave_type = data.get("leaveType", "")
        if not leave_type:
            errors.append("Leave type is required")
        elif leave_type not in LeaveValidator.VALID_LEAVE_TYPES:
            errors.append(
                f"Invalid leave type: {leave_type}. "
                f"Must be one of: {', '.join(LeaveValidator.VALID_LEAVE_TYPES)}"
            )

        # Validate dates
        start_date = data.get("startDate", "")
        end_date = data.get("endDate", "")

        if not start_date:
            errors.append("Start date is required")
        else:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                errors.append("Invalid start date format. Use YYYY-MM-DD")
                start = None

        if not end_date:
            errors.append("End date is required")
        else:
            try:
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                errors.append("Invalid end date format. Use YYYY-MM-DD")
                end = None

        if start_date and end_date and "start" in dir() and "end" in dir():
            if start is not None and end is not None and start > end:
                errors.append("Start date must be before or equal to end date")

        # Validate reason
        reason = data.get("reason", "")
        if not reason:
            errors.append("Reason is required")
        elif len(reason.strip()) < 10:
            errors.append("Reason must be at least 10 characters")

        return len(errors) == 0, errors

    @staticmethod
    def validate_employee(data):
        """
        Validate employee registration data.

        Args:
            data: dict with name, email, role, department

        Returns:
            Tuple of (is_valid: bool, errors: list of str)
        """
        errors = []

        if not data or not isinstance(data, dict):
            return False, ["Employee data is required"]

        # Validate name
        name = data.get("name", "")
        if not name or len(name.strip()) < 2:
            errors.append("Name is required (minimum 2 characters)")

        # Validate email
        email = data.get("email", "")
        if not email:
            errors.append("Email is required")
        elif not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            errors.append("Invalid email format")

        # Validate role
        role = data.get("role", "")
        if role and role not in ["employee", "manager"]:
            errors.append("Role must be 'employee' or 'manager'")

        # Validate password
        password = data.get("password", "")
        if not password:
            errors.append("Password is required")
        elif len(password) < 8:
            errors.append("Password must be at least 8 characters")

        return len(errors) == 0, errors

    @staticmethod
    def validate_approval(data):
        """
        Validate approval/rejection payload.

        Rules:
            - status must be 'approved' or 'rejected'
            - comments required for rejection

        Args:
            data: dict with status and optional comments

        Returns:
            Tuple of (is_valid: bool, errors: list of str)
        """
        errors = []

        if not data or not isinstance(data, dict):
            return False, ["Approval data is required"]

        status = data.get("status", "")
        if not status:
            errors.append("Status is required")
        elif status not in LeaveValidator.VALID_APPROVAL_STATUSES:
            errors.append(
                f"Invalid status: {status}. "
                f"Must be one of: {', '.join(LeaveValidator.VALID_APPROVAL_STATUSES)}"
            )

        # Comments required for rejection
        if status == "rejected":
            comments = data.get("comments", "")
            if not comments or len(comments.strip()) < 1:
                errors.append("Comments are required when rejecting a request")

        return len(errors) == 0, errors

    @staticmethod
    def sanitize_input(text):
        """
        Sanitize user input by removing potentially dangerous characters.

        Args:
            text: input string to sanitize

        Returns:
            Sanitized string
        """
        if not isinstance(text, str):
            return str(text) if text is not None else ""

        # Remove HTML tags
        text = re.sub(r"<[^>]*>", "", text)
        # Remove script injections
        text = re.sub(r"(javascript|script|onclick|onerror):", "", text, flags=re.IGNORECASE)
        # Strip leading/trailing whitespace
        text = text.strip()

        return text
