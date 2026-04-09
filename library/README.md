# studygroup-scheduler-nci

Study Group Scheduling Library for StudySync - a student study group finder and scheduler.

## Author

Lakshmi Chaitanya (X25171216) - National College of Ireland

## Installation

```bash
pip install studygroup-scheduler-nci
```

## Modules

### SessionScheduler
Handles study session scheduling, time conflict detection, and weekly planning.

```python
from leave_manager import SessionScheduler

conflict = SessionScheduler.check_time_conflict(new_session, existing_sessions)
schedule = SessionScheduler.get_weekly_schedule(sessions, "2026-04-06")
slots = SessionScheduler.suggest_time_slots(existing, "2026-04-10")
hours = SessionScheduler.get_total_study_hours(sessions)
```

### GroupMatcher
Matches students to relevant study groups based on subject overlap and preferences.

```python
from leave_manager import GroupMatcher

score = GroupMatcher.calculate_similarity(user_subjects, "mathematics")
recs = GroupMatcher.recommend_groups(user_subjects, all_groups)
popularity = GroupMatcher.get_subject_popularity(all_groups)
```

### InputValidator
Validates study groups, sessions, and user registration data.

```python
from leave_manager import InputValidator

valid, errors = InputValidator.validate_group(group_data)
valid, errors = InputValidator.validate_session(session_data)
clean = InputValidator.sanitize_input(user_input)
```

### ScheduleFormatter
Formats schedules, session summaries, group reports, and CSV export.

```python
from leave_manager import ScheduleFormatter

summary = ScheduleFormatter.format_session_summary(session)
report = ScheduleFormatter.format_weekly_schedule(sessions, "2026-04-06")
csv_data = ScheduleFormatter.to_csv(sessions)
```

## Testing

```bash
cd library
python -m pytest tests/ -v
```

## License

MIT
