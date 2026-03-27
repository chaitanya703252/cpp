"""
LeaveFlow - Employee Leave Request System
AWS Lambda Function Handler

Student: Kondragunta Lakshmi Chaitanya (X25171216)
"""

import json
import os
import uuid
import hashlib
import hmac
import time
import re
from datetime import datetime, timedelta
from decimal import Decimal

import boto3
import jwt

# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "leaveflow-prod")
S3_BUCKET = os.environ.get("S3_BUCKET", "leaveflow-files-prod-chaitanya")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")
REGION = os.environ.get("REGION", "eu-west-1")
JWT_SECRET = os.environ.get("JWT_SECRET", "leaveflow-secret-2026")

# ---------------------------------------------------------------------------
# AWS clients
# ---------------------------------------------------------------------------
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(DYNAMODB_TABLE)
s3_client = boto3.client("s3", region_name=REGION)
sns_client = boto3.client("sns", region_name=REGION)

# ---------------------------------------------------------------------------
# Leave defaults
# ---------------------------------------------------------------------------
DEFAULT_BALANCES = {"annual": 20, "sick": 10, "unpaid": 30}
VALID_LEAVE_TYPES = ["annual", "sick", "unpaid"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class DecimalEncoder(json.JSONEncoder):
    """Handle Decimal types returned by DynamoDB."""
    def default(self, o):
        if isinstance(o, Decimal):
            return int(o) if o % 1 == 0 else float(o)
        return super().default(o)


def json_response(status_code, body):
    """Return an API Gateway-compatible response with CORS headers."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": json.dumps(body, cls=DecimalEncoder),
    }


def parse_body(event):
    """Parse JSON body from the event."""
    body = event.get("body", "{}")
    if isinstance(body, str):
        try:
            return json.loads(body)
        except (json.JSONDecodeError, TypeError):
            return {}
    return body or {}


def hash_password(password, salt=None):
    """Hash a password using PBKDF2-HMAC-SHA256."""
    if salt is None:
        salt = uuid.uuid4().hex
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return f"{salt}:{hashed.hex()}"


def verify_password(password, stored_hash):
    """Verify a password against a stored PBKDF2 hash."""
    salt, _ = stored_hash.split(":")
    return hash_password(password, salt) == stored_hash


def generate_token(user_id, email, role):
    """Generate a JWT token."""
    payload = {
        "userId": user_id,
        "email": email,
        "role": role,
        "exp": int(time.time()) + 86400,  # 24 hours
        "iat": int(time.time()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_token(token):
    """Decode and verify a JWT token."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_current_user(event):
    """Extract the current user from the Authorization header."""
    headers = event.get("headers", {}) or {}
    auth = headers.get("Authorization") or headers.get("authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        return decode_token(token)
    return None


def calculate_business_days(start_date_str, end_date_str):
    """Calculate business days (excluding weekends) between two dates."""
    start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    days = 0
    current = start
    while current <= end:
        if current.weekday() < 5:
            days += 1
        current += timedelta(days=1)
    return days


def to_decimal(obj):
    """Convert floats/ints in a dict to Decimal for DynamoDB."""
    if isinstance(obj, dict):
        return {k: to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_decimal(i) for i in obj]
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, int) and not isinstance(obj, bool):
        return Decimal(str(obj))
    return obj


def publish_notification(subject, message):
    """Publish a notification to SNS topic."""
    if not SNS_TOPIC_ARN:
        return
    try:
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject[:100],
            Message=message,
        )
    except Exception as e:
        print(f"SNS publish error: {e}")


# ---------------------------------------------------------------------------
# Auth handlers
# ---------------------------------------------------------------------------

def handle_register(event):
    """Register a new user."""
    body = parse_body(event)
    name = body.get("name", "").strip()
    email = body.get("email", "").strip().lower()
    password = body.get("password", "")
    role = body.get("role", "employee")
    department = body.get("department", "General")

    # Validation
    if not name or len(name) < 2:
        return json_response(400, {"error": "Name is required (minimum 2 characters)"})
    if not email or not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        return json_response(400, {"error": "Valid email is required"})
    if not password or len(password) < 8:
        return json_response(400, {"error": "Password must be at least 8 characters"})
    if role not in ["employee", "manager"]:
        return json_response(400, {"error": "Role must be 'employee' or 'manager'"})

    # Check if email already exists
    response = table.query(
        IndexName="GSI-Email",
        KeyConditionExpression=boto3.dynamodb.conditions.Key("GSI1PK").eq(f"EMAIL#{email}"),
    )
    if response.get("Items"):
        return json_response(409, {"error": "Email already registered"})

    user_id = str(uuid.uuid4())
    password_hash = hash_password(password)
    balances = to_decimal(DEFAULT_BALANCES.copy())
    now = datetime.utcnow().isoformat()

    item = {
        "PK": f"USER#{user_id}",
        "SK": "PROFILE",
        "GSI1PK": f"EMAIL#{email}",
        "GSI1SK": "PROFILE",
        "userId": user_id,
        "name": name,
        "email": email,
        "passwordHash": password_hash,
        "role": role,
        "department": department,
        "balances": balances,
        "createdAt": now,
        "entityType": "User",
    }
    table.put_item(Item=item)

    token = generate_token(user_id, email, role)

    return json_response(201, {
        "message": "Registration successful",
        "token": token,
        "user": {
            "userId": user_id,
            "name": name,
            "email": email,
            "role": role,
            "department": department,
            "balances": DEFAULT_BALANCES,
        },
    })


def handle_login(event):
    """Authenticate a user and return a JWT token."""
    body = parse_body(event)
    email = body.get("email", "").strip().lower()
    password = body.get("password", "")

    if not email or not password:
        return json_response(400, {"error": "Email and password are required"})

    response = table.query(
        IndexName="GSI-Email",
        KeyConditionExpression=boto3.dynamodb.conditions.Key("GSI1PK").eq(f"EMAIL#{email}"),
    )
    items = response.get("Items", [])
    if not items:
        return json_response(401, {"error": "Invalid email or password"})

    user = items[0]
    if not verify_password(password, user["passwordHash"]):
        return json_response(401, {"error": "Invalid email or password"})

    token = generate_token(user["userId"], email, user["role"])

    return json_response(200, {
        "message": "Login successful",
        "token": token,
        "user": {
            "userId": user["userId"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "department": user.get("department", "General"),
            "balances": user.get("balances", DEFAULT_BALANCES),
        },
    })


# ---------------------------------------------------------------------------
# Leave Request handlers
# ---------------------------------------------------------------------------

def handle_get_leaves(event):
    """GET /leaves - employees see own, managers see team's."""
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})

    if user["role"] == "manager":
        # Managers see all leave requests
        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr("entityType").eq("LeaveRequest"),
        )
    else:
        # Employees see only their own
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key("PK").eq(f"USER#{user['userId']}")
            & boto3.dynamodb.conditions.Key("SK").begins_with("LEAVE#"),
        )

    items = response.get("Items", [])
    leaves = []
    for item in items:
        leaves.append({
            "requestId": item.get("requestId"),
            "employeeId": item.get("employeeId"),
            "employeeName": item.get("employeeName"),
            "leaveType": item.get("leaveType"),
            "startDate": item.get("startDate"),
            "endDate": item.get("endDate"),
            "reason": item.get("reason"),
            "status": item.get("status"),
            "days": item.get("days"),
            "comments": item.get("comments", ""),
            "createdAt": item.get("createdAt"),
        })

    leaves.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
    return json_response(200, {"leaves": leaves})


def handle_create_leave(event):
    """POST /leaves - submit a leave request."""
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})

    body = parse_body(event)
    leave_type = body.get("leaveType", "")
    start_date = body.get("startDate", "")
    end_date = body.get("endDate", "")
    reason = body.get("reason", "")

    # Validation
    if leave_type not in VALID_LEAVE_TYPES:
        return json_response(400, {"error": f"Invalid leave type. Must be one of: {', '.join(VALID_LEAVE_TYPES)}"})
    if not start_date or not end_date:
        return json_response(400, {"error": "Start date and end date are required"})
    if not reason or len(reason.strip()) < 10:
        return json_response(400, {"error": "Reason is required (minimum 10 characters)"})

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return json_response(400, {"error": "Invalid date format. Use YYYY-MM-DD"})

    if start > end:
        return json_response(400, {"error": "Start date must be before or equal to end date"})

    days = calculate_business_days(start_date, end_date)
    if days == 0:
        return json_response(400, {"error": "Leave request must include at least one business day"})

    # Get user profile for balances and name
    user_profile = table.get_item(
        Key={"PK": f"USER#{user['userId']}", "SK": "PROFILE"}
    ).get("Item")
    if not user_profile:
        return json_response(404, {"error": "User profile not found"})

    balances = user_profile.get("balances", to_decimal(DEFAULT_BALANCES.copy()))

    # Check balance
    current_balance = int(balances.get(leave_type, 0))
    if current_balance < days:
        return json_response(400, {
            "error": f"Insufficient {leave_type} leave balance. Available: {current_balance}, Requested: {days}"
        })

    # Check overlaps with existing approved/pending leaves
    existing_response = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("PK").eq(f"USER#{user['userId']}")
        & boto3.dynamodb.conditions.Key("SK").begins_with("LEAVE#"),
    )
    existing_leaves = [
        item for item in existing_response.get("Items", [])
        if item.get("status") in ["pending", "approved"]
    ]

    for existing in existing_leaves:
        ex_start = datetime.strptime(existing["startDate"], "%Y-%m-%d").date()
        ex_end = datetime.strptime(existing["endDate"], "%Y-%m-%d").date()
        if start <= ex_end and end >= ex_start:
            return json_response(409, {"error": "Leave request overlaps with an existing request"})

    # Deduct balance and save
    request_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    balances[leave_type] = Decimal(str(current_balance - days))

    # Update user balances
    table.update_item(
        Key={"PK": f"USER#{user['userId']}", "SK": "PROFILE"},
        UpdateExpression="SET balances = :b",
        ExpressionAttributeValues={":b": balances},
    )

    # Create leave request
    leave_item = {
        "PK": f"USER#{user['userId']}",
        "SK": f"LEAVE#{request_id}",
        "GSI1PK": "LEAVES",
        "GSI1SK": now,
        "requestId": request_id,
        "employeeId": user["userId"],
        "employeeName": user_profile.get("name", "Unknown"),
        "leaveType": leave_type,
        "startDate": start_date,
        "endDate": end_date,
        "reason": reason,
        "status": "pending",
        "days": Decimal(str(days)),
        "comments": "",
        "createdAt": now,
        "entityType": "LeaveRequest",
    }
    table.put_item(Item=leave_item)

    return json_response(201, {
        "message": "Leave request submitted successfully",
        "request": {
            "requestId": request_id,
            "leaveType": leave_type,
            "startDate": start_date,
            "endDate": end_date,
            "reason": reason,
            "status": "pending",
            "days": days,
            "createdAt": now,
        },
    })


def handle_get_leave(event, request_id):
    """GET /leaves/{id} - get a specific leave request."""
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})

    # Try to find the leave request
    if user["role"] == "manager":
        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr("requestId").eq(request_id)
            & boto3.dynamodb.conditions.Attr("entityType").eq("LeaveRequest"),
        )
        items = response.get("Items", [])
    else:
        response = table.get_item(
            Key={"PK": f"USER#{user['userId']}", "SK": f"LEAVE#{request_id}"}
        )
        items = [response["Item"]] if "Item" in response else []

    if not items:
        return json_response(404, {"error": "Leave request not found"})

    item = items[0]
    return json_response(200, {
        "request": {
            "requestId": item.get("requestId"),
            "employeeId": item.get("employeeId"),
            "employeeName": item.get("employeeName"),
            "leaveType": item.get("leaveType"),
            "startDate": item.get("startDate"),
            "endDate": item.get("endDate"),
            "reason": item.get("reason"),
            "status": item.get("status"),
            "days": item.get("days"),
            "comments": item.get("comments", ""),
            "createdAt": item.get("createdAt"),
        },
    })


def handle_delete_leave(event, request_id):
    """DELETE /leaves/{id} - cancel a pending leave request and restore balance."""
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})

    response = table.get_item(
        Key={"PK": f"USER#{user['userId']}", "SK": f"LEAVE#{request_id}"}
    )
    item = response.get("Item")
    if not item:
        return json_response(404, {"error": "Leave request not found"})

    if item.get("status") != "pending":
        return json_response(400, {"error": "Only pending requests can be cancelled"})

    # Restore balance
    leave_type = item["leaveType"]
    days = int(item.get("days", 0))

    user_profile = table.get_item(
        Key={"PK": f"USER#{user['userId']}", "SK": "PROFILE"}
    ).get("Item")
    if user_profile:
        balances = user_profile.get("balances", {})
        current = int(balances.get(leave_type, 0))
        max_balance = DEFAULT_BALANCES.get(leave_type, 0)
        balances[leave_type] = Decimal(str(min(current + days, max_balance)))
        table.update_item(
            Key={"PK": f"USER#{user['userId']}", "SK": "PROFILE"},
            UpdateExpression="SET balances = :b",
            ExpressionAttributeValues={":b": balances},
        )

    # Delete the leave request
    table.delete_item(Key={"PK": f"USER#{user['userId']}", "SK": f"LEAVE#{request_id}"})

    return json_response(200, {"message": "Leave request cancelled successfully"})


# ---------------------------------------------------------------------------
# Approval handlers
# ---------------------------------------------------------------------------

def handle_approve_leave(event, request_id):
    """PUT /leaves/{id}/approve - manager approves or rejects a leave request."""
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})
    if user["role"] != "manager":
        return json_response(403, {"error": "Only managers can approve/reject leave requests"})

    body = parse_body(event)
    status = body.get("status", "")
    comments = body.get("comments", "")

    if status not in ["approved", "rejected"]:
        return json_response(400, {"error": "Status must be 'approved' or 'rejected'"})
    if status == "rejected" and not comments.strip():
        return json_response(400, {"error": "Comments are required when rejecting a request"})

    # Find the leave request
    response = table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr("requestId").eq(request_id)
        & boto3.dynamodb.conditions.Attr("entityType").eq("LeaveRequest"),
    )
    items = response.get("Items", [])
    if not items:
        return json_response(404, {"error": "Leave request not found"})

    leave = items[0]
    if leave.get("status") != "pending":
        return json_response(400, {"error": "Only pending requests can be approved/rejected"})

    employee_id = leave["employeeId"]
    pk = leave["PK"]
    sk = leave["SK"]

    # Update leave request status
    table.update_item(
        Key={"PK": pk, "SK": sk},
        UpdateExpression="SET #s = :s, comments = :c",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": status, ":c": comments},
    )

    # If rejected, restore balance
    if status == "rejected":
        leave_type = leave["leaveType"]
        days = int(leave.get("days", 0))

        user_profile = table.get_item(
            Key={"PK": f"USER#{employee_id}", "SK": "PROFILE"}
        ).get("Item")
        if user_profile:
            balances = user_profile.get("balances", {})
            current = int(balances.get(leave_type, 0))
            max_balance = DEFAULT_BALANCES.get(leave_type, 0)
            balances[leave_type] = Decimal(str(min(current + days, max_balance)))
            table.update_item(
                Key={"PK": f"USER#{employee_id}", "SK": "PROFILE"},
                UpdateExpression="SET balances = :b",
                ExpressionAttributeValues={":b": balances},
            )

    # SNS notification
    employee_name = leave.get("employeeName", "Employee")
    publish_notification(
        f"Leave Request {status.capitalize()} - {employee_name}",
        f"Leave request for {employee_name} ({leave.get('leaveType')}) "
        f"from {leave.get('startDate')} to {leave.get('endDate')} "
        f"has been {status}.\nComments: {comments or 'None'}",
    )

    return json_response(200, {
        "message": f"Leave request {status} successfully",
        "requestId": request_id,
        "status": status,
        "comments": comments,
    })


# ---------------------------------------------------------------------------
# Employee handlers
# ---------------------------------------------------------------------------

def handle_get_employees(event):
    """GET /employees - list all employees (manager only)."""
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})
    if user["role"] != "manager":
        return json_response(403, {"error": "Only managers can view employee list"})

    response = table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr("entityType").eq("User"),
    )
    employees = []
    for item in response.get("Items", []):
        employees.append({
            "userId": item.get("userId"),
            "name": item.get("name"),
            "email": item.get("email"),
            "role": item.get("role"),
            "department": item.get("department", "General"),
            "balances": item.get("balances", DEFAULT_BALANCES),
        })

    return json_response(200, {"employees": employees})


def handle_get_employee_balance(event, employee_id):
    """GET /employees/{id}/balance - get leave balances."""
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})

    # Employees can only view their own, managers can view anyone
    if user["role"] != "manager" and user["userId"] != employee_id:
        return json_response(403, {"error": "Access denied"})

    response = table.get_item(
        Key={"PK": f"USER#{employee_id}", "SK": "PROFILE"}
    )
    item = response.get("Item")
    if not item:
        return json_response(404, {"error": "Employee not found"})

    return json_response(200, {
        "employeeId": employee_id,
        "name": item.get("name"),
        "balances": item.get("balances", DEFAULT_BALANCES),
    })


# ---------------------------------------------------------------------------
# Dashboard handler
# ---------------------------------------------------------------------------

def handle_dashboard(event):
    """GET /dashboard - role-based dashboard data."""
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})

    today = datetime.utcnow().strftime("%Y-%m-%d")

    if user["role"] == "employee":
        # Get user profile
        profile = table.get_item(
            Key={"PK": f"USER#{user['userId']}", "SK": "PROFILE"}
        ).get("Item", {})

        # Get user's leave requests
        leaves_response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key("PK").eq(f"USER#{user['userId']}")
            & boto3.dynamodb.conditions.Key("SK").begins_with("LEAVE#"),
        )
        leaves = leaves_response.get("Items", [])

        pending = [l for l in leaves if l.get("status") == "pending"]
        upcoming = [
            l for l in leaves
            if l.get("status") in ["approved", "pending"] and l.get("startDate", "") >= today
        ]
        upcoming.sort(key=lambda x: x.get("startDate", ""))

        return json_response(200, {
            "role": "employee",
            "name": profile.get("name", ""),
            "balances": profile.get("balances", DEFAULT_BALANCES),
            "pendingRequests": len(pending),
            "upcomingLeaves": [
                {
                    "requestId": l.get("requestId"),
                    "leaveType": l.get("leaveType"),
                    "startDate": l.get("startDate"),
                    "endDate": l.get("endDate"),
                    "status": l.get("status"),
                    "days": l.get("days"),
                }
                for l in upcoming[:5]
            ],
        })

    else:
        # Manager dashboard
        all_leaves = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr("entityType").eq("LeaveRequest"),
        ).get("Items", [])

        pending_approvals = [l for l in all_leaves if l.get("status") == "pending"]
        on_leave_today = [
            l for l in all_leaves
            if l.get("status") == "approved"
            and l.get("startDate", "") <= today
            and l.get("endDate", "") >= today
        ]

        total_requests = len(all_leaves)
        approved_count = len([l for l in all_leaves if l.get("status") == "approved"])
        rejected_count = len([l for l in all_leaves if l.get("status") == "rejected"])

        return json_response(200, {
            "role": "manager",
            "pendingApprovals": len(pending_approvals),
            "teamOnLeaveToday": [
                {
                    "employeeName": l.get("employeeName"),
                    "leaveType": l.get("leaveType"),
                    "endDate": l.get("endDate"),
                }
                for l in on_leave_today
            ],
            "leaveStats": {
                "total": total_requests,
                "approved": approved_count,
                "rejected": rejected_count,
                "pending": len(pending_approvals),
            },
        })


# ---------------------------------------------------------------------------
# Notification handlers
# ---------------------------------------------------------------------------

def handle_subscribe(event):
    """POST /subscribe - subscribe an email to SNS notifications."""
    body = parse_body(event)
    email = body.get("email", "").strip()

    if not email or not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        return json_response(400, {"error": "Valid email is required"})

    if not SNS_TOPIC_ARN:
        return json_response(500, {"error": "SNS topic not configured"})

    try:
        sns_client.subscribe(
            TopicArn=SNS_TOPIC_ARN,
            Protocol="email",
            Endpoint=email,
        )
        return json_response(200, {
            "message": "Subscription request sent. Please check your email to confirm.",
        })
    except Exception as e:
        return json_response(500, {"error": f"Subscription failed: {str(e)}"})


def handle_get_subscribers(event):
    """GET /subscribers - list SNS subscriptions (public)."""
    if not SNS_TOPIC_ARN:
        return json_response(200, {"subscribers": []})

    try:
        response = sns_client.list_subscriptions_by_topic(TopicArn=SNS_TOPIC_ARN)
        subscribers = [
            {
                "endpoint": sub.get("Endpoint"),
                "protocol": sub.get("Protocol"),
            }
            for sub in response.get("Subscriptions", [])
        ]
        return json_response(200, {"subscribers": subscribers})
    except Exception as e:
        return json_response(500, {"error": f"Failed to list subscribers: {str(e)}"})


# ---------------------------------------------------------------------------
# Main Lambda handler
# ---------------------------------------------------------------------------

def lambda_handler(event, context):
    """Main Lambda entry point - routes requests based on HTTP method and path."""
    http_method = event.get("httpMethod", "GET")
    path = event.get("path", "/")
    path_params = event.get("pathParameters") or {}

    # Handle CORS preflight
    if http_method == "OPTIONS":
        return json_response(200, {"message": "OK"})

    try:
        # Auth routes
        if path == "/auth/register" and http_method == "POST":
            return handle_register(event)
        elif path == "/auth/login" and http_method == "POST":
            return handle_login(event)

        # Leave routes
        elif path == "/leaves" and http_method == "GET":
            return handle_get_leaves(event)
        elif path == "/leaves" and http_method == "POST":
            return handle_create_leave(event)
        elif re.match(r"^/leaves/[^/]+/approve$", path) and http_method == "PUT":
            request_id = path.split("/")[2]
            return handle_approve_leave(event, request_id)
        elif re.match(r"^/leaves/[^/]+$", path) and http_method == "GET":
            request_id = path.split("/")[2]
            return handle_get_leave(event, request_id)
        elif re.match(r"^/leaves/[^/]+$", path) and http_method == "DELETE":
            request_id = path.split("/")[2]
            return handle_delete_leave(event, request_id)

        # Employee routes
        elif path == "/employees" and http_method == "GET":
            return handle_get_employees(event)
        elif re.match(r"^/employees/[^/]+/balance$", path) and http_method == "GET":
            employee_id = path.split("/")[2]
            return handle_get_employee_balance(event, employee_id)

        # Dashboard
        elif path == "/dashboard" and http_method == "GET":
            return handle_dashboard(event)

        # Notifications
        elif path == "/subscribe" and http_method == "POST":
            return handle_subscribe(event)
        elif path == "/subscribers" and http_method == "GET":
            return handle_get_subscribers(event)

        else:
            return json_response(404, {"error": f"Route not found: {http_method} {path}"})

    except Exception as e:
        print(f"Unhandled error: {e}")
        return json_response(500, {"error": "Internal server error"})
