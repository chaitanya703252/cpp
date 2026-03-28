"""
LeaveFlow - Employee Leave Request System
AWS Lambda Function Handler

Student: Kondragunta Lakshmi Chaitanya (X25171216)
"""

import json
import os
import uuid
import hashlib
import time
import re
from datetime import datetime, timedelta
from decimal import Decimal

import hmac
import base64

import boto3
from boto3.dynamodb.conditions import Attr

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
# Defaults
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
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": json.dumps(body, cls=DecimalEncoder, default=str),
    }


def parse_body(event):
    body = event.get("body", "{}")
    if isinstance(body, str):
        try:
            return json.loads(body)
        except (json.JSONDecodeError, TypeError):
            return {}
    return body or {}


def to_decimal(obj):
    if isinstance(obj, dict):
        return {k: to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_decimal(i) for i in obj]
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, int) and not isinstance(obj, bool):
        return Decimal(str(obj))
    return obj


def hash_password(password, salt=None):
    if salt is None:
        salt = uuid.uuid4().hex
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return f"{salt}:{hashed.hex()}"


def verify_password(password, stored_hash):
    salt, _ = stored_hash.split(":")
    return hash_password(password, salt) == stored_hash


def _b64_encode(data):
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")

def _b64_decode(s):
    s += "=" * (4 - len(s) % 4)
    return json.loads(base64.urlsafe_b64decode(s))

def generate_token(user_id, email, role):
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "userId": user_id,
        "email": email,
        "role": role,
        "exp": int(time.time()) + 86400,
        "iat": int(time.time()),
    }
    segments = _b64_encode(header) + "." + _b64_encode(payload)
    signature = hmac.new(JWT_SECRET.encode(), segments.encode(), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return segments + "." + sig_b64


def decode_token(token):
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        segments = parts[0] + "." + parts[1]
        expected_sig = hmac.new(JWT_SECRET.encode(), segments.encode(), hashlib.sha256).digest()
        expected_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")
        if not hmac.compare_digest(expected_b64, parts[2]):
            return None
        payload = _b64_decode(parts[1])
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


def get_current_user(event):
    headers = event.get("headers", {}) or {}
    auth = headers.get("Authorization") or headers.get("authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        return decode_token(token)
    return None


def calculate_business_days(start_date_str, end_date_str):
    start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    days = 0
    current = start
    while current <= end:
        if current.weekday() < 5:
            days += 1
        current += timedelta(days=1)
    return days


def dates_overlap(s1, e1, s2, e2):
    return s1 <= e2 and e1 >= s2


def publish_notification(subject, message):
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
# DynamoDB scan helpers (single-table, PK = id)
# ---------------------------------------------------------------------------

def scan_by_entity(entity_type, extra_filter=None):
    """Scan for items with a given entityType, optionally with extra filter."""
    filter_exp = Attr("entityType").eq(entity_type)
    if extra_filter is not None:
        filter_exp = filter_exp & extra_filter
    items = []
    params = {"FilterExpression": filter_exp}
    while True:
        resp = table.scan(**params)
        items.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp:
            break
        params["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    return items


def get_item_by_id(item_id):
    resp = table.get_item(Key={"id": item_id})
    return resp.get("Item")


# ---------------------------------------------------------------------------
# Auth handlers
# ---------------------------------------------------------------------------

def handle_register(event):
    body = parse_body(event)
    username = body.get("username", "").strip()
    email = body.get("email", "").strip().lower()
    password = body.get("password", "")
    role = body.get("role", "employee")

    if not username or len(username) < 2:
        return json_response(400, {"error": "Username is required (minimum 2 characters)"})
    if not email or not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        return json_response(400, {"error": "Valid email is required"})
    if not password or len(password) < 8:
        return json_response(400, {"error": "Password must be at least 8 characters"})
    if role not in ["employee", "manager"]:
        return json_response(400, {"error": "Role must be 'employee' or 'manager'"})

    # Check if email already exists (scan for users with this email)
    existing = scan_by_entity("user", Attr("email").eq(email))
    if existing:
        return json_response(409, {"error": "Email already registered"})

    user_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    # Create user item
    user_item = to_decimal({
        "id": user_id,
        "entityType": "user",
        "username": username,
        "email": email,
        "passwordHash": hash_password(password),
        "role": role,
        "createdAt": now,
    })
    table.put_item(Item=user_item)

    # Create leave_balance item
    balance_id = str(uuid.uuid4())
    balance_item = to_decimal({
        "id": balance_id,
        "entityType": "leave_balance",
        "userId": user_id,
        "annual": 20,
        "sick": 10,
        "unpaid": 30,
        "createdAt": now,
    })
    table.put_item(Item=balance_item)

    token = generate_token(user_id, email, role)

    return json_response(201, {
        "message": "Registration successful",
        "token": token,
        "user": {
            "userId": user_id,
            "username": username,
            "email": email,
            "role": role,
        },
    })


def handle_login(event):
    body = parse_body(event)
    email = body.get("email", "").strip().lower()
    password = body.get("password", "")

    if not email or not password:
        return json_response(400, {"error": "Email and password are required"})

    users = scan_by_entity("user", Attr("email").eq(email))
    if not users:
        return json_response(401, {"error": "Invalid email or password"})

    user = users[0]
    if not verify_password(password, user["passwordHash"]):
        return json_response(401, {"error": "Invalid email or password"})

    token = generate_token(user["id"], email, user["role"])

    return json_response(200, {
        "message": "Login successful",
        "token": token,
        "user": {
            "userId": user["id"],
            "username": user.get("username", ""),
            "email": user["email"],
            "role": user["role"],
        },
    })


# ---------------------------------------------------------------------------
# Leave Request handlers
# ---------------------------------------------------------------------------

def _get_balance_for_user(user_id):
    """Return the leave_balance item for a user."""
    items = scan_by_entity("leave_balance", Attr("userId").eq(user_id))
    return items[0] if items else None


def _get_user_item(user_id):
    """Return the user item by id."""
    item = get_item_by_id(user_id)
    if item and item.get("entityType") == "user":
        return item
    return None


def handle_get_leaves(event):
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})

    if user["role"] == "manager":
        items = scan_by_entity("leave_request")
    else:
        items = scan_by_entity("leave_request", Attr("userId").eq(user["userId"]))

    leaves = []
    for item in items:
        leaves.append({
            "id": item.get("id"),
            "userId": item.get("userId"),
            "employeeName": item.get("employeeName", ""),
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
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})

    body = parse_body(event)
    leave_type = body.get("leaveType", "")
    start_date = body.get("startDate", "")
    end_date = body.get("endDate", "")
    reason = body.get("reason", "")

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

    # Get user profile for name
    user_item = _get_user_item(user["userId"])
    if not user_item:
        return json_response(404, {"error": "User profile not found"})

    # Get balance
    balance = _get_balance_for_user(user["userId"])
    if not balance:
        return json_response(404, {"error": "Leave balance not found"})

    current_balance = int(balance.get(leave_type, 0))
    if current_balance < days:
        return json_response(400, {
            "error": f"Insufficient {leave_type} leave balance. Available: {current_balance}, Requested: {days}"
        })

    # Overlap detection
    existing = scan_by_entity(
        "leave_request",
        Attr("userId").eq(user["userId"]) & Attr("status").is_in(["pending", "approved"])
    )
    for ex in existing:
        ex_start = datetime.strptime(ex["startDate"], "%Y-%m-%d").date()
        ex_end = datetime.strptime(ex["endDate"], "%Y-%m-%d").date()
        if dates_overlap(start, end, ex_start, ex_end):
            return json_response(409, {"error": "Leave request overlaps with an existing pending/approved request"})

    # Deduct balance
    new_balance = current_balance - days
    table.update_item(
        Key={"id": balance["id"]},
        UpdateExpression="SET #lt = :val",
        ExpressionAttributeNames={"#lt": leave_type},
        ExpressionAttributeValues={":val": Decimal(str(new_balance))},
    )

    # Create leave request
    request_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    leave_item = to_decimal({
        "id": request_id,
        "entityType": "leave_request",
        "userId": user["userId"],
        "employeeName": user_item.get("username", "Unknown"),
        "leaveType": leave_type,
        "startDate": start_date,
        "endDate": end_date,
        "reason": reason,
        "status": "pending",
        "days": days,
        "comments": "",
        "createdAt": now,
    })
    table.put_item(Item=leave_item)

    # SNS notification
    publish_notification(
        f"New Leave Request - {user_item.get('username', 'Employee')}",
        f"{user_item.get('username', 'Employee')} submitted a {leave_type} leave request "
        f"from {start_date} to {end_date} ({days} days).\nReason: {reason}",
    )

    return json_response(201, {
        "message": "Leave request submitted successfully",
        "request": {
            "id": request_id,
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
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})

    item = get_item_by_id(request_id)
    if not item or item.get("entityType") != "leave_request":
        return json_response(404, {"error": "Leave request not found"})

    # Employees can only see their own
    if user["role"] != "manager" and item.get("userId") != user["userId"]:
        return json_response(403, {"error": "Access denied"})

    return json_response(200, {
        "request": {
            "id": item.get("id"),
            "userId": item.get("userId"),
            "employeeName": item.get("employeeName", ""),
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
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})

    item = get_item_by_id(request_id)
    if not item or item.get("entityType") != "leave_request":
        return json_response(404, {"error": "Leave request not found"})

    if item.get("userId") != user["userId"]:
        return json_response(403, {"error": "Access denied"})

    if item.get("status") != "pending":
        return json_response(400, {"error": "Only pending requests can be cancelled"})

    # Restore balance
    leave_type = item["leaveType"]
    days = int(item.get("days", 0))

    balance = _get_balance_for_user(user["userId"])
    if balance:
        current = int(balance.get(leave_type, 0))
        restored = min(current + days, DEFAULT_BALANCES.get(leave_type, 0))
        table.update_item(
            Key={"id": balance["id"]},
            UpdateExpression="SET #lt = :val",
            ExpressionAttributeNames={"#lt": leave_type},
            ExpressionAttributeValues={":val": Decimal(str(restored))},
        )

    # Delete the leave request
    table.delete_item(Key={"id": request_id})

    return json_response(200, {"message": "Leave request cancelled successfully"})


# ---------------------------------------------------------------------------
# Approval handlers
# ---------------------------------------------------------------------------

def handle_approve_leave(event, request_id):
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

    item = get_item_by_id(request_id)
    if not item or item.get("entityType") != "leave_request":
        return json_response(404, {"error": "Leave request not found"})

    if item.get("status") != "pending":
        return json_response(400, {"error": "Only pending requests can be approved/rejected"})

    # Update status
    table.update_item(
        Key={"id": request_id},
        UpdateExpression="SET #s = :s, comments = :c",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": status, ":c": comments},
    )

    # If rejected, restore balance
    if status == "rejected":
        leave_type = item["leaveType"]
        days = int(item.get("days", 0))
        employee_id = item["userId"]

        balance = _get_balance_for_user(employee_id)
        if balance:
            current = int(balance.get(leave_type, 0))
            restored = min(current + days, DEFAULT_BALANCES.get(leave_type, 0))
            table.update_item(
                Key={"id": balance["id"]},
                UpdateExpression="SET #lt = :val",
                ExpressionAttributeNames={"#lt": leave_type},
                ExpressionAttributeValues={":val": Decimal(str(restored))},
            )

    # SNS notification
    employee_name = item.get("employeeName", "Employee")
    publish_notification(
        f"Leave Request {status.capitalize()} - {employee_name}",
        f"Leave request for {employee_name} ({item.get('leaveType')}) "
        f"from {item.get('startDate')} to {item.get('endDate')} "
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
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})
    if user["role"] != "manager":
        return json_response(403, {"error": "Only managers can view employee list"})

    items = scan_by_entity("user")
    employees = []
    for item in items:
        employees.append({
            "userId": item.get("id"),
            "username": item.get("username"),
            "email": item.get("email"),
            "role": item.get("role"),
        })

    return json_response(200, {"employees": employees})


def handle_get_employee_balance(event, employee_id):
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})

    # Employees can only view their own, managers can view anyone
    if user["role"] != "manager" and user["userId"] != employee_id:
        return json_response(403, {"error": "Access denied"})

    user_item = _get_user_item(employee_id)
    if not user_item:
        return json_response(404, {"error": "Employee not found"})

    balance = _get_balance_for_user(employee_id)
    if not balance:
        return json_response(404, {"error": "Leave balance not found"})

    return json_response(200, {
        "employeeId": employee_id,
        "username": user_item.get("username", ""),
        "balances": {
            "annual": balance.get("annual", 20),
            "sick": balance.get("sick", 10),
            "unpaid": balance.get("unpaid", 30),
        },
    })


# ---------------------------------------------------------------------------
# Dashboard handler
# ---------------------------------------------------------------------------

def handle_dashboard(event):
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})

    today = datetime.utcnow().strftime("%Y-%m-%d")

    if user["role"] == "employee":
        # Get balance
        balance = _get_balance_for_user(user["userId"])
        balances = {
            "annual": int(balance.get("annual", 20)) if balance else 20,
            "sick": int(balance.get("sick", 10)) if balance else 10,
            "unpaid": int(balance.get("unpaid", 30)) if balance else 30,
        }

        # Get leave requests
        leaves = scan_by_entity("leave_request", Attr("userId").eq(user["userId"]))

        pending_count = len([l for l in leaves if l.get("status") == "pending"])
        approved_count = len([l for l in leaves if l.get("status") == "approved"])

        upcoming = [
            l for l in leaves
            if l.get("status") in ["approved", "pending"] and l.get("startDate", "") >= today
        ]
        upcoming.sort(key=lambda x: x.get("startDate", ""))

        return json_response(200, {
            "role": "employee",
            "balances": balances,
            "pendingCount": pending_count,
            "approvedCount": approved_count,
            "upcomingLeaves": [
                {
                    "id": l.get("id"),
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
        all_leaves = scan_by_entity("leave_request")

        pending_approvals = [l for l in all_leaves if l.get("status") == "pending"]
        on_leave_today = [
            l for l in all_leaves
            if l.get("status") == "approved"
            and l.get("startDate", "") <= today
            and l.get("endDate", "") >= today
        ]

        total = len(all_leaves)
        approved = len([l for l in all_leaves if l.get("status") == "approved"])
        rejected = len([l for l in all_leaves if l.get("status") == "rejected"])

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
                "total": total,
                "approved": approved,
                "rejected": rejected,
                "pending": len(pending_approvals),
            },
        })


# ---------------------------------------------------------------------------
# Notification handlers (PUBLIC)
# ---------------------------------------------------------------------------

def handle_subscribe(event):
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
    http_method = event.get("httpMethod", "GET")
    path = event.get("path", "/")

    # CORS preflight — first
    if http_method == "OPTIONS":
        return json_response(200, {"message": "OK"})

    try:
        # ---- PUBLIC routes (before auth check) ----
        if path == "/subscribe" and http_method == "POST":
            return handle_subscribe(event)
        if path == "/subscribers" and http_method == "GET":
            return handle_get_subscribers(event)
        if path == "/auth/register" and http_method == "POST":
            return handle_register(event)
        if path == "/auth/login" and http_method == "POST":
            return handle_login(event)

        # ---- PROTECTED routes (auth required) ----

        # Leave routes
        if path == "/leaves" and http_method == "GET":
            return handle_get_leaves(event)
        if path == "/leaves" and http_method == "POST":
            return handle_create_leave(event)
        if re.match(r"^/leaves/[^/]+/approve$", path) and http_method == "PUT":
            request_id = path.split("/")[2]
            return handle_approve_leave(event, request_id)
        if re.match(r"^/leaves/[^/]+$", path) and http_method == "GET":
            request_id = path.split("/")[2]
            return handle_get_leave(event, request_id)
        if re.match(r"^/leaves/[^/]+$", path) and http_method == "DELETE":
            request_id = path.split("/")[2]
            return handle_delete_leave(event, request_id)

        # Employee routes
        if path == "/employees" and http_method == "GET":
            return handle_get_employees(event)
        if re.match(r"^/employees/[^/]+/balance$", path) and http_method == "GET":
            employee_id = path.split("/")[2]
            return handle_get_employee_balance(event, employee_id)

        # Dashboard
        if path == "/dashboard" and http_method == "GET":
            return handle_dashboard(event)

        return json_response(404, {"error": f"Route not found: {http_method} {path}"})

    except Exception as e:
        print(f"Unhandled error: {e}")
        return json_response(500, {"error": "Internal server error"})
