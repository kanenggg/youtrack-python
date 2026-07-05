from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

from user.models import (
    AddCommentRequest,
    CreateCardRequest,
    SetStateRequest,
    UpdateEmailRequest,
    WebhookPayload,
    UpdateNameRequest
)
from user.rules import EMAIL_RULES, MOCK_USERS
from app.youtrack_client import (
    add_comment,
    create_issue,
    get_issue,
    get_user_by_email,
    get_all_youtrack_users,
    set_state,
    update_user_email,
    update_user_name,
)
from app.db import init_pool, close_pool, update_user_name_in_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()


app = FastAPI(title="YouTrack Connector", lifespan=lifespan)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/cards/{issue_id}")
async def get_card(issue_id: str):
    return await get_issue(issue_id)


@app.post("/api/cards", status_code=201)
async def create_card(req: CreateCardRequest):
    return await create_issue(req.summary, req.description or "", req.project_id)


@app.post("/api/workflow/update-email")
async def workflow_update_email(req: UpdateEmailRequest):
    return await update_user_email(req.issue_id, req.new_email)


@app.post("/api/webhook/state-changed")
async def webhook_state_changed(payload: WebhookPayload):
    """รับ email จาก customField -> เช็ค domain กับ EMAIL_RULES -> หา user -> แก้ไขชื่อ"""
    email = payload.custom_field
    if not email:
        raise HTTPException(status_code=400, detail={"success": False, "message": "customField is empty"})

    domain = email.split("@")[-1] if "@" in email else ""
    new_name = EMAIL_RULES.get(domain)

    if new_name is None:
        return {"success": False, "message": f"no rule matched for domain: {domain}"}

    user = await get_user_by_email(email)
    user_id = user[0]["id"] if isinstance(user, list) and user else None

    if user_id is None:
        raise HTTPException(status_code=404, detail={"success": False, "message": "user not found"})

    await update_user_name(user_id, new_name)
    return {"success": True, "email": email, "newName": new_name}


@app.get("/api/users")
async def get_all_users():
    return await get_all_youtrack_users()


@app.get("/api/mock-users")
async def mock_users():
    return MOCK_USERS


@app.post("/api/cards/{issue_id}/state")
async def update_card_state(issue_id: str, req: SetStateRequest):
    return await set_state(issue_id, req.state_name)


@app.post("/api/cards/{issue_id}/comments", status_code=201)
async def create_card_comment(issue_id: str, req: AddCommentRequest):
    return await add_comment(issue_id, req.text)


@app.post("/api/update-name")
async def update_name(req: UpdateNameRequest):
    try:
        await update_user_name_in_db(req.email, req.current_first_name, req.current_last_name, req.new_first_name, req.new_last_name)
    except ValueError as exc:
        return {"success": False, "message": str(exc)}

    return {"success": True, "message": f"แก้ไขชื่อเป็น {req.new_first_name} {req.new_last_name} สำเร็จ"}