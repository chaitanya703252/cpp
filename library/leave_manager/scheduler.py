"""
Session Scheduler - handles study session scheduling and time conflict detection.
"""

from datetime import datetime, timedelta


class SessionScheduler:
    """Manages study session scheduling, conflict detection, and weekly planning."""

    DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    @staticmethod
    def check_time_conflict(new_session, existing_sessions):
        """
        Check if a new session conflicts with any existing sessions on the same date.

        Args:
            new_session: dict with date, startTime, endTime (HH:MM format)
            existing_sessions: list of session dicts

        Returns:
            True if conflict found, False otherwise
        """
        new_date = new_session.get("date", "")
        new_start = new_session.get("startTime", "")
        new_end = new_session.get("endTime", "")

        for existing in existing_sessions:
            if existing.get("date") != new_date:
                continue
            if new_session.get("sessionId") and existing.get("sessionId") == new_session.get("sessionId"):
                continue

            ex_start = existing.get("startTime", "")
            ex_end = existing.get("endTime", "")

            if new_start < ex_end and new_end > ex_start:
                return True

        return False

    @staticmethod
    def find_conflicts(session, all_sessions):
        """
        Find all sessions that conflict with the given session.

        Args:
            session: dict with date, startTime, endTime
            all_sessions: list of all session dicts

        Returns:
            List of conflicting session dicts
        """
        conflicts = []
        session_date = session.get("date", "")
        session_start = session.get("startTime", "")
        session_end = session.get("endTime", "")

        for other in all_sessions:
            if other.get("sessionId") == session.get("sessionId"):
                continue
            if other.get("date") != session_date:
                continue

            other_start = other.get("startTime", "")
            other_end = other.get("endTime", "")

            if session_start < other_end and session_end > other_start:
                conflicts.append(other)

        return conflicts

    @staticmethod
    def get_weekly_schedule(sessions, week_start_date):
        """
        Build a weekly schedule from a list of sessions.

        Args:
            sessions: list of session dicts with date, startTime, endTime, title
            week_start_date: start date string (YYYY-MM-DD) for the week (Monday)

        Returns:
            Dict mapping day names to lists of sessions for that day
        """
        if isinstance(week_start_date, str):
            start = datetime.strptime(week_start_date, "%Y-%m-%d").date()
        else:
            start = week_start_date

        # Adjust to Monday
        start = start - timedelta(days=start.weekday())

        schedule = {}
        for i in range(7):
            day_date = start + timedelta(days=i)
            day_name = SessionScheduler.DAYS_OF_WEEK[i]
            date_str = day_date.strftime("%Y-%m-%d")

            day_sessions = [
                s for s in sessions if s.get("date") == date_str
            ]
            day_sessions.sort(key=lambda x: x.get("startTime", ""))
            schedule[day_name] = day_sessions

        return schedule

    @staticmethod
    def calculate_duration_minutes(start_time, end_time):
        """
        Calculate the duration in minutes between two times.

        Args:
            start_time: start time string HH:MM
            end_time: end time string HH:MM

        Returns:
            Duration in minutes (int)

        Raises:
            ValueError: if times are invalid or end <= start
        """
        try:
            start = datetime.strptime(start_time, "%H:%M")
            end = datetime.strptime(end_time, "%H:%M")
        except (ValueError, TypeError):
            raise ValueError("Invalid time format. Use HH:MM")

        if end <= start:
            raise ValueError("End time must be after start time")

        delta = end - start
        return int(delta.total_seconds() / 60)

    @staticmethod
    def suggest_time_slots(existing_sessions, date, min_duration=60):
        """
        Suggest available time slots on a given date.

        Args:
            existing_sessions: list of session dicts for that date
            date: date string YYYY-MM-DD
            min_duration: minimum slot duration in minutes (default 60)

        Returns:
            List of available slot dicts with startTime and endTime
        """
        day_sessions = [
            s for s in existing_sessions if s.get("date") == date
        ]
        day_sessions.sort(key=lambda x: x.get("startTime", ""))

        # Study hours: 08:00 to 21:00
        day_start = "08:00"
        day_end = "21:00"

        occupied = [(s.get("startTime", ""), s.get("endTime", "")) for s in day_sessions]

        slots = []
        current = day_start

        for occ_start, occ_end in occupied:
            if current < occ_start:
                start_dt = datetime.strptime(current, "%H:%M")
                end_dt = datetime.strptime(occ_start, "%H:%M")
                if (end_dt - start_dt).total_seconds() / 60 >= min_duration:
                    slots.append({"startTime": current, "endTime": occ_start})
            if occ_end > current:
                current = occ_end

        if current < day_end:
            start_dt = datetime.strptime(current, "%H:%M")
            end_dt = datetime.strptime(day_end, "%H:%M")
            if (end_dt - start_dt).total_seconds() / 60 >= min_duration:
                slots.append({"startTime": current, "endTime": day_end})

        return slots

    @staticmethod
    def get_total_study_hours(sessions):
        """
        Calculate total study hours from a list of sessions.

        Args:
            sessions: list of session dicts with startTime and endTime

        Returns:
            Total hours as float rounded to 1 decimal
        """
        total_minutes = 0
        for s in sessions:
            try:
                start = datetime.strptime(s.get("startTime", ""), "%H:%M")
                end = datetime.strptime(s.get("endTime", ""), "%H:%M")
                if end > start:
                    total_minutes += int((end - start).total_seconds() / 60)
            except (ValueError, TypeError):
                continue

        return round(total_minutes / 60, 1)
