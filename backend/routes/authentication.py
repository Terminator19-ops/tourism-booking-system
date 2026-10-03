from typing import Any, Dict, Optional

import oracledb
from fastapi import APIRouter, Depends, Header, HTTPException, status

from backend.database.connection import get_connection
from backend.schemas.authentication import (
    AuthTokenResponse,
    ChangePasswordRequest,
    LoginRequest,
    ProfileUpdateRequest,
    RegistrationRequest,
    UserPublic,
)
from backend.utils.authentication import (
    create_session,
    get_session_user,
    hash_password,
    invalidate_session,
    normalize_role,
    serialize_user,
    verify_password,
)

router = APIRouter(prefix="/api/auth")


async def get_current_user(authorization: Optional[str] = Header(default=None, alias="Authorization")) -> Dict[str, Any]:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization token.")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header.")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token value.")

    user = get_session_user(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")
    return user


def _fetch_user_by_email(email: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT USER_ID, FIRST_NAME, LAST_NAME, EMAIL, PHONE, PASSWORD_HASH, ROLE, STATUS
                FROM APP_USER
                WHERE EMAIL = :email
                """,
                {"email": email},
            )
            columns = [col[0].lower() for col in cur.description]
            row = cur.fetchone()
            if not row:
                return None
            return dict(zip(columns, row))


def _fetch_user_by_id(user_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT USER_ID, FIRST_NAME, LAST_NAME, EMAIL, PHONE, PASSWORD_HASH, ROLE, STATUS
                FROM APP_USER
                WHERE USER_ID = :user_id
                """,
                {"user_id": user_id},
            )
            columns = [col[0].lower() for col in cur.description]
            row = cur.fetchone()
            if not row:
                return None
            return dict(zip(columns, row))


@router.post("/register/customer", response_model=AuthTokenResponse)
async def register_customer(payload: RegistrationRequest):
    email = payload.normalized_email
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM APP_USER WHERE EMAIL = :email", {"email": email})
            if cur.fetchone()[0] > 0:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")

            user_id = cur.var(oracledb.NUMBER)
            password_hash = hash_password(payload.password)
            cur.execute(
                """
                BEGIN
                    sp_register_customer(:first_name, :last_name, :email, :phone, :password_hash, :user_id);
                END;
                """,
                {
                    "first_name": payload.first_name.strip(),
                    "last_name": payload.last_name.strip(),
                    "email": email,
                    "phone": payload.phone.strip(),
                    "password_hash": password_hash,
                    "user_id": user_id,
                },
            )
            user_record = _fetch_user_by_email(email)

    if user_record is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User registration failed.")

    user_payload = serialize_user(user_record)
    token = create_session(user_payload)
    return AuthTokenResponse(
        access_token=token,
        user=UserPublic(**user_payload),
    )


@router.post("/register/owner", response_model=AuthTokenResponse)
async def register_owner(payload: RegistrationRequest):
    email = payload.normalized_email
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM APP_USER WHERE EMAIL = :email", {"email": email})
            if cur.fetchone()[0] > 0:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")

            user_id = cur.var(oracledb.NUMBER)
            password_hash = hash_password(payload.password)
            cur.execute(
                """
                SELECT NVL(MAX(USER_ID), 0) + 1 FROM APP_USER
                """
            )
            next_user_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO APP_USER (
                    USER_ID, FIRST_NAME, LAST_NAME, EMAIL, PHONE,
                    PASSWORD_HASH, ROLE, STATUS, CREATED_AT
                ) VALUES (
                    :user_id, :first_name, :last_name, :email, :phone,
                    :password_hash, 'OWNER', 'ACTIVE', CURRENT_TIMESTAMP
                )
                """,
                {
                    "user_id": next_user_id,
                    "first_name": payload.first_name.strip(),
                    "last_name": payload.last_name.strip(),
                    "email": email,
                    "phone": payload.phone.strip(),
                    "password_hash": password_hash,
                },
            )
            conn.commit()
            user_record = _fetch_user_by_email(email)

    if user_record is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Owner registration failed.")

    user_payload = serialize_user(user_record)
    token = create_session(user_payload)
    return AuthTokenResponse(
        access_token=token,
        user=UserPublic(**user_payload),
    )


@router.post("/login", response_model=AuthTokenResponse)
async def login(payload: LoginRequest):
    email = payload.email.strip().lower()
    selected_role = normalize_role(payload.role)

    if selected_role not in {"CUSTOMER", "OWNER", "ADMIN"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role must be CUSTOMER, OWNER, or ADMIN.")

    user_record = _fetch_user_by_email(email)
    if not user_record:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    if normalize_role(user_record.get("role")) != selected_role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Selected role does not match account role.")

    if normalize_role(user_record.get("status")) != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not active.")

    if not verify_password(payload.password, user_record.get("password_hash")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    user_payload = serialize_user(user_record)
    token = create_session(user_payload)
    return AuthTokenResponse(
        access_token=token,
        user=UserPublic(**user_payload),
    )


@router.get("/me")
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    user_record = _fetch_user_by_id(current_user["user_id"])
    if not user_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return serialize_user(user_record)


@router.put("/me")
async def update_me(payload: ProfileUpdateRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    first_name = (payload.first_name or "").strip()
    last_name = (payload.last_name or "").strip()
    phone = (payload.phone or "").strip()

    if not first_name or not last_name or not phone:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="First name, last name and phone are required.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE APP_USER
                SET FIRST_NAME = :first_name,
                    LAST_NAME = :last_name,
                    PHONE = :phone
                WHERE USER_ID = :user_id
                """,
                {
                    "first_name": first_name,
                    "last_name": last_name,
                    "phone": phone,
                    "user_id": current_user["user_id"],
                },
            )
            conn.commit()

    user_record = _fetch_user_by_id(current_user["user_id"])
    return serialize_user(user_record)


@router.put("/change-password")
async def change_password(payload: ChangePasswordRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    user_record = _fetch_user_by_id(current_user["user_id"])
    if not user_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if not verify_password(payload.current_password, user_record.get("password_hash")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect.")

    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New passwords do not match.")

    if len(payload.new_password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 8 characters long.")

    new_hash = hash_password(payload.new_password)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE APP_USER SET PASSWORD_HASH = :password_hash WHERE USER_ID = :user_id",
                {"password_hash": new_hash, "user_id": current_user["user_id"]},
            )
            conn.commit()
    return {"message": "Password changed successfully."}


@router.post("/logout")
async def logout(authorization: Optional[str] = Header(default=None, alias="Authorization")):
    token = None
    if authorization:
        if authorization.lower().startswith("bearer "):
            token = authorization.split(" ", 1)[1].strip()
    invalidate_session(token)
    return {"message": "Logged out successfully."}


@router.get("/health")
async def health_check():
    return {"status": "ok"}
