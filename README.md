# LeaveFlow - Employee Leave Request System

**Student:** Kondragunta Lakshmi Chaitanya (X25171216)
**Module:** Cloud Platform Programming
**College:** National College of Ireland

## Overview

LeaveFlow is a serverless employee leave request management system. Employees submit leave requests (annual, sick, unpaid), managers approve or reject with comments, and the system tracks leave balances while blocking overlapping dates.

## Architecture

### AWS Services (6)
- **AWS Lambda** - Serverless backend API (leaveflow-api)
- **Amazon DynamoDB** - NoSQL database (leaveflow-prod)
- **Amazon API Gateway** - REST API endpoint (leaveflow-api)
- **Amazon S3** - File storage + frontend hosting
- **Amazon SNS** - Email notifications (leaveflow-notifications)
- **AWS IAM** - Role-based access control (leaveflow-lambda-role)

**Region:** eu-west-1 (Ireland)

## Project Structure

```
Chaitanya/
├── library/                  # Custom Python library (leave-manager-nci)
│   ├── leave_manager/
│   │   ├── __init__.py       # Package exports, v1.0.0
│   │   ├── balance.py        # LeaveBalanceManager
│   │   ├── overlap.py        # OverlapDetector
│   │   ├── validator.py      # LeaveValidator
│   │   └── formatter.py      # LeaveFormatter
│   ├── tests/
│   │   └── test_leave.py     # 30+ unit tests
│   ├── setup.py
│   └── README.md
├── backend/
│   ├── lambda_function.py    # Single Lambda handler
│   └── requirements.txt
├── frontend/                 # React 19 + Vite + Tailwind v4
│   ├── src/
│   │   ├── pages/            # Dashboard, RequestLeave, MyLeaves, Approvals, TeamCalendar, Balances
│   │   ├── components/       # Navbar, StatusBadge
│   │   ├── context/          # AuthContext
│   │   └── api.js            # Axios API client
│   └── ...
├── .github/workflows/
│   └── deploy.yml            # CI/CD pipeline
├── .gitignore
└── README.md
```

## API Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | /auth/register | Register user | Public |
| POST | /auth/login | Login | Public |
| GET | /leaves | List leaves | Required |
| POST | /leaves | Submit leave request | Required |
| GET | /leaves/{id} | Get leave details | Required |
| DELETE | /leaves/{id} | Cancel pending leave | Required |
| PUT | /leaves/{id}/approve | Approve/reject leave | Manager |
| GET | /employees | List employees | Manager |
| GET | /employees/{id}/balance | Get leave balance | Required |
| GET | /dashboard | Dashboard data | Required |
| POST | /subscribe | Subscribe to notifications | Public |
| GET | /subscribers | List subscribers | Public |

## Custom Library: leave-manager-nci

- **LeaveBalanceManager** - Default balances, deduction, restoration, business day calculation
- **OverlapDetector** - Overlap checking, conflict detection, busy date tracking
- **LeaveValidator** - Request validation, employee validation, approval validation, input sanitization
- **LeaveFormatter** - Request summaries, balance reports, team calendars, CSV export, notification formatting

## Running Locally

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Library Tests
```bash
cd library
pip install -e .
python -m pytest tests/ -v
```

## Deployment

Push to `main` branch triggers the CI/CD pipeline which:
1. Runs library tests and frontend build
2. Creates AWS infrastructure (DynamoDB, S3, SNS, IAM)
3. Deploys Lambda function with API Gateway
4. Builds and deploys frontend to S3

## GitHub

Repository: https://github.com/chaitanya703252/cpp
