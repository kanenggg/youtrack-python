from typing import Any

import httpx
from fastapi import HTTPException

from app.config import HEADERS, YOUTRACK_BASE_URL


async def _send(client: httpx.AsyncClient, request: httpx.Request, operation: str) -> dict[str, Any] | list[Any]:
    resp = await client.send(request)
    print(f"[{operation}] status: {resp.status_code} {resp.reason_phrase}")
    if resp.text:
        print(f"[{operation}] response: {resp.text}")

    if not resp.is_success:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"{operation} failed: HTTP {resp.status_code} {resp.reason_phrase} - {resp.text}",
        )

    return resp.json() if resp.text else {}


async def get_issue(issue_id: str) -> dict[str, Any]:
    url = f"{YOUTRACK_BASE_URL}/api/issues/{issue_id}"
    params = {"fields": "id,summary,description,project(id,name),assignee(email,name)"}
    async with httpx.AsyncClient(timeout=5) as client:
        request = client.build_request("GET", url, params=params, headers=HEADERS)
        return await _send(client, request, "getIssue")


async def create_issue(summary: str, description: str, project_id: str) -> dict[str, Any]:
    url = f"{YOUTRACK_BASE_URL}/api/issues"
    params = {"fields": "id,summary,project(id,name)"}
    body = {"summary": summary, "description": description, "project": {"id": project_id}}
    async with httpx.AsyncClient(timeout=5) as client:
        request = client.build_request("POST", url, params=params, headers=HEADERS, json=body)
        return await _send(client, request, "createIssue")


async def update_user_email(issue_id: str, new_email: str) -> dict[str, Any]:
    """เปลี่ยน assignee ของ issue ผ่าน YouTrack commands API"""
    url = f"{YOUTRACK_BASE_URL}/api/issues/{issue_id}/commands"
    body = {"query": f"assignee {new_email}"}
    async with httpx.AsyncClient(timeout=5) as client:
        request = client.build_request("POST", url, headers=HEADERS, json=body)
        return await _send(client, request, "updateUserEmail")


async def get_all_youtrack_users() -> list[Any]:
    url = f"{YOUTRACK_BASE_URL}/api/admin/users"
    params = {"fields": "id,login,email,fullName"}
    async with httpx.AsyncClient(timeout=5) as client:
        request = client.build_request("GET", url, params=params, headers=HEADERS)
        return await _send(client, request, "getAllUsers")


async def get_user_by_email(email: str) -> dict[str, Any] | list[Any]:
    url = f"{YOUTRACK_BASE_URL}/api/admin/users"
    params = {"fields": "id,login,email,fullName", "query": email}
    async with httpx.AsyncClient(timeout=5) as client:
        request = client.build_request("GET", url, params=params, headers=HEADERS)
        return await _send(client, request, "getUserByEmail")


async def update_user_name(user_id: str, new_name: str) -> dict[str, Any]:
    url = f"{YOUTRACK_BASE_URL}/api/admin/users/{user_id}"
    params = {"fields": "id,fullName,email"}
    body = {"fullName": new_name}
    async with httpx.AsyncClient(timeout=5) as client:
        request = client.build_request("POST", url, params=params, headers=HEADERS, json=body)
        return await _send(client, request, "updateUserName")


async def set_state(issue_id: str, state_name: str) -> dict[str, Any]:
    url = f"{YOUTRACK_BASE_URL}/api/commands"
    body = {
        "query": f"State {state_name}",
        "issues": [{"$type": "Issue", "idReadable": issue_id}],
    }
    print(f"[setState] URL: {url}")
    print(f"[setState] BODY: {body}")
    async with httpx.AsyncClient(timeout=5) as client:
        request = client.build_request("POST", url, headers=HEADERS, json=body)
        return await _send(client, request, "setState")


async def add_comment(issue_id: str, text: str) -> dict[str, Any]:
    url = f"{YOUTRACK_BASE_URL}/api/issues/{issue_id}/comments"
    body = {"text": text}
    async with httpx.AsyncClient(timeout=5) as client:
        request = client.build_request("POST", url, headers=HEADERS, json=body)
        return await _send(client, request, "addComment")