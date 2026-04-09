"""
Tests for the studygroup-scheduler-nci library.
45+ test cases covering scheduler, matcher, validator, and formatter modules.
"""

import unittest
from datetime import datetime, timedelta

from leave_manager.scheduler import SessionScheduler
from leave_manager.matcher import GroupMatcher
from leave_manager.validator import InputValidator
from leave_manager.formatter import ScheduleFormatter


class TestSessionScheduler(unittest.TestCase):
    """Tests for SessionScheduler."""

    def test_check_time_conflict_true(self):
        new = {"date": "2026-04-10", "startTime": "10:00", "endTime": "11:30"}
        existing = [{"date": "2026-04-10", "startTime": "11:00", "endTime": "12:00"}]
        self.assertTrue(SessionScheduler.check_time_conflict(new, existing))

    def test_check_time_conflict_false(self):
        new = {"date": "2026-04-10", "startTime": "10:00", "endTime": "11:00"}
        existing = [{"date": "2026-04-10", "startTime": "11:00", "endTime": "12:00"}]
        self.assertFalse(SessionScheduler.check_time_conflict(new, existing))

    def test_check_time_conflict_different_date(self):
        new = {"date": "2026-04-10", "startTime": "10:00", "endTime": "11:30"}
        existing = [{"date": "2026-04-11", "startTime": "10:00", "endTime": "12:00"}]
        self.assertFalse(SessionScheduler.check_time_conflict(new, existing))

    def test_check_time_conflict_same_session_ignored(self):
        new = {"sessionId": "s1", "date": "2026-04-10", "startTime": "10:00", "endTime": "11:00"}
        existing = [{"sessionId": "s1", "date": "2026-04-10", "startTime": "10:00", "endTime": "11:00"}]
        self.assertFalse(SessionScheduler.check_time_conflict(new, existing))

    def test_find_conflicts(self):
        session = {"sessionId": "s1", "date": "2026-04-10", "startTime": "10:00", "endTime": "12:00"}
        all_sessions = [
            {"sessionId": "s1", "date": "2026-04-10", "startTime": "10:00", "endTime": "12:00"},
            {"sessionId": "s2", "date": "2026-04-10", "startTime": "11:00", "endTime": "13:00"},
            {"sessionId": "s3", "date": "2026-04-10", "startTime": "14:00", "endTime": "15:00"},
        ]
        conflicts = SessionScheduler.find_conflicts(session, all_sessions)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["sessionId"], "s2")

    def test_get_weekly_schedule(self):
        sessions = [
            {"date": "2026-04-06", "startTime": "10:00", "endTime": "11:00", "title": "Math"},
            {"date": "2026-04-08", "startTime": "14:00", "endTime": "15:00", "title": "Physics"},
        ]
        schedule = SessionScheduler.get_weekly_schedule(sessions, "2026-04-06")
        self.assertEqual(len(schedule["Monday"]), 1)
        self.assertEqual(len(schedule["Wednesday"]), 1)
        self.assertEqual(len(schedule["Tuesday"]), 0)

    def test_get_weekly_schedule_empty(self):
        schedule = SessionScheduler.get_weekly_schedule([], "2026-04-06")
        for day in SessionScheduler.DAYS_OF_WEEK:
            self.assertEqual(len(schedule[day]), 0)

    def test_calculate_duration_minutes(self):
        result = SessionScheduler.calculate_duration_minutes("10:00", "11:30")
        self.assertEqual(result, 90)

    def test_calculate_duration_one_hour(self):
        result = SessionScheduler.calculate_duration_minutes("14:00", "15:00")
        self.assertEqual(result, 60)

    def test_calculate_duration_invalid_range(self):
        with self.assertRaises(ValueError):
            SessionScheduler.calculate_duration_minutes("15:00", "14:00")

    def test_calculate_duration_invalid_format(self):
        with self.assertRaises(ValueError):
            SessionScheduler.calculate_duration_minutes("bad", "14:00")

    def test_suggest_time_slots(self):
        existing = [
            {"date": "2026-04-10", "startTime": "10:00", "endTime": "12:00"},
            {"date": "2026-04-10", "startTime": "14:00", "endTime": "16:00"},
        ]
        slots = SessionScheduler.suggest_time_slots(existing, "2026-04-10")
        self.assertTrue(len(slots) >= 2)
        self.assertEqual(slots[0]["startTime"], "08:00")
        self.assertEqual(slots[0]["endTime"], "10:00")

    def test_suggest_time_slots_empty_day(self):
        slots = SessionScheduler.suggest_time_slots([], "2026-04-10")
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]["startTime"], "08:00")
        self.assertEqual(slots[0]["endTime"], "21:00")

    def test_get_total_study_hours(self):
        sessions = [
            {"startTime": "10:00", "endTime": "12:00"},
            {"startTime": "14:00", "endTime": "15:30"},
        ]
        hours = SessionScheduler.get_total_study_hours(sessions)
        self.assertEqual(hours, 3.5)

    def test_get_total_study_hours_empty(self):
        hours = SessionScheduler.get_total_study_hours([])
        self.assertEqual(hours, 0.0)


class TestGroupMatcher(unittest.TestCase):
    """Tests for GroupMatcher."""

    def test_calculate_similarity_exact_match(self):
        score = GroupMatcher.calculate_similarity(["mathematics", "physics"], "mathematics")
        self.assertEqual(score, 1.0)

    def test_calculate_similarity_no_match(self):
        score = GroupMatcher.calculate_similarity(["law", "history"], "chemistry")
        self.assertEqual(score, 0.0)

    def test_calculate_similarity_related(self):
        score = GroupMatcher.calculate_similarity(["mathematics"], "physics")
        self.assertEqual(score, 0.4)

    def test_calculate_similarity_partial(self):
        score = GroupMatcher.calculate_similarity(["computer"], "computer_science")
        self.assertEqual(score, 0.7)

    def test_calculate_similarity_empty_user(self):
        score = GroupMatcher.calculate_similarity([], "physics")
        self.assertEqual(score, 0.0)

    def test_calculate_similarity_empty_group(self):
        score = GroupMatcher.calculate_similarity(["math"], "")
        self.assertEqual(score, 0.0)

    def test_recommend_groups(self):
        groups = [
            {"id": "1", "subject": "mathematics"},
            {"id": "2", "subject": "physics"},
            {"id": "3", "subject": "law"},
        ]
        recs = GroupMatcher.recommend_groups(["mathematics"], groups)
        self.assertTrue(len(recs) >= 1)
        self.assertEqual(recs[0][0]["id"], "1")
        self.assertEqual(recs[0][1], 1.0)

    def test_recommend_groups_limit(self):
        groups = [{"id": str(i), "subject": "mathematics"} for i in range(10)]
        recs = GroupMatcher.recommend_groups(["mathematics"], groups, limit=3)
        self.assertEqual(len(recs), 3)

    def test_find_groups_by_subject(self):
        groups = [
            {"id": "1", "subject": "Mathematics"},
            {"id": "2", "subject": "physics"},
            {"id": "3", "subject": "Mathematics"},
        ]
        result = GroupMatcher.find_groups_by_subject("mathematics", groups)
        self.assertEqual(len(result), 2)

    def test_find_groups_by_subject_empty(self):
        result = GroupMatcher.find_groups_by_subject("", [{"subject": "math"}])
        self.assertEqual(len(result), 0)

    def test_get_subject_popularity(self):
        groups = [
            {"subject": "math"},
            {"subject": "math"},
            {"subject": "physics"},
        ]
        pop = GroupMatcher.get_subject_popularity(groups)
        self.assertEqual(pop["math"], 2)
        self.assertEqual(pop["physics"], 1)
        first_key = list(pop.keys())[0]
        self.assertEqual(first_key, "math")

    def test_check_group_availability_has_spots(self):
        group = {"maxMembers": 10}
        available, spots = GroupMatcher.check_group_availability(group, 5)
        self.assertTrue(available)
        self.assertEqual(spots, 5)

    def test_check_group_availability_full(self):
        group = {"maxMembers": 10}
        available, spots = GroupMatcher.check_group_availability(group, 10)
        self.assertFalse(available)
        self.assertEqual(spots, 0)

    def test_check_group_availability_over_capacity(self):
        group = {"maxMembers": 5}
        available, spots = GroupMatcher.check_group_availability(group, 7)
        self.assertFalse(available)
        self.assertEqual(spots, 0)


class TestInputValidator(unittest.TestCase):
    """Tests for InputValidator."""

    def test_validate_group_valid(self):
        data = {
            "name": "Calculus Study Group",
            "subject": "mathematics",
            "description": "Weekly calculus review sessions for exam prep",
            "maxMembers": 8,
        }
        valid, errors = InputValidator.validate_group(data)
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)

    def test_validate_group_missing_name(self):
        data = {"subject": "math", "description": "A good description here", "maxMembers": 8}
        valid, errors = InputValidator.validate_group(data)
        self.assertFalse(valid)

    def test_validate_group_short_description(self):
        data = {"name": "Test Group", "subject": "math", "description": "Short", "maxMembers": 8}
        valid, errors = InputValidator.validate_group(data)
        self.assertFalse(valid)

    def test_validate_group_invalid_max_members(self):
        data = {"name": "Test Group", "subject": "math", "description": "A good description here", "maxMembers": 50}
        valid, errors = InputValidator.validate_group(data)
        self.assertFalse(valid)

    def test_validate_group_none(self):
        valid, errors = InputValidator.validate_group(None)
        self.assertFalse(valid)

    def test_validate_session_valid(self):
        data = {
            "title": "Calculus Review",
            "date": "2026-04-15",
            "startTime": "10:00",
            "endTime": "11:30",
        }
        valid, errors = InputValidator.validate_session(data)
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)

    def test_validate_session_missing_title(self):
        data = {"date": "2026-04-15", "startTime": "10:00", "endTime": "11:30"}
        valid, errors = InputValidator.validate_session(data)
        self.assertFalse(valid)

    def test_validate_session_invalid_date(self):
        data = {"title": "Review", "date": "bad-date", "startTime": "10:00", "endTime": "11:30"}
        valid, errors = InputValidator.validate_session(data)
        self.assertFalse(valid)

    def test_validate_session_end_before_start(self):
        data = {"title": "Review", "date": "2026-04-15", "startTime": "15:00", "endTime": "14:00"}
        valid, errors = InputValidator.validate_session(data)
        self.assertFalse(valid)

    def test_validate_session_none(self):
        valid, errors = InputValidator.validate_session(None)
        self.assertFalse(valid)

    def test_validate_user_valid(self):
        data = {"username": "John", "email": "john@example.com", "password": "password123"}
        valid, errors = InputValidator.validate_user(data)
        self.assertTrue(valid)

    def test_validate_user_invalid_email(self):
        data = {"username": "John", "email": "not-an-email", "password": "password123"}
        valid, errors = InputValidator.validate_user(data)
        self.assertFalse(valid)

    def test_validate_user_short_password(self):
        data = {"username": "John", "email": "john@example.com", "password": "short"}
        valid, errors = InputValidator.validate_user(data)
        self.assertFalse(valid)

    def test_sanitize_input_removes_html(self):
        result = InputValidator.sanitize_input("<script>alert('xss')</script>Hello")
        self.assertNotIn("<script>", result)
        self.assertIn("Hello", result)

    def test_sanitize_input_strips_whitespace(self):
        result = InputValidator.sanitize_input("  hello  ")
        self.assertEqual(result, "hello")

    def test_sanitize_input_none(self):
        result = InputValidator.sanitize_input(None)
        self.assertEqual(result, "")


class TestScheduleFormatter(unittest.TestCase):
    """Tests for ScheduleFormatter."""

    def test_format_session_summary(self):
        session = {
            "title": "Algebra Review",
            "date": "2026-04-10",
            "startTime": "10:00",
            "endTime": "11:30",
            "location": "Library Room 201",
            "groupName": "Math Wizards",
            "isOnline": False,
        }
        result = ScheduleFormatter.format_session_summary(session)
        self.assertIn("Algebra Review", result)
        self.assertIn("Math Wizards", result)
        self.assertIn("Library Room 201", result)

    def test_format_session_summary_online(self):
        session = {
            "title": "Physics Lab",
            "date": "2026-04-10",
            "startTime": "14:00",
            "endTime": "15:00",
            "isOnline": True,
        }
        result = ScheduleFormatter.format_session_summary(session)
        self.assertIn("Online", result)

    def test_format_group_report(self):
        members = [
            {"username": "Alice", "role": "organizer"},
            {"username": "Bob", "role": "member"},
        ]
        sessions = [
            {"date": "2026-04-10", "startTime": "10:00", "endTime": "11:00", "title": "Review"},
        ]
        result = ScheduleFormatter.format_group_report("Math Group", "mathematics", members, sessions)
        self.assertIn("Math Group", result)
        self.assertIn("Alice", result)
        self.assertIn("Organizer", result)
        self.assertIn("Review", result)

    def test_format_group_report_no_sessions(self):
        result = ScheduleFormatter.format_group_report("Empty Group", "physics", [], [])
        self.assertIn("No upcoming sessions", result)

    def test_format_weekly_schedule(self):
        sessions = [
            {"date": "2026-04-06", "startTime": "10:00", "endTime": "11:00", "title": "Math", "isOnline": False, "location": "Room 1"},
        ]
        result = ScheduleFormatter.format_weekly_schedule(sessions, "2026-04-06")
        self.assertIn("Monday", result)
        self.assertIn("Math", result)

    def test_format_weekly_schedule_invalid_date(self):
        result = ScheduleFormatter.format_weekly_schedule([], "bad-date")
        self.assertIn("Invalid", result)

    def test_to_csv(self):
        sessions = [
            {
                "id": "s1",
                "title": "Physics Lab",
                "groupName": "Science Club",
                "date": "2026-04-10",
                "startTime": "10:00",
                "endTime": "11:30",
                "location": "Lab 101",
                "isOnline": False,
            }
        ]
        result = ScheduleFormatter.to_csv(sessions)
        self.assertIn("sessionId", result)
        self.assertIn("Physics Lab", result)
        self.assertIn("Science Club", result)

    def test_to_csv_empty(self):
        result = ScheduleFormatter.to_csv([])
        self.assertEqual(result, "")

    def test_format_session_notification_created(self):
        session = {
            "title": "Calculus Review",
            "date": "2026-04-15",
            "startTime": "10:00",
            "endTime": "11:30",
            "location": "Room 301",
        }
        result = ScheduleFormatter.format_session_notification(session, "Math Stars", "created")
        self.assertIn("CREATED", result)
        self.assertIn("Math Stars", result)
        self.assertIn("Calculus Review", result)

    def test_format_session_notification_cancelled(self):
        session = {
            "title": "Lab Session",
            "date": "2026-04-15",
            "startTime": "14:00",
            "endTime": "15:00",
            "location": "Online",
        }
        result = ScheduleFormatter.format_session_notification(session, "Physics Group", "cancelled")
        self.assertIn("CANCELLED", result)
        self.assertIn("Physics Group", result)


if __name__ == "__main__":
    unittest.main()
