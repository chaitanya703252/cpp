"""
StudySync - Student Study Group Finder & Scheduler
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
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "studysync-prod")
S3_BUCKET = os.environ.get("S3_BUCKET", "studysync-files-prod-chaitanya")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")
REGION = os.environ.get("REGION", "eu-west-1")
JWT_SECRET = os.environ.get("JWT_SECRET", "studysync-secret-2026")

# ---------------------------------------------------------------------------
# AWS clients
# ---------------------------------------------------------------------------
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(DYNAMODB_TABLE)
s3_client = boto3.client("s3", region_name=REGION)
sns_client = boto3.client("sns", region_name=REGION)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
VALID_SUBJECTS = [
    "mathematics", "physics", "chemistry", "biology", "computer_science",
    "english", "history", "economics", "psychology", "engineering",
    "business", "statistics", "data_science", "law", "medicine",
]
MAX_GROUP_MEMBERS = 12

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

def generate_token(user_id, email):
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "userId": user_id,
        "email": email,
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
    university = body.get("university", "").strip()
    subjects = body.get("subjects", [])

    if not username or len(username) < 2:
        return json_response(400, {"error": "Username is required (minimum 2 characters)"})
    if not email or not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        return json_response(400, {"error": "Valid email is required"})
    if not password or len(password) < 8:
        return json_response(400, {"error": "Password must be at least 8 characters"})

    # Validate subjects
    if isinstance(subjects, list):
        subjects = [s.lower().strip() for s in subjects if isinstance(s, str) and s.strip()]
    else:
        subjects = []

    existing = scan_by_entity("user", Attr("email").eq(email))
    if existing:
        return json_response(409, {"error": "Email already registered"})

    user_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    user_item = to_decimal({
        "id": user_id,
        "entityType": "user",
        "username": username,
        "email": email,
        "passwordHash": hash_password(password),
        "university": university,
        "subjects": subjects,
        "createdAt": now,
    })
    table.put_item(Item=user_item)

    token = generate_token(user_id, email)

    return json_response(201, {
        "message": "Registration successful",
        "token": token,
        "user": {
            "userId": user_id,
            "username": username,
            "email": email,
            "university": university,
            "subjects": subjects,
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

    token = generate_token(user["id"], email)

    return json_response(200, {
        "message": "Login successful",
        "token": token,
        "user": {
            "userId": user["id"],
            "username": user.get("username", ""),
            "email": user["email"],
            "university": user.get("university", ""),
            "subjects": user.get("subjects", []),
        },
    })


# ---------------------------------------------------------------------------
# Study Group handlers
# ---------------------------------------------------------------------------

def handle_get_groups(event):
    """Get all study groups, optionally filtered by subject."""
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})

    query_params = event.get("queryStringParameters") or {}
    subject_filter = query_params.get("subject", "").lower().strip()
    search_query = query_params.get("search", "").lower().strip()

    groups = scan_by_entity("study_group")

    if subject_filter:
        groups = [g for g in groups if g.get("subject", "").lower() == subject_filter]

    if search_query:
        groups = [
            g for g in groups
            if search_query in g.get("name", "").lower()
            or search_query in g.get("description", "").lower()
            or search_query in g.get("subject", "").lower()
        ]

    # Enrich with member count
    memberships = scan_by_entity("membership")
    group_member_counts = {}
    for m in memberships:
        gid = m.get("groupId")
        group_member_counts[gid] = group_member_counts.get(gid, 0) + 1

    result = []
    for g in groups:
        result.append({
            "id": g["id"],
            "name": g.get("name"),
            "subject": g.get("subject"),
            "description": g.get("description", ""),
            "maxMembers": g.get("maxMembers", MAX_GROUP_MEMBERS),
            "memberCount": group_member_counts.get(g["id"], 0),
            "createdBy": g.get("createdBy"),
            "creatorName": g.get("creatorName", ""),
            "createdAt": g.get("createdAt"),
        })

    result.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
    return json_response(200, {"groups": result})


def handle_create_group(event):
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})

    body = parse_body(event)
    name = body.get("name", "").strip()
    subject = body.get("subject", "").lower().strip()
    description = body.get("description", "").strip()
    max_members = body.get("maxMembers", MAX_GROUP_MEMBERS)

    if not name or len(name) < 3:
        return json_response(400, {"error": "Group name is required (minimum 3 characters)"})
    if not subject:
        return json_response(400, {"error": "Subject is required"})
    if not description or len(description) < 10:
        return json_response(400, {"error": "Description is required (minimum 10 characters)"})

    try:
        max_members = int(max_members)
        if max_members < 2 or max_members > 20:
            return json_response(400, {"error": "Max members must be between 2 and 20"})
    except (ValueError, TypeError):
        max_members = MAX_GROUP_MEMBERS

    # Get creator name
    user_item = get_item_by_id(user["userId"])
    creator_name = user_item.get("username", "Unknown") if user_item else "Unknown"

    group_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    group_item = to_decimal({
        "id": group_id,
        "entityType": "study_group",
        "name": name,
        "subject": subject,
        "description": description,
        "maxMembers": max_members,
        "createdBy": user["userId"],
        "creatorName": creator_name,
        "createdAt": now,
    })
    table.put_item(Item=group_item)

    # Auto-add creator as organizer
    membership_id = str(uuid.uuid4())
    membership_item = to_decimal({
        "id": membership_id,
        "entityType": "membership",
        "groupId": group_id,
        "userId": user["userId"],
        "username": creator_name,
        "role": "organizer",
        "joinedAt": now,
    })
    table.put_item(Item=membership_item)

    publish_notification(
        f"New Study Group: {name}",
        f"{creator_name} created a new study group '{name}' for {subject}.\n"
        f"Description: {description}\nMax members: {max_members}",
    )

    return json_response(201, {
        "message": "Study group created successfully",
        "group": {
            "id": group_id,
            "name": name,
            "subject": subject,
            "description": description,
            "maxMembers": max_members,
            "memberCount": 1,
            "createdAt": now,
        },
    })


def handle_get_group(event, group_id):
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})

    group = get_item_by_id(group_id)
    if not group or group.get("entityType") != "study_group":
        return json_response(404, {"error": "Study group not found"})

    # Get members
    memberships = scan_by_entity("membership", Attr("groupId").eq(group_id))
    members = [
        {
            "userId": m.get("userId"),
            "username": m.get("username"),
            "role": m.get("role"),
            "joinedAt": m.get("joinedAt"),
        }
        for m in memberships
    ]

    # Get upcoming sessions
    sessions = scan_by_entity("session", Attr("groupId").eq(group_id))
    today = datetime.utcnow().strftime("%Y-%m-%d")
    upcoming = [s for s in sessions if s.get("date", "") >= today]
    upcoming.sort(key=lambda x: (x.get("date", ""), x.get("startTime", "")))

    # Check if current user is a member
    is_member = any(m.get("userId") == user["userId"] for m in memberships)
    user_role = None
    for m in memberships:
        if m.get("userId") == user["userId"]:
            user_role = m.get("role")
            break

    return json_response(200, {
        "group": {
            "id": group["id"],
            "name": group.get("name"),
            "subject": group.get("subject"),
            "description": group.get("description", ""),
            "maxMembers": group.get("maxMembers", MAX_GROUP_MEMBERS),
            "createdBy": group.get("createdBy"),
            "creatorName": group.get("creatorName", ""),
            "createdAt": group.get("createdAt"),
        },
        "members": members,
        "sessions": [
            {
                "id": s["id"],
                "title": s.get("title"),
                "date": s.get("date"),
                "startTime": s.get("startTime"),
                "endTime": s.get("endTime"),
                "location": s.get("location", ""),
                "isOnline": s.get("isOnline", False),
                "notes": s.get("notes", ""),
                "createdBy": s.get("createdBy"),
            }
            for s in upcoming
        ],
        "isMember": is_member,
        "userRole": user_role,
    })


def handle_update_group(event, group_id):
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})

    group = get_item_by_id(group_id)
    if not group or group.get("entityType") != "study_group":
        return json_response(404, {"error": "Study group not found"})

    # Only organizer can update
    memberships = scan_by_entity(
        "membership",
        Attr("groupId").eq(group_id) & Attr("userId").eq(user["userId"]) & Attr("role").eq("organizer")
    )
    if not memberships:
        return json_response(403, {"error": "Only the group organizer can update this group"})

    body = parse_body(event)
    name = body.get("name", "").strip()
    description = body.get("description", "").strip()

    update_parts = []
    attr_values = {}
    attr_names = {}

    if name and len(name) >= 3:
        update_parts.append("#n = :n")
        attr_names["#n"] = "name"
        attr_values[":n"] = name
    if description:
        update_parts.append("description = :d")
        attr_values[":d"] = description

    if not update_parts:
        return json_response(400, {"error": "No valid fields to update"})

    table.update_item(
        Key={"id": group_id},
        UpdateExpression="SET " + ", ".join(update_parts),
        ExpressionAttributeValues=attr_values,
        ExpressionAttributeNames=attr_names if attr_names else None,
    ) if attr_names else table.update_item(
        Key={"id": group_id},
        UpdateExpression="SET " + ", ".join(update_parts),
        ExpressionAttributeValues=attr_values,
    )

    return json_response(200, {"message": "Group updated successfully"})


def handle_delete_group(event, group_id):
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})

    group = get_item_by_id(group_id)
    if not group or group.get("entityType") != "study_group":
        return json_response(404, {"error": "Study group not found"})

    if group.get("createdBy") != user["userId"]:
        return json_response(403, {"error": "Only the creator can delete this group"})

    # Delete all memberships
    memberships = scan_by_entity("membership", Attr("groupId").eq(group_id))
    for m in memberships:
        table.delete_item(Key={"id": m["id"]})

    # Delete all sessions
    sessions = scan_by_entity("session", Attr("groupId").eq(group_id))
    for s in sessions:
        table.delete_item(Key={"id": s["id"]})

    # Delete the group
    table.delete_item(Key={"id": group_id})

    return json_response(200, {"message": "Study group deleted successfully"})


# ---------------------------------------------------------------------------
# Membership handlers
# ---------------------------------------------------------------------------

def handle_join_group(event, group_id):
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})

    group = get_item_by_id(group_id)
    if not group or group.get("entityType") != "study_group":
        return json_response(404, {"error": "Study group not found"})

    # Check if already a member
    existing = scan_by_entity(
        "membership",
        Attr("groupId").eq(group_id) & Attr("userId").eq(user["userId"])
    )
    if existing:
        return json_response(409, {"error": "You are already a member of this group"})

    # Check member limit
    all_members = scan_by_entity("membership", Attr("groupId").eq(group_id))
    max_members = int(group.get("maxMembers", MAX_GROUP_MEMBERS))
    if len(all_members) >= max_members:
        return json_response(400, {"error": "This group has reached its maximum member limit"})

    # Get username
    user_item = get_item_by_id(user["userId"])
    username = user_item.get("username", "Unknown") if user_item else "Unknown"

    membership_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    membership_item = to_decimal({
        "id": membership_id,
        "entityType": "membership",
        "groupId": group_id,
        "userId": user["userId"],
        "username": username,
        "role": "member",
        "joinedAt": now,
    })
    table.put_item(Item=membership_item)

    publish_notification(
        f"New Member: {group.get('name', 'Study Group')}",
        f"{username} joined the study group '{group.get('name', '')}'.",
    )

    return json_response(200, {"message": "Successfully joined the study group"})


def handle_leave_group(event, group_id):
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})

    memberships = scan_by_entity(
        "membership",
        Attr("groupId").eq(group_id) & Attr("userId").eq(user["userId"])
    )
    if not memberships:
        return json_response(404, {"error": "You are not a member of this group"})

    membership = memberships[0]
    if membership.get("role") == "organizer":
        return json_response(400, {"error": "Organizers cannot leave their own group. Delete the group instead."})

    table.delete_item(Key={"id": membership["id"]})

    return json_response(200, {"message": "Successfully left the study group"})


# ---------------------------------------------------------------------------
# Session handlers
# ---------------------------------------------------------------------------

def handle_get_sessions(event, group_id):
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})

    sessions = scan_by_entity("session", Attr("groupId").eq(group_id))
    sessions.sort(key=lambda x: (x.get("date", ""), x.get("startTime", "")))

    result = [
        {
            "id": s["id"],
            "groupId": s.get("groupId"),
            "title": s.get("title"),
            "date": s.get("date"),
            "startTime": s.get("startTime"),
            "endTime": s.get("endTime"),
            "location": s.get("location", ""),
            "isOnline": s.get("isOnline", False),
            "notes": s.get("notes", ""),
            "createdBy": s.get("createdBy"),
            "creatorName": s.get("creatorName", ""),
            "createdAt": s.get("createdAt"),
        }
        for s in sessions
    ]

    return json_response(200, {"sessions": result})


def handle_create_session(event, group_id):
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})

    # Verify membership
    memberships = scan_by_entity(
        "membership",
        Attr("groupId").eq(group_id) & Attr("userId").eq(user["userId"])
    )
    if not memberships:
        return json_response(403, {"error": "You must be a member of this group to schedule sessions"})

    body = parse_body(event)
    title = body.get("title", "").strip()
    date = body.get("date", "").strip()
    start_time = body.get("startTime", "").strip()
    end_time = body.get("endTime", "").strip()
    location = body.get("location", "").strip()
    is_online = body.get("isOnline", False)
    notes = body.get("notes", "").strip()

    if not title or len(title) < 3:
        return json_response(400, {"error": "Session title is required (minimum 3 characters)"})
    if not date:
        return json_response(400, {"error": "Date is required"})
    if not start_time or not end_time:
        return json_response(400, {"error": "Start time and end time are required"})

    # Validate date format
    try:
        session_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return json_response(400, {"error": "Invalid date format. Use YYYY-MM-DD"})

    # Validate time format
    try:
        st = datetime.strptime(start_time, "%H:%M")
        et = datetime.strptime(end_time, "%H:%M")
    except ValueError:
        return json_response(400, {"error": "Invalid time format. Use HH:MM"})

    if st >= et:
        return json_response(400, {"error": "End time must be after start time"})

    # Check for time conflicts within the same group on the same date
    existing_sessions = scan_by_entity(
        "session",
        Attr("groupId").eq(group_id) & Attr("date").eq(date)
    )
    for es in existing_sessions:
        es_start = es.get("startTime", "")
        es_end = es.get("endTime", "")
        if start_time < es_end and end_time > es_start:
            return json_response(409, {
                "error": f"Time conflict with existing session '{es.get('title', '')}' ({es_start}-{es_end})"
            })

    user_item = get_item_by_id(user["userId"])
    creator_name = user_item.get("username", "Unknown") if user_item else "Unknown"

    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    session_item = to_decimal({
        "id": session_id,
        "entityType": "session",
        "groupId": group_id,
        "title": title,
        "date": date,
        "startTime": start_time,
        "endTime": end_time,
        "location": location if not is_online else "Online",
        "isOnline": is_online,
        "notes": notes,
        "createdBy": user["userId"],
        "creatorName": creator_name,
        "createdAt": now,
    })
    table.put_item(Item=session_item)

    # Get group name for notification
    group = get_item_by_id(group_id)
    group_name = group.get("name", "Study Group") if group else "Study Group"

    publish_notification(
        f"New Session: {group_name}",
        f"{creator_name} scheduled a new session '{title}' for {group_name}.\n"
        f"Date: {date} | Time: {start_time} - {end_time}\n"
        f"Location: {location if not is_online else 'Online'}",
    )

    return json_response(201, {
        "message": "Study session scheduled successfully",
        "session": {
            "id": session_id,
            "title": title,
            "date": date,
            "startTime": start_time,
            "endTime": end_time,
            "location": location if not is_online else "Online",
            "isOnline": is_online,
            "notes": notes,
            "createdAt": now,
        },
    })


def handle_update_session(event, group_id, session_id):
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})

    session = get_item_by_id(session_id)
    if not session or session.get("entityType") != "session" or session.get("groupId") != group_id:
        return json_response(404, {"error": "Session not found"})

    # Only the session creator or group organizer can update
    is_creator = session.get("createdBy") == user["userId"]
    is_organizer = bool(scan_by_entity(
        "membership",
        Attr("groupId").eq(group_id) & Attr("userId").eq(user["userId"]) & Attr("role").eq("organizer")
    ))

    if not is_creator and not is_organizer:
        return json_response(403, {"error": "Only the session creator or group organizer can update sessions"})

    body = parse_body(event)
    update_parts = []
    attr_values = {}

    if body.get("title", "").strip():
        update_parts.append("title = :t")
        attr_values[":t"] = body["title"].strip()
    if body.get("date", "").strip():
        update_parts.append("#d = :d")
        attr_values[":d"] = body["date"].strip()
    if body.get("startTime", "").strip():
        update_parts.append("startTime = :st")
        attr_values[":st"] = body["startTime"].strip()
    if body.get("endTime", "").strip():
        update_parts.append("endTime = :et")
        attr_values[":et"] = body["endTime"].strip()
    if "location" in body:
        update_parts.append("#l = :l")
        attr_values[":l"] = body["location"].strip()
    if "notes" in body:
        update_parts.append("notes = :n")
        attr_values[":n"] = body["notes"].strip()
    if "isOnline" in body:
        update_parts.append("isOnline = :io")
        attr_values[":io"] = bool(body["isOnline"])

    if not update_parts:
        return json_response(400, {"error": "No valid fields to update"})

    attr_names = {}
    if "#d" in str(update_parts):
        attr_names["#d"] = "date"
    if "#l" in str(update_parts):
        attr_names["#l"] = "location"

    update_kwargs = {
        "Key": {"id": session_id},
        "UpdateExpression": "SET " + ", ".join(update_parts),
        "ExpressionAttributeValues": attr_values,
    }
    if attr_names:
        update_kwargs["ExpressionAttributeNames"] = attr_names

    table.update_item(**update_kwargs)

    return json_response(200, {"message": "Session updated successfully"})


def handle_delete_session(event, group_id, session_id):
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})

    session = get_item_by_id(session_id)
    if not session or session.get("entityType") != "session" or session.get("groupId") != group_id:
        return json_response(404, {"error": "Session not found"})

    is_creator = session.get("createdBy") == user["userId"]
    is_organizer = bool(scan_by_entity(
        "membership",
        Attr("groupId").eq(group_id) & Attr("userId").eq(user["userId"]) & Attr("role").eq("organizer")
    ))

    if not is_creator and not is_organizer:
        return json_response(403, {"error": "Only the session creator or group organizer can delete sessions"})

    table.delete_item(Key={"id": session_id})

    return json_response(200, {"message": "Session deleted successfully"})


# ---------------------------------------------------------------------------
# My Groups handler
# ---------------------------------------------------------------------------

def handle_my_groups(event):
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})

    memberships = scan_by_entity("membership", Attr("userId").eq(user["userId"]))
    group_ids = [m.get("groupId") for m in memberships]

    groups = []
    all_memberships = scan_by_entity("membership")

    for gid in group_ids:
        group = get_item_by_id(gid)
        if group and group.get("entityType") == "study_group":
            member_count = len([m for m in all_memberships if m.get("groupId") == gid])
            user_membership = next((m for m in memberships if m.get("groupId") == gid), {})
            groups.append({
                "id": group["id"],
                "name": group.get("name"),
                "subject": group.get("subject"),
                "description": group.get("description", ""),
                "maxMembers": group.get("maxMembers", MAX_GROUP_MEMBERS),
                "memberCount": member_count,
                "myRole": user_membership.get("role", "member"),
                "createdAt": group.get("createdAt"),
            })

    groups.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
    return json_response(200, {"groups": groups})


# ---------------------------------------------------------------------------
# Dashboard handler
# ---------------------------------------------------------------------------

def handle_dashboard(event):
    user = get_current_user(event)
    if not user:
        return json_response(401, {"error": "Authentication required"})

    today = datetime.utcnow().strftime("%Y-%m-%d")

    # My memberships
    my_memberships = scan_by_entity("membership", Attr("userId").eq(user["userId"]))
    my_group_ids = [m.get("groupId") for m in my_memberships]

    # My groups count
    total_groups = len(my_group_ids)
    organized = len([m for m in my_memberships if m.get("role") == "organizer"])

    # Upcoming sessions in my groups
    all_sessions = scan_by_entity("session")
    upcoming_sessions = [
        s for s in all_sessions
        if s.get("groupId") in my_group_ids and s.get("date", "") >= today
    ]
    upcoming_sessions.sort(key=lambda x: (x.get("date", ""), x.get("startTime", "")))

    # Enrich sessions with group names
    group_names = {}
    for gid in my_group_ids:
        g = get_item_by_id(gid)
        if g:
            group_names[gid] = g.get("name", "Unknown")

    upcoming_list = [
        {
            "id": s["id"],
            "title": s.get("title"),
            "date": s.get("date"),
            "startTime": s.get("startTime"),
            "endTime": s.get("endTime"),
            "location": s.get("location", ""),
            "isOnline": s.get("isOnline", False),
            "groupName": group_names.get(s.get("groupId"), ""),
            "groupId": s.get("groupId"),
        }
        for s in upcoming_sessions[:8]
    ]

    # Sessions today
    today_sessions = [s for s in upcoming_sessions if s.get("date") == today]

    # Popular subjects
    all_groups = scan_by_entity("study_group")
    subject_counts = {}
    for g in all_groups:
        subj = g.get("subject", "other")
        subject_counts[subj] = subject_counts.get(subj, 0) + 1
    popular_subjects = sorted(subject_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return json_response(200, {
        "totalGroups": total_groups,
        "organizedGroups": organized,
        "todaySessions": len(today_sessions),
        "totalUpcomingSessions": len(upcoming_sessions),
        "upcomingSessions": upcoming_list,
        "popularSubjects": [{"subject": s, "count": c} for s, c in popular_subjects],
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

    # CORS preflight
    if http_method == "OPTIONS":
        return json_response(200, {"message": "OK"})

    try:
        # ---- PUBLIC routes ----
        if path == "/subscribe" and http_method == "POST":
            return handle_subscribe(event)
        if path == "/subscribers" and http_method == "GET":
            return handle_get_subscribers(event)
        if path == "/auth/register" and http_method == "POST":
            return handle_register(event)
        if path == "/auth/login" and http_method == "POST":
            return handle_login(event)

        # ---- PROTECTED routes ----

        # Dashboard
        if path == "/dashboard" and http_method == "GET":
            return handle_dashboard(event)

        # My groups
        if path == "/my-groups" and http_method == "GET":
            return handle_my_groups(event)

        # Groups
        if path == "/groups" and http_method == "GET":
            return handle_get_groups(event)
        if path == "/groups" and http_method == "POST":
            return handle_create_group(event)

        # Group detail + join/leave
        if re.match(r"^/groups/[^/]+/join$", path) and http_method == "POST":
            group_id = path.split("/")[2]
            return handle_join_group(event, group_id)
        if re.match(r"^/groups/[^/]+/leave$", path) and http_method == "DELETE":
            group_id = path.split("/")[2]
            return handle_leave_group(event, group_id)

        # Sessions
        if re.match(r"^/groups/[^/]+/sessions$", path) and http_method == "GET":
            group_id = path.split("/")[2]
            return handle_get_sessions(event, group_id)
        if re.match(r"^/groups/[^/]+/sessions$", path) and http_method == "POST":
            group_id = path.split("/")[2]
            return handle_create_session(event, group_id)
        if re.match(r"^/groups/[^/]+/sessions/[^/]+$", path) and http_method == "PUT":
            group_id = path.split("/")[2]
            session_id = path.split("/")[4]
            return handle_update_session(event, group_id, session_id)
        if re.match(r"^/groups/[^/]+/sessions/[^/]+$", path) and http_method == "DELETE":
            group_id = path.split("/")[2]
            session_id = path.split("/")[4]
            return handle_delete_session(event, group_id, session_id)

        # Group CRUD (after more specific routes)
        if re.match(r"^/groups/[^/]+$", path) and http_method == "GET":
            group_id = path.split("/")[2]
            return handle_get_group(event, group_id)
        if re.match(r"^/groups/[^/]+$", path) and http_method == "PUT":
            group_id = path.split("/")[2]
            return handle_update_group(event, group_id)
        if re.match(r"^/groups/[^/]+$", path) and http_method == "DELETE":
            group_id = path.split("/")[2]
            return handle_delete_group(event, group_id)

        return json_response(404, {"error": f"Route not found: {http_method} {path}"})

    except Exception as e:
        print(f"Unhandled error: {e}")
        return json_response(500, {"error": "Internal server error"})
