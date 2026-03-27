# leave-manager-nci

Employee Leave Management Library for the LeaveFlow system.

## Author

Lakshmi Chaitanya (X25171216) - National College of Ireland

## Installation

```bash
pip install leave-manager-nci
```

## Modules

### LeaveBalanceManager
Manages employee leave balances including deductions, restorations, and business day calculations.

```python
from leave_manager import LeaveBalanceManager

balances = LeaveBalanceManager.get_default_balances()
# {'annual': 20, 'sick': 10, 'unpaid': 30}

days = LeaveBalanceManager.calculate_days("2026-04-01", "2026-04-05")
LeaveBalanceManager.deduct_leave(balances, "annual", days)
```

### OverlapDetector
Detects overlapping leave requests and manages date conflicts.

```python
from leave_manager import OverlapDetector

new_request = {"startDate": "2026-04-01", "endDate": "2026-04-05"}
existing = [{"startDate": "2026-04-03", "endDate": "2026-04-07"}]
has_overlap = OverlapDetector.check_overlap(new_request, existing)
```

### LeaveValidator
Validates leave requests, employee data, and approval payloads.

```python
from leave_manager import LeaveValidator

valid, errors = LeaveValidator.validate_leave_request({
    "leaveType": "annual",
    "startDate": "2026-04-01",
    "endDate": "2026-04-05",
    "reason": "Family vacation planned"
})
```

### LeaveFormatter
Formats leave data for display, notifications, and CSV export.

```python
from leave_manager import LeaveFormatter

summary = LeaveFormatter.format_request_summary(request)
csv_data = LeaveFormatter.to_csv(requests)
calendar = LeaveFormatter.format_team_calendar(requests, "2026-04")
```

## Testing

```bash
cd library
python -m pytest tests/ -v
```

## License

MIT
