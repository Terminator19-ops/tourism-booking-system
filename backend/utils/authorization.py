from typing import Any, Dict, Optional

from fastapi import Depends, Header, HTTPException, status

from backend.utils.authentication import get_session_user, normalize_role


async def get_current_user(authorization: Optional[str] = Header(default=None, alias="Authorization")) -> Dict[str, Any]:
    """Get the current authenticated user from the session token."""
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


def require_customer(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Require the current user to have CUSTOMER role."""
    if normalize_role(current_user.get("role")) != "CUSTOMER":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customer access required.")
    return current_user


def require_owner(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Require the current user to have OWNER role."""
    if normalize_role(current_user.get("role")) != "OWNER":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner access required.")
    return current_user


def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Require the current user to have ADMIN role."""
    if normalize_role(current_user.get("role")) != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return current_user


def require_customer_or_owner(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Require the current user to have CUSTOMER or OWNER role."""
    role = normalize_role(current_user.get("role"))
    if role not in {"CUSTOMER", "OWNER"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customer or Owner access required.")
    return current_user


def require_any_authenticated(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Require any authenticated user (any role)."""
    return current_user


async def verify_hotel_ownership(hotel_id: int, owner_id: int) -> bool:
    """Verify that a hotel belongs to the given owner."""
    from backend.database.connection import get_connection
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM HOTEL WHERE HOTEL_ID = :hotel_id AND OWNER_ID = :owner_id",
                {"hotel_id": hotel_id, "owner_id": owner_id}
            )
            return cur.fetchone()[0] > 0


async def verify_room_ownership(room_id: int, owner_id: int) -> bool:
    """Verify that a room belongs to a hotel owned by the given owner."""
    from backend.database.connection import get_connection
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) FROM ROOM r
                JOIN HOTEL h ON r.HOTEL_ID = h.HOTEL_ID
                WHERE r.ROOM_ID = :room_id AND h.OWNER_ID = :owner_id
                """,
                {"room_id": room_id, "owner_id": owner_id}
            )
            return cur.fetchone()[0] > 0


async def verify_booking_ownership(booking_id: int, user_id: int) -> bool:
    """Verify that a booking belongs to the given user."""
    from backend.database.connection import get_connection
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM BOOKING WHERE BOOKING_ID = :booking_id AND USER_ID = :user_id",
                {"booking_id": booking_id, "user_id": user_id}
            )
            return cur.fetchone()[0] > 0


async def verify_trip_ownership(trip_id: int, user_id: int) -> bool:
    """Verify that a trip belongs to the given user."""
    from backend.database.connection import get_connection
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM TRIP WHERE TRIP_ID = :trip_id AND USER_ID = :user_id",
                {"trip_id": trip_id, "user_id": user_id}
            )
            return cur.fetchone()[0] > 0


async def get_owner_hotel_ids(owner_id: int) -> list:
    """Get all hotel IDs owned by the given owner."""
    from backend.database.connection import get_connection
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT HOTEL_ID FROM HOTEL WHERE OWNER_ID = :owner_id",
                {"owner_id": owner_id}
            )
            return [row[0] for row in cur.fetchall()]


async def get_owner_room_ids(owner_id: int) -> list:
    """Get all room IDs for hotels owned by the given owner."""
    from backend.database.connection import get_connection
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT r.ROOM_ID FROM ROOM r
                JOIN HOTEL h ON r.HOTEL_ID = h.HOTEL_ID
                WHERE h.OWNER_ID = :owner_id
                """,
                {"owner_id": owner_id}
            )
            return [row[0] for row in cur.fetchall()]