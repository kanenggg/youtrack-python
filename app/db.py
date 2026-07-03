from user.rules import MOCK_USERS

# mock DB — key: email, value: {id, full_name}
_mock_db: dict[str, dict] = {
    u["email"]: {"id": u["id"], "full_name": u["fullName"]} for u in MOCK_USERS
}


async def init_pool():
    pass


async def close_pool():
    pass


async def get_mock_user_by_email(email: str) -> dict | None:
    return _mock_db.get(email)


async def update_user_name_in_db(email: str, current_first: str, current_last: str, new_full_name: str) -> None:
    """เช็คชื่อปัจจุบันก่อน — raise ถ้าไม่พบหรือชื่อไม่ตรง"""
    user = _mock_db.get(email)
    if user is None:
        raise ValueError(f"ไม่พบ user ที่มีอีเมล {email} ใน DB")
    current_full = f"{current_first} {current_last}"
    if user["full_name"] != current_full:
        raise ValueError(f"ชื่อปัจจุบันไม่ตรง: คาดหวัง '{user['full_name']}' แต่ได้ '{current_full}'")
    _mock_db[email]["full_name"] = new_full_name
    _mock_db[email] = new_full_name
