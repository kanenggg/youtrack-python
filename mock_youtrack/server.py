"""
Mock YouTrack Server
====================
จำลอง endpoint ของ YouTrack REST API (/api/issues) สำหรับทดสอบ
โดยไม่ต้องมี YouTrack instance จริง

รัน:
    uvicorn mock_youtrack.server:app --reload --port 9100

ทดสอบผ่าน Postman ได้ที่:
    GET http://localhost:9100/api/issues
    Header: Authorization: Bearer perm:demo-token
"""

import time
from typing import Any

from fastapi import Body, FastAPI, Header, HTTPException, Query

app = FastAPI(title="Mock YouTrack API")

VALID_TOKEN = "perm:demo-token"

MOCK_USERS = [
    {"id": "user-1", "login": "somchai", "email": "somchai@example.com", "fullName": "สมชาย ใจดี"},
    {"id": "user-2", "login": "somsri", "email": "somsri@example.com", "fullName": "สมศรี รักเรียน"},
]

_next_issue_num = len(range(3)) + 1  # เริ่มต่อจาก DEMO-3


def _epoch_ms(offset_days: int = 0) -> int:
    return int((time.time() - offset_days * 86400) * 1000)


# ข้อมูลจำลอง — โครงสร้างเลียนแบบ response จริงของ YouTrack
MOCK_ISSUES = [
    {
        "id": "DEMO-1",
        "$type": "Issue",
        "summary": "Login page แสดง error เมื่อ password มีอักขระพิเศษ",
        "description": "ทดสอบ login ด้วย password ที่มี # หรือ & แล้วระบบ reject ทั้งที่ควรผ่าน",
        "created": _epoch_ms(offset_days=5),
        "updated": _epoch_ms(offset_days=1),
        "project": {"shortName": "DEMO", "name": "Demo Project"},
        "customFields": [
            {"name": "State", "value": {"name": "Open"}},
            {"name": "Priority", "value": {"name": "High"}},
        ],
    },
    {
        "id": "DEMO-2",
        "$type": "Issue",
        "summary": "เพิ่มปุ่ม Export CSV ในหน้า Dashboard",
        "description": "ทีม analytics ขอ feature export ข้อมูลตารางเป็น CSV",
        "created": _epoch_ms(offset_days=10),
        "updated": _epoch_ms(offset_days=2),
        "project": {"shortName": "DEMO", "name": "Demo Project"},
        "customFields": [
            {"name": "State", "value": {"name": "In Progress"}},
            {"name": "Priority", "value": {"name": "Normal"}},
        ],
    },
    {
        "id": "DEMO-3",
        "$type": "Issue",
        "summary": "API /users ตอบช้าเกิน 3 วินาทีตอน load สูง",
        "description": "พบว่า response time พุ่งสูงตอน concurrent request เกิน 100",
        "created": _epoch_ms(offset_days=15),
        "updated": _epoch_ms(offset_days=15),
        "project": {"shortName": "DEMO", "name": "Demo Project"},
        "customFields": [
            {"name": "State", "value": {"name": "Fixed"}},
            {"name": "Priority", "value": {"name": "Critical"}},
        ],
    },
]


@app.get("/api/issues")
def get_issues(
    fields: str = Query(default=""),
    query: str = Query(default=""),
    top: int | None = Query(default=None, alias="$top"),
    authorization: str | None = Header(default=None),
):
    # จำลอง auth check เหมือน YouTrack จริง
    if authorization != f"Bearer {VALID_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized. Check your token.")

    results = MOCK_ISSUES
    if top:
        results = results[:top]

    return results


@app.get("/api/issues/{issue_id}")
def get_issue(issue_id: str, fields: str = Query(default=""), authorization: str | None = Header(default=None)):
    if authorization != f"Bearer {VALID_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized. Check your token.")

    for issue in MOCK_ISSUES:
        if issue["id"] == issue_id:
            return issue

    raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found")


@app.post("/api/issues")
def create_issue(
    body: dict[str, Any] = Body(...),
    fields: str = Query(default=""),
    authorization: str | None = Header(default=None),
):
    if authorization != f"Bearer {VALID_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized. Check your token.")

    global _next_issue_num
    _next_issue_num += 1
    new_issue = {
        "id": f"DEMO-{_next_issue_num}",
        "$type": "Issue",
        "summary": body.get("summary", ""),
        "description": body.get("description", ""),
        "created": _epoch_ms(),
        "updated": _epoch_ms(),
        "project": {"shortName": "DEMO", "name": "Demo Project"},
        "customFields": [{"name": "State", "value": {"name": "Open"}}],
    }
    MOCK_ISSUES.append(new_issue)
    return new_issue


@app.get("/api/admin/users")
def list_users(query: str = Query(default=""), fields: str = Query(default=""), authorization: str | None = Header(default=None)):
    if authorization != f"Bearer {VALID_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized. Check your token.")

    matched = [u for u in MOCK_USERS if query.lower() in u["email"].lower()]
    return matched


@app.post("/api/admin/users/{user_id}")
def update_user(
    user_id: str,
    body: dict[str, Any] = Body(...),
    fields: str = Query(default=""),
    authorization: str | None = Header(default=None),
):
    if authorization != f"Bearer {VALID_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized. Check your token.")

    for user in MOCK_USERS:
        if user["id"] == user_id:
            if "fullName" in body:
                user["fullName"] = body["fullName"]
            return user

    raise HTTPException(status_code=404, detail=f"User {user_id} not found")


@app.post("/api/issues/{issue_id}/commands")
def run_command(
    issue_id: str,
    body: dict[str, Any] = Body(...),
    authorization: str | None = Header(default=None),
):
    if authorization != f"Bearer {VALID_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized. Check your token.")

    for issue in MOCK_ISSUES:
        if issue["id"] == issue_id:
            return {"issue": issue_id, "query": body.get("query", ""), "applied": True}

    raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found")


@app.post("/api/issues/{issue_id}/comments", status_code=201)
def add_comment(
    issue_id: str,
    body: dict[str, Any] = Body(...),
    authorization: str | None = Header(default=None),
):
    if authorization != f"Bearer {VALID_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized. Check your token.")

    for issue in MOCK_ISSUES:
        if issue["id"] == issue_id:
            return {"id": "comment-1", "text": body.get("text", ""), "issue": issue_id}

    raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found")


@app.post("/api/commands")
def bulk_command(body: dict[str, Any] = Body(...), authorization: str | None = Header(default=None)):
    if authorization != f"Bearer {VALID_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized. Check your token.")

    issues = body.get("issues", [])
    query = body.get("query", "")
    return {"query": query, "issues": issues, "applied": True}


@app.get("/api/users/me")
def whoami(authorization: str | None = Header(default=None)):
    """เอาไว้ทดสอบว่า token ใช้ได้ไหม (endpoint นี้ YouTrack จริงก็มี)"""
    if authorization != f"Bearer {VALID_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"login": "demo-user", "name": "Demo User"}