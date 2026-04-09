"""
Schedule Formatter - formats study schedules, group info, and session data for display and export.
"""

import csv
import io
from datetime import datetime, timedelta


class ScheduleFormatter:
    """Formats study group sessions, schedules, and reports for display."""

    DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    @staticmethod
    def format_session_summary(session):
        """
        Format a study session into a readable summary string.

        Args:
            session: dict with title, date, startTime, endTime, location, groupName

        Returns:
            Formatted summary string
        """
        title = session.get("title", "Untitled Session")
        date = session.get("date", "N/A")
        start = session.get("startTime", "N/A")
        end = session.get("endTime", "N/A")
        location = session.get("location", "Not specified")
        group_name = session.get("groupName", "Unknown Group")
        is_online = session.get("isOnline", False)

        return (
            f"Study Session Summary\n"
            f"{'=' * 40}\n"
            f"Title    : {title}\n"
            f"Group    : {group_name}\n"
            f"Date     : {date}\n"
            f"Time     : {start} - {end}\n"
            f"Location : {'Online' if is_online else location}\n"
            f"{'=' * 40}"
        )

    @staticmethod
    def format_group_report(group_name, subject, members, sessions):
        """
        Format a study group report with members and session summary.

        Args:
            group_name: name of the study group
            subject: the subject area
            members: list of member dicts with username and role
            sessions: list of session dicts

        Returns:
            Formatted report string
        """
        lines = [
            f"Study Group Report - {group_name}",
            "=" * 50,
            f"Subject  : {subject.capitalize() if subject else 'N/A'}",
            f"Members  : {len(members)}",
            f"Sessions : {len(sessions)}",
            "",
            "Members:",
            "-" * 30,
        ]

        for m in members:
            role_label = " (Organizer)" if m.get("role") == "organizer" else ""
            lines.append(f"  - {m.get('username', 'Unknown')}{role_label}")

        lines.append("")
        lines.append("Upcoming Sessions:")
        lines.append("-" * 30)

        if sessions:
            for s in sessions:
                lines.append(
                    f"  {s.get('date', 'N/A')} | {s.get('startTime', '')}-{s.get('endTime', '')} | {s.get('title', 'Untitled')}"
                )
        else:
            lines.append("  No upcoming sessions scheduled")

        lines.append("=" * 50)
        return "\n".join(lines)

    @staticmethod
    def format_weekly_schedule(sessions, week_start_date):
        """
        Format a weekly schedule showing all sessions organized by day.

        Args:
            sessions: list of session dicts
            week_start_date: start date string YYYY-MM-DD (Monday)

        Returns:
            Formatted weekly schedule string
        """
        try:
            if isinstance(week_start_date, str):
                start = datetime.strptime(week_start_date, "%Y-%m-%d").date()
            else:
                start = week_start_date
        except (ValueError, AttributeError):
            return "Invalid date format. Use YYYY-MM-DD"

        start = start - timedelta(days=start.weekday())

        lines = [
            f"Weekly Study Schedule",
            f"Week of {start.strftime('%B %d, %Y')}",
            "=" * 55,
        ]

        for i in range(7):
            day_date = start + timedelta(days=i)
            day_name = ScheduleFormatter.DAYS_OF_WEEK[i]
            date_str = day_date.strftime("%Y-%m-%d")

            day_sessions = [s for s in sessions if s.get("date") == date_str]
            day_sessions.sort(key=lambda x: x.get("startTime", ""))

            lines.append(f"\n{day_name} ({date_str}):")
            if day_sessions:
                for s in day_sessions:
                    location = "Online" if s.get("isOnline") else s.get("location", "TBD")
                    lines.append(
                        f"  {s.get('startTime', '')}-{s.get('endTime', '')} | "
                        f"{s.get('title', 'Untitled')} @ {location}"
                    )
            else:
                lines.append("  No sessions scheduled")

        lines.append("\n" + "=" * 55)
        return "\n".join(lines)

    @staticmethod
    def to_csv(sessions):
        """
        Convert a list of sessions to CSV format.

        Args:
            sessions: list of session dicts

        Returns:
            CSV string
        """
        if not sessions:
            return ""

        output = io.StringIO()
        fields = [
            "sessionId", "title", "groupName", "date",
            "startTime", "endTime", "location", "isOnline",
        ]
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()

        for s in sessions:
            row = {
                "sessionId": s.get("id", s.get("sessionId", "")),
                "title": s.get("title", ""),
                "groupName": s.get("groupName", ""),
                "date": s.get("date", ""),
                "startTime": s.get("startTime", ""),
                "endTime": s.get("endTime", ""),
                "location": s.get("location", ""),
                "isOnline": s.get("isOnline", False),
            }
            writer.writerow(row)

        return output.getvalue()

    @staticmethod
    def format_session_notification(session, group_name, action="created"):
        """
        Format a session notification message.

        Args:
            session: the session dict
            group_name: name of the study group
            action: 'created', 'updated', or 'cancelled'

        Returns:
            Formatted notification string
        """
        title = session.get("title", "Study Session")
        date = session.get("date", "N/A")
        start = session.get("startTime", "N/A")
        end = session.get("endTime", "N/A")
        location = session.get("location", "Not specified")

        msg = (
            f"Study Session {action.upper()}\n"
            f"{'-' * 35}\n"
            f"Group    : {group_name}\n"
            f"Session  : {title}\n"
            f"Date     : {date}\n"
            f"Time     : {start} - {end}\n"
            f"Location : {location}\n"
            f"{'-' * 35}"
        )

        return msg
