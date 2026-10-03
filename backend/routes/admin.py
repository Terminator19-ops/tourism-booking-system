from typing import Any, Dict, List, Optional
import json

from fastapi import APIRouter, Depends, HTTPException, status, Query

from backend.database.connection import get_connection
from backend.utils.authorization import require_admin, get_current_user
from backend.utils.audit import log_create, log_update, log_delete, log_deactivate, log_user_management
from backend.schemas.authentication import (
    AdminUserCreateRequest, AdminUserUpdateRequest, AdminUserResponse,
    AdminHotelResponse, AdminRoomResponse, AdminActivityResponse,
    AdminTourPackageResponse, AdminTravelSegmentResponse, AdminDestinationResponse,
    AdminTripResponse, AdminBookingResponse, AdminReportResponse, AuditLogResponse
)

router = APIRouter(prefix="/api/admin")


def _convert_lob(value: Any) -> Any:
    """Convert Oracle LOB objects to strings for JSON serialization."""
    if hasattr(value, 'read'):
        return value.read()
    return value


async def _fetch_rows(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or {})
            columns = [col[0].lower() for col in cur.description]
            rows = []
            for row in cur.fetchall():
                rows.append({columns[i]: _convert_lob(row[i]) for i in range(len(columns))})
            return rows


async def _execute(query: str, params: Optional[Dict[str, Any]] = None) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or {})
            conn.commit()
            return cur.rowcount


async def _fetch_one(query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or {})
            columns = [col[0].lower() for col in cur.description]
            row = cur.fetchone()
            if row:
                return {columns[i]: _convert_lob(row[i]) for i in range(len(columns))}
            return None


@router.get("/destinations")
async def list_destinations(current_user: Dict[str, Any] = Depends(require_admin)):
    rows = await _fetch_rows("SELECT * FROM DESTINATION ORDER BY DESTINATION_ID")
    return rows


@router.post("/destinations")
async def create_destination(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_admin)):
    name = str(payload.get("name") or "").strip()
    city = str(payload.get("city") or "").strip()
    country = str(payload.get("country") or "").strip()
    if not name or not city or not country:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name, city and country are required.")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT NVL(MAX(destination_id),0) + 1 FROM DESTINATION")
            destination_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO DESTINATION (
                    destination_id, name, city, state, country, description, status
                ) VALUES (:destination_id, :name, :city, :state, :country, :description, :status)
                """,
                {
                    "destination_id": destination_id,
                    "name": name,
                    "city": city,
                    "state": payload.get("state"),
                    "country": country,
                    "description": payload.get("description"),
                    "status": (payload.get("status") or "ACTIVE").upper(),
                },
            )
            conn.commit()
    await log_create(current_user["user_id"], "DESTINATION", destination_id, f"Destination: {name}")
    return {"message": "Destination created successfully."}


@router.put("/destinations/{destination_id}")
async def update_destination(destination_id: int, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_admin)):
    old_dest = await _fetch_one("SELECT * FROM DESTINATION WHERE DESTINATION_ID = :destination_id", {"destination_id": destination_id})
    if not old_dest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination not found.")
    
    allowed_fields = ["NAME", "CITY", "STATE", "COUNTRY", "DESCRIPTION", "LATITUDE", "LONGITUDE", "STATUS"]
    updates = []
    params = {"destination_id": destination_id}
    
    for field in allowed_fields:
        if field.lower() in payload and payload[field.lower()] is not None:
            updates.append(f"{field} = :{field.lower()}")
            params[field.lower()] = payload[field.lower()]
    
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields to update.")
    
    query = f"UPDATE DESTINATION SET {', '.join(updates)} WHERE DESTINATION_ID = :destination_id"
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
    
    await log_update(current_user["user_id"], "DESTINATION", destination_id, str(old_dest), str(payload))
    return {"message": "Destination updated successfully."}


@router.delete("/destinations/{destination_id}")
async def delete_destination(destination_id: int, current_user: Dict[str, Any] = Depends(require_admin)):
    old_dest = await _fetch_one("SELECT * FROM DESTINATION WHERE DESTINATION_ID = :destination_id", {"destination_id": destination_id})
    if not old_dest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination not found.")
    
    # Check for dependencies
    deps = await _fetch_one("""
        SELECT 
            (SELECT COUNT(*) FROM HOTEL WHERE DESTINATION_ID = :destination_id) AS hotels,
            (SELECT COUNT(*) FROM ACTIVITY WHERE DESTINATION_ID = :destination_id) AS activities,
            (SELECT COUNT(*) FROM TRAVEL_SEGMENT WHERE ORIGIN_DESTINATION_ID = :destination_id OR DESTINATION_DESTINATION_ID = :destination_id) AS travel_segments,
            (SELECT COUNT(*) FROM PACKAGE_DESTINATION WHERE DESTINATION_ID = :destination_id) AS package_destinations,
            (SELECT COUNT(*) FROM TRIP_DESTINATION WHERE DESTINATION_ID = :destination_id) AS trip_destinations
        FROM DUAL
    """, {"destination_id": destination_id})
    
    if deps and any(v > 0 for v in deps.values()):
        # Soft delete instead
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE DESTINATION SET STATUS = 'INACTIVE' WHERE DESTINATION_ID = :destination_id", {"destination_id": destination_id})
                conn.commit()
        await log_deactivate(current_user["user_id"], "DESTINATION", destination_id, str(old_dest))
        return {"message": "Destination has dependencies, deactivated instead of deleted."}
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM DESTINATION WHERE DESTINATION_ID = :destination_id", {"destination_id": destination_id})
            conn.commit()
    await log_delete(current_user["user_id"], "DESTINATION", destination_id, str(old_dest))
    return {"message": "Destination deleted successfully."}


@router.get("/hotels")
async def list_hotels(current_user: Dict[str, Any] = Depends(require_admin)):
    rows = await _fetch_rows("""
        SELECT h.*, u.FIRST_NAME || ' ' || u.LAST_NAME AS OWNER_NAME, d.NAME AS DESTINATION_NAME
        FROM HOTEL h
        JOIN APP_USER u ON h.OWNER_ID = u.USER_ID
        JOIN DESTINATION d ON h.DESTINATION_ID = d.DESTINATION_ID
        ORDER BY h.HOTEL_ID
    """)
    return rows


@router.post("/hotels")
async def create_hotel(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_admin)):
    name = str(payload.get("name") or "").strip()
    destination_id = payload.get("destination_id")
    address = str(payload.get("address") or "").strip()
    if not name or not destination_id or not address:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name, destination_id and address are required.")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT NVL(MAX(hotel_id),0) + 1 FROM HOTEL")
            hotel_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO HOTEL (
                    hotel_id, owner_id, destination_id, name, description, address,
                    contact_number, email, star_rating, status
                ) VALUES (
                    :hotel_id, :owner_id, :destination_id, :name, :description,
                    :address, :contact_number, :email, :star_rating, :status
                )
                """,
                {
                    "hotel_id": hotel_id,
                    "owner_id": payload.get("owner_id") or current_user["user_id"],
                    "destination_id": destination_id,
                    "name": name,
                    "description": payload.get("description"),
                    "address": address,
                    "contact_number": payload.get("contact_number"),
                    "email": payload.get("email"),
                    "star_rating": payload.get("star_rating") or 4.5,
                    "status": (payload.get("status") or "ACTIVE").upper(),
                },
            )
            conn.commit()
    await log_create(current_user["user_id"], "HOTEL", hotel_id, f"Hotel: {name}")
    return {"message": "Hotel created successfully."}


@router.get("/hotels/{hotel_id}")
async def get_hotel(hotel_id: int, current_user: Dict[str, Any] = Depends(require_admin)):
    hotel = await _fetch_one("""
        SELECT h.*, u.FIRST_NAME || ' ' || u.LAST_NAME AS OWNER_NAME, d.NAME AS DESTINATION_NAME
        FROM HOTEL h
        JOIN APP_USER u ON h.OWNER_ID = u.USER_ID
        JOIN DESTINATION d ON h.DESTINATION_ID = d.DESTINATION_ID
        WHERE h.HOTEL_ID = :hotel_id
    """, {"hotel_id": hotel_id})
    if not hotel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found.")
    return hotel


@router.put("/hotels/{hotel_id}")
async def update_hotel(hotel_id: int, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_admin)):
    old_hotel = await _fetch_one("SELECT * FROM HOTEL WHERE HOTEL_ID = :hotel_id", {"hotel_id": hotel_id})
    if not old_hotel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found.")
    
    allowed_fields = ["OWNER_ID", "DESTINATION_ID", "NAME", "DESCRIPTION", "ADDRESS", "CONTACT_NUMBER", "EMAIL", "STAR_RATING", "STATUS"]
    updates = []
    params = {"hotel_id": hotel_id}
    
    for field in allowed_fields:
        if field.lower() in payload and payload[field.lower()] is not None:
            updates.append(f"{field} = :{field.lower()}")
            params[field.lower()] = payload[field.lower()]
    
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields to update.")
    
    query = f"UPDATE HOTEL SET {', '.join(updates)} WHERE HOTEL_ID = :hotel_id"
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
    
    await log_update(current_user["user_id"], "HOTEL", hotel_id, str(old_hotel), str(payload))
    return {"message": "Hotel updated successfully."}


@router.delete("/hotels/{hotel_id}")
async def delete_hotel(hotel_id: int, current_user: Dict[str, Any] = Depends(require_admin)):
    old_hotel = await _fetch_one("SELECT * FROM HOTEL WHERE HOTEL_ID = :hotel_id", {"hotel_id": hotel_id})
    if not old_hotel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found.")
    
    # Check for dependencies
    deps = await _fetch_one("""
        SELECT 
            (SELECT COUNT(*) FROM ROOM WHERE HOTEL_ID = :hotel_id) AS rooms,
            (SELECT COUNT(*) FROM BOOKING b JOIN HOTEL_BOOKING hb ON b.BOOKING_ID = hb.BOOKING_ID JOIN ROOM r ON hb.ROOM_ID = r.ROOM_ID WHERE r.HOTEL_ID = :hotel_id AND b.STATUS NOT IN ('CANCELLED', 'COMPLETED')) AS active_bookings
        FROM DUAL
    """, {"hotel_id": hotel_id})
    
    if deps and (deps.get("rooms", 0) > 0 or deps.get("active_bookings", 0) > 0):
        # Soft delete instead
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE HOTEL SET STATUS = 'INACTIVE' WHERE HOTEL_ID = :hotel_id", {"hotel_id": hotel_id})
                cur.execute("UPDATE ROOM SET STATUS = 'INACTIVE' WHERE HOTEL_ID = :hotel_id", {"hotel_id": hotel_id})
                conn.commit()
        await log_deactivate(current_user["user_id"], "HOTEL", hotel_id, str(old_hotel))
        return {"message": "Hotel has dependencies, deactivated instead of deleted."}
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM HOTEL WHERE HOTEL_ID = :hotel_id", {"hotel_id": hotel_id})
            conn.commit()
    await log_delete(current_user["user_id"], "HOTEL", hotel_id, str(old_hotel))
    return {"message": "Hotel deleted successfully."}


@router.get("/tour-packages")
async def list_tour_packages(current_user: Dict[str, Any] = Depends(require_admin)):
    rows = await _fetch_rows("SELECT * FROM TOUR_PACKAGE ORDER BY PACKAGE_ID")
    return rows


@router.get("/tour-packages/{package_id}")
async def get_tour_package(package_id: int, current_user: Dict[str, Any] = Depends(require_admin)):
    pkg = await _fetch_one("SELECT * FROM TOUR_PACKAGE WHERE PACKAGE_ID = :package_id", {"package_id": package_id})
    if not pkg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tour package not found.")
    
    # Add destinations and activities
    destinations = await _fetch_rows("""
        SELECT d.DESTINATION_ID, d.NAME, pd.VISIT_ORDER, pd.DAYS
        FROM PACKAGE_DESTINATION pd
        JOIN DESTINATION d ON pd.DESTINATION_ID = d.DESTINATION_ID
        WHERE pd.PACKAGE_ID = :package_id
        ORDER BY pd.VISIT_ORDER
    """, {"package_id": package_id})
    
    activities = await _fetch_rows("""
        SELECT a.ACTIVITY_ID, a.NAME, pa.ACTIVITY_DAY
        FROM PACKAGE_ACTIVITY pa
        JOIN ACTIVITY a ON pa.ACTIVITY_ID = a.ACTIVITY_ID
        WHERE pa.PACKAGE_ID = :package_id
        ORDER BY pa.ACTIVITY_DAY
    """, {"package_id": package_id})
    
    pkg["destinations"] = destinations
    pkg["activities"] = activities
    return pkg


@router.post("/tour-packages")
async def create_tour_package(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_admin)):
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name is required.")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT NVL(MAX(package_id),0) + 1 FROM TOUR_PACKAGE")
            package_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO TOUR_PACKAGE (
                    package_id, name, description, duration_days, price, max_capacity, status
                ) VALUES (
                    :package_id, :name, :description, :duration_days, :price, :max_capacity, :status
                )
                """,
                {
                    "package_id": package_id,
                    "name": name,
                    "description": payload.get("description"),
                    "duration_days": payload.get("duration_days") or 1,
                    "price": payload.get("price") or 0,
                    "max_capacity": payload.get("max_capacity"),
                    "status": (payload.get("status") or "ACTIVE").upper(),
                },
            )
            conn.commit()
    await log_create(current_user["user_id"], "TOUR_PACKAGE", package_id, f"Package: {name}")
    return {"message": "Tour package created successfully."}


@router.put("/tour-packages/{package_id}")
async def update_tour_package(package_id: int, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_admin)):
    old_pkg = await _fetch_one("SELECT * FROM TOUR_PACKAGE WHERE PACKAGE_ID = :package_id", {"package_id": package_id})
    if not old_pkg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tour package not found.")
    
    allowed_fields = ["NAME", "DESCRIPTION", "DURATION_DAYS", "PRICE", "MAX_CAPACITY", "STATUS"]
    updates = []
    params = {"package_id": package_id}
    
    for field in allowed_fields:
        if field.lower() in payload and payload[field.lower()] is not None:
            updates.append(f"{field} = :{field.lower()}")
            params[field.lower()] = payload[field.lower()]
    
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields to update.")
    
    query = f"UPDATE TOUR_PACKAGE SET {', '.join(updates)} WHERE PACKAGE_ID = :package_id"
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
    
    await log_update(current_user["user_id"], "TOUR_PACKAGE", package_id, str(old_pkg), str(payload))
    return {"message": "Tour package updated successfully."}


@router.delete("/tour-packages/{package_id}")
async def delete_tour_package(package_id: int, current_user: Dict[str, Any] = Depends(require_admin)):
    old_pkg = await _fetch_one("SELECT * FROM TOUR_PACKAGE WHERE PACKAGE_ID = :package_id", {"package_id": package_id})
    if not old_pkg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tour package not found.")
    
    # Check for dependencies
    deps = await _fetch_one("""
        SELECT 
            (SELECT COUNT(*) FROM PACKAGE_BOOKING WHERE PACKAGE_ID = :package_id) AS bookings,
            (SELECT COUNT(*) FROM PACKAGE_DESTINATION WHERE PACKAGE_ID = :package_id) AS destinations,
            (SELECT COUNT(*) FROM PACKAGE_ACTIVITY WHERE PACKAGE_ID = :package_id) AS activities
        FROM DUAL
    """, {"package_id": package_id})
    
    if deps and any(v > 0 for v in deps.values()):
        # Soft delete instead
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE TOUR_PACKAGE SET STATUS = 'INACTIVE' WHERE PACKAGE_ID = :package_id", {"package_id": package_id})
                conn.commit()
        await log_deactivate(current_user["user_id"], "TOUR_PACKAGE", package_id, str(old_pkg))
        return {"message": "Tour package has dependencies, deactivated instead of deleted."}
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM TOUR_PACKAGE WHERE PACKAGE_ID = :package_id", {"package_id": package_id})
            conn.commit()
    await log_delete(current_user["user_id"], "TOUR_PACKAGE", package_id, str(old_pkg))
    return {"message": "Tour package deleted successfully."}


@router.post("/tour-packages/{package_id}/destinations")
async def add_package_destination(package_id: int, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_admin)):
    destination_id = payload.get("destination_id")
    visit_order = payload.get("visit_order")
    days = payload.get("days")
    
    if not destination_id or not visit_order or not days:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="destination_id, visit_order, and days are required.")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO PACKAGE_DESTINATION (PACKAGE_ID, DESTINATION_ID, VISIT_ORDER, DAYS)
                VALUES (:package_id, :destination_id, :visit_order, :days)
                """,
                {"package_id": package_id, "destination_id": destination_id, "visit_order": visit_order, "days": days}
            )
            conn.commit()
    await log_create(current_user["user_id"], "PACKAGE_DESTINATION", package_id, f"Destination: {destination_id}")
    return {"message": "Destination added to package successfully."}


@router.delete("/tour-packages/{package_id}/destinations/{destination_id}")
async def remove_package_destination(package_id: int, destination_id: int, current_user: Dict[str, Any] = Depends(require_admin)):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM PACKAGE_DESTINATION WHERE PACKAGE_ID = :package_id AND DESTINATION_ID = :destination_id",
                {"package_id": package_id, "destination_id": destination_id}
            )
            conn.commit()
    await log_delete(current_user["user_id"], "PACKAGE_DESTINATION", package_id, f"Destination: {destination_id}")
    return {"message": "Destination removed from package successfully."}


@router.post("/tour-packages/{package_id}/activities")
async def add_package_activity(package_id: int, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_admin)):
    activity_id = payload.get("activity_id")
    activity_day = payload.get("activity_day")
    
    if not activity_id or not activity_day:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="activity_id and activity_day are required.")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO PACKAGE_ACTIVITY (PACKAGE_ID, ACTIVITY_ID, ACTIVITY_DAY)
                VALUES (:package_id, :activity_id, :activity_day)
                """,
                {"package_id": package_id, "activity_id": activity_id, "activity_day": activity_day}
            )
            conn.commit()
    await log_create(current_user["user_id"], "PACKAGE_ACTIVITY", package_id, f"Activity: {activity_id}")
    return {"message": "Activity added to package successfully."}


@router.delete("/tour-packages/{package_id}/activities/{activity_id}")
async def remove_package_activity(package_id: int, activity_id: int, current_user: Dict[str, Any] = Depends(require_admin)):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM PACKAGE_ACTIVITY WHERE PACKAGE_ID = :package_id AND ACTIVITY_ID = :activity_id",
                {"package_id": package_id, "activity_id": activity_id}
            )
            conn.commit()
    await log_delete(current_user["user_id"], "PACKAGE_ACTIVITY", package_id, f"Activity: {activity_id}")
    return {"message": "Activity removed from package successfully."}


@router.get("/activities")
async def list_activities(current_user: Dict[str, Any] = Depends(require_admin)):
    rows = await _fetch_rows("""
        SELECT a.*, d.NAME AS DESTINATION_NAME
        FROM ACTIVITY a
        JOIN DESTINATION d ON a.DESTINATION_ID = d.DESTINATION_ID
        ORDER BY a.ACTIVITY_ID
    """)
    return rows


@router.get("/activities/{activity_id}")
async def get_activity(activity_id: int, current_user: Dict[str, Any] = Depends(require_admin)):
    activity = await _fetch_one("""
        SELECT a.*, d.NAME AS DESTINATION_NAME
        FROM ACTIVITY a
        JOIN DESTINATION d ON a.DESTINATION_ID = d.DESTINATION_ID
        WHERE a.ACTIVITY_ID = :activity_id
    """, {"activity_id": activity_id})
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found.")
    return activity


@router.post("/activities")
async def create_activity(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_admin)):
    destination_id = payload.get("destination_id")
    name = str(payload.get("name") or "").strip()
    if not destination_id or not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="destination_id and name are required.")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT NVL(MAX(activity_id),0) + 1 FROM ACTIVITY")
            activity_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO ACTIVITY (
                    activity_id, destination_id, name, description, category,
                    duration_hours, price, capacity, status
                ) VALUES (
                    :activity_id, :destination_id, :name, :description, :category,
                    :duration_hours, :price, :capacity, :status
                )
                """,
                {
                    "activity_id": activity_id,
                    "destination_id": destination_id,
                    "name": name,
                    "description": payload.get("description"),
                    "category": payload.get("category") or "General",
                    "duration_hours": payload.get("duration_hours") or 1,
                    "price": payload.get("price") or 0,
                    "capacity": payload.get("capacity") or 1,
                    "status": (payload.get("status") or "ACTIVE").upper(),
                },
            )
            conn.commit()
    await log_create(current_user["user_id"], "ACTIVITY", activity_id, f"Activity: {name}")
    return {"message": "Activity created successfully."}


@router.put("/activities/{activity_id}")
async def update_activity(activity_id: int, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_admin)):
    old_activity = await _fetch_one("SELECT * FROM ACTIVITY WHERE ACTIVITY_ID = :activity_id", {"activity_id": activity_id})
    if not old_activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found.")
    
    allowed_fields = ["DESTINATION_ID", "NAME", "DESCRIPTION", "CATEGORY", "DURATION_HOURS", "PRICE", "CAPACITY", "STATUS"]
    updates = []
    params = {"activity_id": activity_id}
    
    for field in allowed_fields:
        if field.lower() in payload and payload[field.lower()] is not None:
            updates.append(f"{field} = :{field.lower()}")
            params[field.lower()] = payload[field.lower()]
    
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields to update.")
    
    query = f"UPDATE ACTIVITY SET {', '.join(updates)} WHERE ACTIVITY_ID = :activity_id"
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
    
    await log_update(current_user["user_id"], "ACTIVITY", activity_id, str(old_activity), str(payload))
    return {"message": "Activity updated successfully."}


@router.delete("/activities/{activity_id}")
async def delete_activity(activity_id: int, current_user: Dict[str, Any] = Depends(require_admin)):
    old_activity = await _fetch_one("SELECT * FROM ACTIVITY WHERE ACTIVITY_ID = :activity_id", {"activity_id": activity_id})
    if not old_activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found.")
    
    # Check for dependencies
    deps = await _fetch_one("""
        SELECT 
            (SELECT COUNT(*) FROM PACKAGE_ACTIVITY WHERE ACTIVITY_ID = :activity_id) AS packages,
            (SELECT COUNT(*) FROM ACTIVITY_BOOKING WHERE ACTIVITY_ID = :activity_id) AS bookings
        FROM DUAL
    """, {"activity_id": activity_id})
    
    if deps and any(v > 0 for v in deps.values()):
        # Soft delete instead
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE ACTIVITY SET STATUS = 'INACTIVE' WHERE ACTIVITY_ID = :activity_id", {"activity_id": activity_id})
                conn.commit()
        await log_deactivate(current_user["user_id"], "ACTIVITY", activity_id, str(old_activity))
        return {"message": "Activity has dependencies, deactivated instead of deleted."}
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM ACTIVITY WHERE ACTIVITY_ID = :activity_id", {"activity_id": activity_id})
            conn.commit()
    await log_delete(current_user["user_id"], "ACTIVITY", activity_id, str(old_activity))
    return {"message": "Activity deleted successfully."}


# ============================================================
# TRAVEL SEGMENTS
# ============================================================

@router.get("/travel-segments")
async def list_travel_segments(current_user: Dict[str, Any] = Depends(require_admin)):
    rows = await _fetch_rows("""
        SELECT ts.*, 
               d1.NAME AS ORIGIN_NAME, d1.CITY AS ORIGIN_CITY, d1.COUNTRY AS ORIGIN_COUNTRY,
               d2.NAME AS DESTINATION_NAME, d2.CITY AS DESTINATION_CITY, d2.COUNTRY AS DESTINATION_COUNTRY
        FROM TRAVEL_SEGMENT ts
        JOIN DESTINATION d1 ON ts.ORIGIN_DESTINATION_ID = d1.DESTINATION_ID
        JOIN DESTINATION d2 ON ts.DESTINATION_DESTINATION_ID = d2.DESTINATION_ID
        ORDER BY ts.TRAVEL_SEGMENT_ID
    """)
    return rows


@router.get("/travel-segments/{segment_id}")
async def get_travel_segment(segment_id: int, current_user: Dict[str, Any] = Depends(require_admin)):
    segment = await _fetch_one("""
        SELECT ts.*, 
               d1.NAME AS ORIGIN_NAME, d1.CITY AS ORIGIN_CITY, d1.COUNTRY AS ORIGIN_COUNTRY,
               d2.NAME AS DESTINATION_NAME, d2.CITY AS DESTINATION_CITY, d2.COUNTRY AS DESTINATION_COUNTRY
        FROM TRAVEL_SEGMENT ts
        JOIN DESTINATION d1 ON ts.ORIGIN_DESTINATION_ID = d1.DESTINATION_ID
        JOIN DESTINATION d2 ON ts.DESTINATION_DESTINATION_ID = d2.DESTINATION_ID
        WHERE ts.TRAVEL_SEGMENT_ID = :segment_id
    """, {"segment_id": segment_id})
    if not segment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Travel segment not found.")
    return segment


@router.post("/travel-segments")
async def create_travel_segment(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_admin)):
    origin_id = payload.get("origin_destination_id")
    destination_id = payload.get("destination_destination_id")
    transport_type = str(payload.get("transport_type") or "").strip()
    duration_hours = payload.get("duration_hours")
    price = payload.get("price")
    
    if not origin_id or not destination_id or not transport_type or not duration_hours or price is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="origin_destination_id, destination_destination_id, transport_type, duration_hours, and price are required.")
    
    if origin_id == destination_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Origin and destination cannot be the same.")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT NVL(MAX(travel_segment_id),0) + 1 FROM TRAVEL_SEGMENT")
            segment_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO TRAVEL_SEGMENT (
                    travel_segment_id, origin_destination_id, destination_destination_id,
                    transport_type, duration_hours, price, status
                ) VALUES (
                    :segment_id, :origin_id, :destination_id,
                    :transport_type, :duration_hours, :price, :status
                )
                """,
                {
                    "segment_id": segment_id,
                    "origin_id": origin_id,
                    "destination_id": destination_id,
                    "transport_type": transport_type,
                    "duration_hours": duration_hours,
                    "price": price,
                    "status": (payload.get("status") or "ACTIVE").upper(),
                },
            )
            conn.commit()
    await log_create(current_user["user_id"], "TRAVEL_SEGMENT", segment_id, f"Segment: {origin_id} -> {destination_id}")
    return {"message": "Travel segment created successfully."}


@router.put("/travel-segments/{segment_id}")
async def update_travel_segment(segment_id: int, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_admin)):
    old_segment = await _fetch_one("SELECT * FROM TRAVEL_SEGMENT WHERE TRAVEL_SEGMENT_ID = :segment_id", {"segment_id": segment_id})
    if not old_segment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Travel segment not found.")
    
    allowed_fields = ["ORIGIN_DESTINATION_ID", "DESTINATION_DESTINATION_ID", "TRANSPORT_TYPE", "DURATION_HOURS", "PRICE", "STATUS"]
    updates = []
    params = {"segment_id": segment_id}
    
    for field in allowed_fields:
        if field.lower() in payload and payload[field.lower()] is not None:
            updates.append(f"{field} = :{field.lower()}")
            params[field.lower()] = payload[field.lower()]
    
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields to update.")
    
    # Validate origin != destination if both are being updated
    origin_id = payload.get("origin_destination_id", old_segment.get("origin_destination_id"))
    destination_id = payload.get("destination_destination_id", old_segment.get("destination_destination_id"))
    if origin_id == destination_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Origin and destination cannot be the same.")
    
    query = f"UPDATE TRAVEL_SEGMENT SET {', '.join(updates)} WHERE TRAVEL_SEGMENT_ID = :segment_id"
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
    
    await log_update(current_user["user_id"], "TRAVEL_SEGMENT", segment_id, str(old_segment), str(payload))
    return {"message": "Travel segment updated successfully."}


@router.delete("/travel-segments/{segment_id}")
async def delete_travel_segment(segment_id: int, current_user: Dict[str, Any] = Depends(require_admin)):
    old_segment = await _fetch_one("SELECT * FROM TRAVEL_SEGMENT WHERE TRAVEL_SEGMENT_ID = :segment_id", {"segment_id": segment_id})
    if not old_segment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Travel segment not found.")
    
    # Check for dependencies
    deps = await _fetch_one("""
        SELECT 
            (SELECT COUNT(*) FROM PACKAGE_TRAVEL WHERE SEGMENT_ID = :segment_id) AS packages,
            (SELECT COUNT(*) FROM TRIP_TRAVEL WHERE SEGMENT_ID = :segment_id) AS trips
        FROM DUAL
    """, {"segment_id": segment_id})
    
    if deps and any(v > 0 for v in deps.values()):
        # Soft delete instead
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE TRAVEL_SEGMENT SET STATUS = 'INACTIVE' WHERE TRAVEL_SEGMENT_ID = :segment_id", {"segment_id": segment_id})
                conn.commit()
        await log_deactivate(current_user["user_id"], "TRAVEL_SEGMENT", segment_id, str(old_segment))
        return {"message": "Travel segment has dependencies, deactivated instead of deleted."}
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM TRAVEL_SEGMENT WHERE TRAVEL_SEGMENT_ID = :segment_id", {"segment_id": segment_id})
            conn.commit()
    await log_delete(current_user["user_id"], "TRAVEL_SEGMENT", segment_id, str(old_segment))
    return {"message": "Travel segment deleted successfully."}


# ============================================================
# ROOMS
# ============================================================

@router.get("/rooms")
async def list_rooms(current_user: Dict[str, Any] = Depends(require_admin)):
    rows = await _fetch_rows("""
        SELECT r.*, h.NAME AS HOTEL_NAME
        FROM ROOM r
        JOIN HOTEL h ON r.HOTEL_ID = h.HOTEL_ID
        ORDER BY r.ROOM_ID
    """)
    return rows


@router.get("/rooms/{room_id}")
async def get_room(room_id: int, current_user: Dict[str, Any] = Depends(require_admin)):
    room = await _fetch_one("""
        SELECT r.*, h.NAME AS HOTEL_NAME
        FROM ROOM r
        JOIN HOTEL h ON r.HOTEL_ID = h.HOTEL_ID
        WHERE r.ROOM_ID = :room_id
    """, {"room_id": room_id})
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found.")
    return room


@router.post("/rooms")
async def create_room(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_admin)):
    hotel_id = payload.get("hotel_id")
    room_type = str(payload.get("room_type") or "").strip()
    price_per_night = payload.get("price_per_night")
    capacity = payload.get("capacity")
    
    if not hotel_id or not room_type or price_per_night is None or not capacity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="hotel_id, room_type, price_per_night, and capacity are required.")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT NVL(MAX(room_id),0) + 1 FROM ROOM")
            room_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO ROOM (
                    room_id, hotel_id, room_type, description, price_per_night,
                    capacity, amenities, status
                ) VALUES (
                    :room_id, :hotel_id, :room_type, :description, :price_per_night,
                    :capacity, :amenities, :status
                )
                """,
                {
                    "room_id": room_id,
                    "hotel_id": hotel_id,
                    "room_type": room_type,
                    "description": payload.get("description"),
                    "price_per_night": price_per_night,
                    "capacity": capacity,
                    "amenities": payload.get("amenities"),
                    "status": (payload.get("status") or "ACTIVE").upper(),
                },
            )
            conn.commit()
    await log_create(current_user["user_id"], "ROOM", room_id, f"Room: {room_type} at Hotel {hotel_id}")
    return {"message": "Room created successfully."}


@router.put("/rooms/{room_id}")
async def update_room(room_id: int, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_admin)):
    old_room = await _fetch_one("SELECT * FROM ROOM WHERE ROOM_ID = :room_id", {"room_id": room_id})
    if not old_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found.")
    
    allowed_fields = ["HOTEL_ID", "ROOM_TYPE", "DESCRIPTION", "PRICE_PER_NIGHT", "CAPACITY", "AMENITIES", "STATUS"]
    updates = []
    params = {"room_id": room_id}
    
    for field in allowed_fields:
        if field.lower() in payload and payload[field.lower()] is not None:
            updates.append(f"{field} = :{field.lower()}")
            params[field.lower()] = payload[field.lower()]
    
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields to update.")
    
    query = f"UPDATE ROOM SET {', '.join(updates)} WHERE ROOM_ID = :room_id"
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
    
    await log_update(current_user["user_id"], "ROOM", room_id, str(old_room), str(payload))
    return {"message": "Room updated successfully."}


@router.delete("/rooms/{room_id}")
async def delete_room(room_id: int, current_user: Dict[str, Any] = Depends(require_admin)):
    old_room = await _fetch_one("SELECT * FROM ROOM WHERE ROOM_ID = :room_id", {"room_id": room_id})
    if not old_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found.")
    
    # Check for dependencies
    deps = await _fetch_one("""
        SELECT 
            (SELECT COUNT(*) FROM BOOKING WHERE ROOM_ID = :room_id AND STATUS IN ('PENDING', 'CONFIRMED')) AS active_bookings,
            (SELECT COUNT(*) FROM BOOKING WHERE ROOM_ID = :room_id) AS all_bookings
        FROM DUAL
    """, {"room_id": room_id})
    
    if deps and deps.get("active_bookings", 0) > 0:
        # Soft delete instead
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE ROOM SET STATUS = 'INACTIVE' WHERE ROOM_ID = :room_id", {"room_id": room_id})
                conn.commit()
        await log_deactivate(current_user["user_id"], "ROOM", room_id, str(old_room))
        return {"message": "Room has active bookings, deactivated instead of deleted."}
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM ROOM WHERE ROOM_ID = :room_id", {"room_id": room_id})
            conn.commit()
    await log_delete(current_user["user_id"], "ROOM", room_id, str(old_room))
    return {"message": "Room deleted successfully."}


# ============================================================
# USERS
# ============================================================

@router.get("/users")
async def list_users(current_user: Dict[str, Any] = Depends(require_admin)):
    rows = await _fetch_rows("""
        SELECT user_id, first_name, last_name, email, phone, role, status, created_at
        FROM APP_USER
        ORDER BY user_id
    """)
    return rows


@router.get("/users/{user_id}")
async def get_user(user_id: int, current_user: Dict[str, Any] = Depends(require_admin)):
    user = await _fetch_one("""
        SELECT user_id, first_name, last_name, email, phone, role, status, created_at
        FROM APP_USER
        WHERE user_id = :user_id
    """, {"user_id": user_id})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


@router.post("/users")
async def create_user(payload: AdminUserCreateRequest, current_user: Dict[str, Any] = Depends(require_admin)):
    # Check if email already exists
    existing = await _fetch_one(
        "SELECT user_id FROM APP_USER WHERE EMAIL = :email",
        {"email": payload.email}
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists.")
    
    # Hash password
    from backend.utils.authorization import hash_password
    password_hash, salt = hash_password(payload.password)
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT NVL(MAX(user_id),0) + 1 FROM APP_USER")
            user_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO APP_USER (
                    user_id, first_name, last_name, email, phone, password_hash, role, status
                ) VALUES (
                    :user_id, :first_name, :last_name, :email, :phone, :password_hash, :role, :status
                )
                """,
                {
                    "user_id": user_id,
                    "first_name": payload.first_name,
                    "last_name": payload.last_name,
                    "email": payload.email,
                    "phone": payload.phone,
                    "password_hash": password_hash,
                    "role": payload.role,
                    "status": (payload.status or "ACTIVE").upper(),
                },
            )
            conn.commit()
    await log_user_management(current_user["user_id"], "CREATE", user_id, f"User: {payload.first_name} {payload.last_name} ({payload.role})")
    return {"message": "User created successfully.", "user_id": user_id}


@router.put("/users/{user_id}")
async def update_user(user_id: int, payload: AdminUserUpdateRequest, current_user: Dict[str, Any] = Depends(require_admin)):
    old_user = await _fetch_one("SELECT user_id, first_name, last_name, email, role, status FROM APP_USER WHERE USER_ID = :user_id", {"user_id": user_id})
    if not old_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    
    # Prevent admin from demoting themselves
    if user_id == current_user["user_id"] and payload.role and payload.role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change your own admin role.")
    
    # Check if email already exists (excluding current user)
    if payload.email:
        existing = await _fetch_one(
            "SELECT user_id FROM APP_USER WHERE EMAIL = :email AND USER_ID != :user_id",
            {"email": payload.email, "user_id": user_id}
        )
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists.")
    
    allowed_fields = ["FIRST_NAME", "LAST_NAME", "EMAIL", "PHONE", "ROLE", "STATUS"]
    updates = []
    params = {"user_id": user_id}
    
    for field in allowed_fields:
        if field.lower() in payload and payload[field.lower()] is not None:
            updates.append(f"{field} = :{field.lower()}")
            params[field.lower()] = payload[field.lower()]
    
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields to update.")
    
    query = f"UPDATE APP_USER SET {', '.join(updates)} WHERE USER_ID = :user_id"
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
    
    await log_user_management(current_user["user_id"], "UPDATE", user_id, f"User: {old_user.get('first_name')} {old_user.get('last_name')}")
    return {"message": "User updated successfully."}


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, current_user: Dict[str, Any] = Depends(require_admin)):
    # Prevent admin from deleting themselves
    if user_id == current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account.")
    
    old_user = await _fetch_one("SELECT user_id, first_name, last_name, email, role, status FROM APP_USER WHERE USER_ID = :user_id", {"user_id": user_id})
    if not old_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    
    # Check for dependencies
    deps = await _fetch_one("""
        SELECT 
            (SELECT COUNT(*) FROM BOOKING WHERE USER_ID = :user_id AND STATUS IN ('PENDING', 'CONFIRMED')) AS active_bookings,
            (SELECT COUNT(*) FROM TRIP WHERE USER_ID = :user_id) AS trips,
            (SELECT COUNT(*) FROM REVIEW WHERE USER_ID = :user_id) AS reviews,
            (SELECT COUNT(*) FROM PAYMENT WHERE USER_ID = :user_id) AS payments,
            (SELECT COUNT(*) FROM HOTEL WHERE OWNER_ID = :user_id) AS owned_hotels
        FROM DUAL
    """, {"user_id": user_id})
    
    if deps and any(v > 0 for v in deps.values()):
        # Soft delete instead
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE APP_USER SET STATUS = 'INACTIVE' WHERE USER_ID = :user_id", {"user_id": user_id})
                conn.commit()
        await log_user_management(current_user["user_id"], "DEACTIVATE", user_id, f"User: {old_user.get('first_name')} {old_user.get('last_name')}")
        return {"message": "User has dependencies, deactivated instead of deleted."}
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM APP_USER WHERE USER_ID = :user_id", {"user_id": user_id})
            conn.commit()
    await log_user_management(current_user["user_id"], "DELETE", user_id, f"User: {old_user.get('first_name')} {old_user.get('last_name')}")
    return {"message": "User deleted successfully."}


# ============================================================
# TRIPS
# ============================================================

@router.get("/trips")
async def list_trips(current_user: Dict[str, Any] = Depends(require_admin)):
    rows = await _fetch_rows("""
        SELECT t.*, u.FIRST_NAME, u.LAST_NAME, u.EMAIL
        FROM TRIP t
        JOIN APP_USER u ON t.USER_ID = u.USER_ID
        ORDER BY t.TRIP_ID
    """)
    return rows


@router.get("/trips/{trip_id}")
async def get_trip(trip_id: int, current_user: Dict[str, Any] = Depends(require_admin)):
    trip = await _fetch_one("""
        SELECT t.*, u.FIRST_NAME, u.LAST_NAME, u.EMAIL
        FROM TRIP t
        JOIN APP_USER u ON t.USER_ID = u.USER_ID
        WHERE t.TRIP_ID = :trip_id
    """, {"trip_id": trip_id})
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
    return trip


@router.put("/trips/{trip_id}")
async def update_trip(trip_id: int, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_admin)):
    old_trip = await _fetch_one("SELECT * FROM TRIP WHERE TRIP_ID = :trip_id", {"trip_id": trip_id})
    if not old_trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
    
    allowed_fields = ["USER_ID", "TRIP_NAME", "START_DATE", "END_DATE", "STATUS"]
    updates = []
    params = {"trip_id": trip_id}
    
    for field in allowed_fields:
        if field.lower() in payload and payload[field.lower()] is not None:
            updates.append(f"{field} = :{field.lower()}")
            params[field.lower()] = payload[field.lower()]
    
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields to update.")
    
    query = f"UPDATE TRIP SET {', '.join(updates)} WHERE TRIP_ID = :trip_id"
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
    
    await log_update(current_user["user_id"], "TRIP", trip_id, str(old_trip), str(payload))
    return {"message": "Trip updated successfully."}


@router.delete("/trips/{trip_id}")
async def delete_trip(trip_id: int, current_user: Dict[str, Any] = Depends(require_admin)):
    old_trip = await _fetch_one("SELECT * FROM TRIP WHERE TRIP_ID = :trip_id", {"trip_id": trip_id})
    if not old_trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
    
    # Check for dependencies
    deps = await _fetch_one("""
        SELECT 
            (SELECT COUNT(*) FROM TRIP_DESTINATION WHERE TRIP_ID = :trip_id) AS destinations,
            (SELECT COUNT(*) FROM TRIP_TRAVEL WHERE TRIP_ID = :trip_id) AS travel_segments,
            (SELECT COUNT(*) FROM BOOKING WHERE TRIP_ID = :trip_id AND STATUS IN ('PENDING', 'CONFIRMED')) AS active_bookings
        FROM DUAL
    """, {"trip_id": trip_id})
    
    if deps and any(v > 0 for v in deps.values()):
        # Soft delete instead
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE TRIP SET STATUS = 'CANCELLED' WHERE TRIP_ID = :trip_id", {"trip_id": trip_id})
                conn.commit()
        await log_deactivate(current_user["user_id"], "TRIP", trip_id, str(old_trip))
        return {"message": "Trip has dependencies, cancelled instead of deleted."}
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM TRIP WHERE TRIP_ID = :trip_id", {"trip_id": trip_id})
            conn.commit()
    await log_delete(current_user["user_id"], "TRIP", trip_id, str(old_trip))
    return {"message": "Trip deleted successfully."}


# ============================================================
# BOOKINGS
# ============================================================

@router.get("/bookings")
async def list_bookings(current_user: Dict[str, Any] = Depends(require_admin)):
    rows = await _fetch_rows("""
        SELECT b.*, u.FIRST_NAME, u.LAST_NAME, u.EMAIL
        FROM BOOKING b
        JOIN APP_USER u ON b.USER_ID = u.USER_ID
        ORDER BY b.BOOKING_ID
    """)
    return rows


@router.get("/bookings/{booking_id}")
async def get_booking(booking_id: int, current_user: Dict[str, Any] = Depends(require_admin)):
    booking = await _fetch_one("""
        SELECT b.*, u.FIRST_NAME, u.LAST_NAME, u.EMAIL
        FROM BOOKING b
        JOIN APP_USER u ON b.USER_ID = u.USER_ID
        WHERE b.BOOKING_ID = :booking_id
    """, {"booking_id": booking_id})
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")
    return booking


@router.put("/bookings/{booking_id}")
async def update_booking(booking_id: int, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_admin)):
    old_booking = await _fetch_one("SELECT * FROM BOOKING WHERE BOOKING_ID = :booking_id", {"booking_id": booking_id})
    if not old_booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")
    
    allowed_fields = ["USER_ID", "TRIP_ID", "BOOKING_TYPE", "BOOKING_DATE", "TOTAL_AMOUNT", "STATUS"]
    updates = []
    params = {"booking_id": booking_id}
    
    for field in allowed_fields:
        if field.lower() in payload and payload[field.lower()] is not None:
            updates.append(f"{field} = :{field.lower()}")
            params[field.lower()] = payload[field.lower()]
    
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields to update.")
    
    query = f"UPDATE BOOKING SET {', '.join(updates)} WHERE BOOKING_ID = :booking_id"
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
    
    await log_update(current_user["user_id"], "BOOKING", booking_id, str(old_booking), str(payload))
    return {"message": "Booking updated successfully."}


@router.delete("/bookings/{booking_id}")
async def delete_booking(booking_id: int, current_user: Dict[str, Any] = Depends(require_admin)):
    old_booking = await _fetch_one("SELECT * FROM BOOKING WHERE BOOKING_ID = :booking_id", {"booking_id": booking_id})
    if not old_booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")
    
    # Check for dependencies
    deps = await _fetch_one("""
        SELECT 
            (SELECT COUNT(*) FROM PAYMENT WHERE BOOKING_ID = :booking_id) AS payments
        FROM DUAL
    """, {"booking_id": booking_id})
    
    if deps and deps.get("payments", 0) > 0:
        # Soft delete instead
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE BOOKING SET STATUS = 'CANCELLED' WHERE BOOKING_ID = :booking_id", {"booking_id": booking_id})
                conn.commit()
        await log_deactivate(current_user["user_id"], "BOOKING", booking_id, str(old_booking))
        return {"message": "Booking has payments, cancelled instead of deleted."}
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM BOOKING WHERE BOOKING_ID = :booking_id", {"booking_id": booking_id})
            conn.commit()
    await log_delete(current_user["user_id"], "BOOKING", booking_id, str(old_booking))
    return {"message": "Booking deleted successfully."}


# ============================================================
# REPORTS
# ============================================================

@router.get("/reports")
async def list_reports(current_user: Dict[str, Any] = Depends(require_admin)):
    rows = await _fetch_rows("""
        SELECT r.*, u.FIRST_NAME, u.LAST_NAME, u.EMAIL
        FROM REPORT r
        JOIN APP_USER u ON r.USER_ID = u.USER_ID
        ORDER BY r.REPORT_ID
    """)
    return rows


@router.get("/reports/{report_id}")
async def get_report(report_id: int, current_user: Dict[str, Any] = Depends(require_admin)):
    report = await _fetch_one("""
        SELECT r.*, u.FIRST_NAME, u.LAST_NAME, u.EMAIL
        FROM REPORT r
        JOIN APP_USER u ON r.USER_ID = u.USER_ID
        WHERE r.REPORT_ID = :report_id
    """, {"report_id": report_id})
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    return report


@router.post("/reports")
async def create_report(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_admin)):
    user_id = payload.get("user_id")
    report_type = str(payload.get("report_type") or "").strip()
    title = str(payload.get("title") or "").strip()
    content = str(payload.get("content") or "").strip()
    
    if not user_id or not report_type or not title or not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id, report_type, title, and content are required.")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT NVL(MAX(report_id),0) + 1 FROM REPORT")
            report_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO REPORT (
                    report_id, user_id, report_type, title, content, status
                ) VALUES (
                    :report_id, :user_id, :report_type, :title, :content, :status
                )
                """,
                {
                    "report_id": report_id,
                    "user_id": user_id,
                    "report_type": report_type,
                    "title": title,
                    "content": content,
                    "status": (payload.get("status") or "PENDING").upper(),
                },
            )
            conn.commit()
    await log_create(current_user["user_id"], "REPORT", report_id, f"Report: {title} ({report_type})")
    return {"message": "Report created successfully.", "report_id": report_id}


@router.put("/reports/{report_id}")
async def update_report(report_id: int, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_admin)):
    old_report = await _fetch_one("SELECT * FROM REPORT WHERE REPORT_ID = :report_id", {"report_id": report_id})
    if not old_report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    
    allowed_fields = ["USER_ID", "REPORT_TYPE", "TITLE", "CONTENT", "STATUS"]
    updates = []
    params = {"report_id": report_id}
    
    for field in allowed_fields:
        if field.lower() in payload and payload[field.lower()] is not None:
            updates.append(f"{field} = :{field.lower()}")
            params[field.lower()] = payload[field.lower()]
    
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields to update.")
    
    query = f"UPDATE REPORT SET {', '.join(updates)} WHERE REPORT_ID = :report_id"
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
    
    await log_update(current_user["user_id"], "REPORT", report_id, str(old_report), str(payload))
    return {"message": "Report updated successfully."}


@router.delete("/reports/{report_id}")
async def delete_report(report_id: int, current_user: Dict[str, Any] = Depends(require_admin)):
    old_report = await _fetch_one("SELECT * FROM REPORT WHERE REPORT_ID = :report_id", {"report_id": report_id})
    if not old_report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM REPORT WHERE REPORT_ID = :report_id", {"report_id": report_id})
            conn.commit()
    await log_delete(current_user["user_id"], "REPORT", report_id, str(old_report))
    return {"message": "Report deleted successfully."}


# ============================================================
# AUDIT LOGS
# ============================================================

@router.get("/audit-logs")
async def list_audit_logs(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    entity_name: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    current_user: Dict[str, Any] = Depends(require_admin)
):
    conditions = []
    params = {"limit": limit, "offset": offset}
    
    if entity_name:
        conditions.append("ENTITY_NAME = :entity_name")
        params["entity_name"] = entity_name
    if action:
        conditions.append("ACTION = :action")
        params["action"] = action
    if user_id:
        conditions.append("USER_ID = :user_id")
        params["user_id"] = user_id
    
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    query = f"""
        SELECT * FROM AUDIT_LOG
        {where_clause}
        ORDER BY ACTION_TIMESTAMP DESC
        OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
    """
    
    rows = await _fetch_rows(query, params)
    return rows


@router.get("/audit-logs/{log_id}")
async def get_audit_log(log_id: int, current_user: Dict[str, Any] = Depends(require_admin)):
    log = await _fetch_one("SELECT * FROM AUDIT_LOG WHERE AUDIT_ID = :log_id", {"log_id": log_id})
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit log not found.")
    return log
