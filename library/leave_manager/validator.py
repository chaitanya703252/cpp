"""
Input Validator - validates study groups, sessions, and user registration data.
"""

import re
from datetime import datetime


class InputValidator:
    """Validates all study group related input data."""

    VALID_SUBJECTS = [
        "mathematics", "physics", "chemistry", "biology", "computer_science",
        "english", "history", "economics", "psychology", "engineering",
        "business", "statistics", "data_science", "law", "medicine",
    ]

    @staticmethod
    def validate_group(data):
        """
        Validate study group creation data.

        Rules:
            - name required, 3-100 characters
            - subject required
            - description required, minimum 10 characters
            - maxMembers between 2 and 20

        Args:
            data: dict with name, subject, description, maxMembers

        Returns:
            Tuple of (is_valid: bool, errors: list of str)
        """
        errors = []

        if not data or not isinstance(data, dict):
            return False, ["Group data is required"]

        name = data.get("name", "")
        if not name or len(name.strip()) < 3:
            errors.append("Group name is required (minimum 3 characters)")
        elif len(name.strip()) > 100:
            errors.append("Group name must be 100 characters or less")

        subject = data.get("subject", "")
        if not subject:
            errors.append("Subject is required")

        description = data.get("description", "")
        if not description or len(description.strip()) < 10:
            errors.append("Description is required (minimum 10 characters)")

        max_members = data.get("maxMembers", 12)
        try:
            max_members = int(max_members)
            if max_members < 2 or max_members > 20:
                errors.append("Max members must be between 2 and 20")
        except (ValueError, TypeError):
            errors.append("Max members must be a valid number")

        return len(errors) == 0, errors

    @staticmethod
    def validate_session(data):
        """
        Validate study session data.

        Rules:
            - title required, minimum 3 characters
            - date required, YYYY-MM-DD format
            - startTime and endTime required, HH:MM format
            - endTime must be after startTime

        Args:
            data: dict with title, date, startTime, endTime

        Returns:
            Tuple of (is_valid: bool, errors: list of str)
        """
        errors = []

        if not data or not isinstance(data, dict):
            return False, ["Session data is required"]

        title = data.get("title", "")
        if not title or len(title.strip()) < 3:
            errors.append("Session title is required (minimum 3 characters)")

        date_str = data.get("date", "")
        if not date_str:
            errors.append("Date is required")
        else:
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except (ValueError, TypeError):
                errors.append("Invalid date format. Use YYYY-MM-DD")

        start_time = data.get("startTime", "")
        end_time = data.get("endTime", "")

        if not start_time:
            errors.append("Start time is required")
        else:
            try:
                st = datetime.strptime(start_time, "%H:%M")
            except (ValueError, TypeError):
                errors.append("Invalid start time format. Use HH:MM")
                st = None

        if not end_time:
            errors.append("End time is required")
        else:
            try:
                et = datetime.strptime(end_time, "%H:%M")
            except (ValueError, TypeError):
                errors.append("Invalid end time format. Use HH:MM")
                et = None

        if start_time and end_time:
            try:
                st_check = datetime.strptime(start_time, "%H:%M")
                et_check = datetime.strptime(end_time, "%H:%M")
                if et_check <= st_check:
                    errors.append("End time must be after start time")
            except (ValueError, TypeError):
                pass

        return len(errors) == 0, errors

    @staticmethod
    def validate_user(data):
        """
        Validate user registration data.

        Args:
            data: dict with username, email, password

        Returns:
            Tuple of (is_valid: bool, errors: list of str)
        """
        errors = []

        if not data or not isinstance(data, dict):
            return False, ["User data is required"]

        username = data.get("username", "")
        if not username or len(username.strip()) < 2:
            errors.append("Username is required (minimum 2 characters)")

        email = data.get("email", "")
        if not email:
            errors.append("Email is required")
        elif not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            errors.append("Invalid email format")

        password = data.get("password", "")
        if not password:
            errors.append("Password is required")
        elif len(password) < 8:
            errors.append("Password must be at least 8 characters")

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

        text = re.sub(r"<[^>]*>", "", text)
        text = re.sub(r"(javascript|script|onclick|onerror):", "", text, flags=re.IGNORECASE)
        text = text.strip()

        return text
