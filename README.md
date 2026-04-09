# StudySync - Student Study Group Finder & Scheduler

**Student:** Kondragunta Lakshmi Chaitanya (X25171216)
**Module:** Cloud Platform Programming
**College:** National College of Ireland

## Overview

StudySync is a serverless web application that helps students find study groups by subject, join groups, and schedule study sessions. It features subject-based group discovery, time conflict detection, weekly schedule views, and SNS notifications for new sessions.

## Architecture

### AWS Services (6)
- **AWS Lambda** - Serverless backend API (studysync-api)
- **Amazon DynamoDB** - NoSQL database (studysync-prod)
- **Amazon API Gateway** - REST API endpoint (studysync-api)
- **Amazon S3** - File storage + frontend hosting
- **Amazon SNS** - Email notifications (studysync-notifications)
- **AWS IAM** - Role-based access control (studysync-lambda-role)

**Region:** eu-west-1 (Ireland)

## Project Structure

```
Chaitanya/
├── library/                  # Custom Python library (studygroup-scheduler-nci)
│   ├── leave_manager/
│   │   ├── __init__.py       # Package exports, v1.0.0
│   │   ├── scheduler.py      # SessionScheduler
│   │   ├── matcher.py        # GroupMatcher
│   │   ├── validator.py      # InputValidator
│   │   └── formatter.py      # ScheduleFormatter
│   ├── tests/
│   │   └── test_leave.py     # 45+ unit tests
│   ├── setup.py
│   └── README.md
├── backend/
│   ├── lambda_function.py    # Single Lambda handler
│   └── requirements.txt
├── frontend/                 # React 19 + Vite + Tailwind
│   ├── src/
│   │   ├── pages/            # Dashboard, BrowseGroups, GroupDetail, MyGroups, CreateGroup, WeeklySchedule
│   │   ├── components/       # Navbar, SubjectBadge, RoleBadge
│   │   ├── context/          # AuthContext
│   │   └── api.js            # Axios API client
│   └── ...
├── .github/workflows/
│   └── deploy.yml            # CI/CD pipeline (3 jobs)
├── .gitignore
└── README.md
```

## API Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | /auth/register | Register user (with university + subjects) | Public |
| POST | /auth/login | Login | Public |
| GET | /groups | Browse groups (filter by subject/search) | Required |
| POST | /groups | Create study group | Required |
| GET | /groups/{id} | Group detail with members & sessions | Required |
| PUT | /groups/{id} | Update group | Organizer |
| DELETE | /groups/{id} | Delete group | Creator |
| POST | /groups/{id}/join | Join a group | Required |
| DELETE | /groups/{id}/leave | Leave a group | Member |
| GET | /groups/{id}/sessions | Get sessions | Required |
| POST | /groups/{id}/sessions | Schedule a session | Member |
| PUT | /groups/{id}/sessions/{sid} | Update session | Creator/Organizer |
| DELETE | /groups/{id}/sessions/{sid} | Delete session | Creator/Organizer |
| GET | /my-groups | User's groups | Required |
| GET | /dashboard | Dashboard stats | Required |
| POST | /subscribe | Subscribe to notifications | Public |
| GET | /subscribers | List subscribers | Public |

## Custom Library: studygroup-scheduler-nci

- **SessionScheduler** - Time conflict detection, weekly schedule builder, duration calculator, slot suggestions, total study hours
- **GroupMatcher** - Subject similarity scoring, group recommendations, subject popularity, availability checks
- **InputValidator** - Group validation, session validation, user validation, input sanitization
- **ScheduleFormatter** - Session summaries, group reports, weekly schedules, CSV export, notifications

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
1. Runs library tests (45+ unit tests)
2. Creates AWS infrastructure (DynamoDB, S3, SNS, IAM)
3. Deploys Lambda function with API Gateway
4. Builds and deploys frontend to S3

## GitHub

Repository: https://github.com/chaitanya703252/cpp
