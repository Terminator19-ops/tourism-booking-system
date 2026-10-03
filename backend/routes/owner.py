from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from backend.database.connection import get_connection
from backend.schemas.authentication import (
    OwnerBookingResponse,
    OwnerHotelResponse,
    OwnerRoomResponse,
    OwnerTripResponse,
    RoomCreateRequest,
    RoomUpdateRequest,
)
from backend.utils.audit import log_create, log_update, log_deactivate
from backend.utils.authorization import (
    get_current_user,
    get_owner_hotel_ids,
    get_owner_room_ids,
    require_owner,
    verify_hotel_ownership,
    verify_room_ownership,
)

router = APIRouter(prefix="/api/owner")


def _convert_lob(value: Any) -> Any:
    """Convert Oracle LOB objects to strings for JSON serialization."""
    if hasattr(value, 'read'):
        return value.read()
    # Convert datetime objects to ISO format strings
    if hasattr(value, 'isoformat'):
        return value.isoformat()
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


async def _fetch_one(query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or {})
            columns = [col[0].lower() for col in cur.description]
            row = cur.fetchone()
            if not row:
                return None
            return {columns[i]: _convert_lob(row[i]) for i in range(len(columns))}


async def _execute(query: str, params: Optional[Dict[str, Any]] = None) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or {})
            conn.commit()


# ============================================================
# OWNER HOTEL MANAGEMENT
# ============================================================

@router.get("/hotels", response_model=List[OwnerHotelResponse])
async def list_owner_hotels(current_user: Dict[str, Any] = Depends(require_owner)):
    """List all hotels owned by the current owner."""
    owner_id = current_user["user_id"]
    rows = await _fetch_rows("""
        SELECT h.HOTEL_ID, h.NAME, h.DESCRIPTION, h.ADDRESS, h.CONTACT_NUMBER,
               h.EMAIL, h.STAR_RATING, h.STATUS, h.DESTINATION_ID,
               d.NAME AS DESTINATION_NAME,
               (SELECT COUNT(*) FROM ROOM WHERE HOTEL_ID = h.HOTEL_ID) AS ROOM_COUNT
        FROM HOTEL h
        JOIN DESTINATION d ON h.DESTINATION_ID = d.DESTINATION_ID
        WHERE h.OWNER_ID = :owner_id
        ORDER BY h.NAME
    """, {"owner_id": owner_id})
    return rows


@router.post("/hotels", response_model=OwnerHotelResponse)
async def create_hotel(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_owner)):
    """Create a new hotel for the current owner."""
    owner_id = current_user["user_id"]
    
    name = str(payload.get("name") or "").strip()
    destination_id = payload.get("destination_id")
    address = str(payload.get("address") or "").strip()
    
    if not name or not destination_id or not address:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                          detail="name, destination_id and address are required.")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT NVL(MAX(HOTEL_ID),0) + 1 FROM HOTEL")
            hotel_id = cur.fetchone()[0]
            
            cur.execute(
                """
                INSERT INTO HOTEL (
                    HOTEL_ID, OWNER_ID, DESTINATION_ID, NAME, DESCRIPTION, ADDRESS,
                    CONTACT_NUMBER, EMAIL, STAR_RATING, STATUS
                ) VALUES (
                    :hotel_id, :owner_id, :destination_id, :name, :description,
                    :address, :contact_number, :email, :star_rating, :status
                )
                """,
                {
                    "hotel_id": hotel_id,
                    "owner_id": owner_id,
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
    
    await log_create(owner_id, "HOTEL", hotel_id, f"Hotel: {name}")
    
    hotel = await _fetch_one("""
        SELECT h.HOTEL_ID, h.NAME, h.DESCRIPTION, h.ADDRESS, h.CONTACT_NUMBER,
               h.EMAIL, h.STAR_RATING, h.STATUS, h.DESTINATION_ID,
               d.NAME AS DESTINATION_NAME,
               (SELECT COUNT(*) FROM ROOM WHERE HOTEL_ID = h.HOTEL_ID) AS ROOM_COUNT
        FROM HOTEL h
        JOIN DESTINATION d ON h.DESTINATION_ID = d.DESTINATION_ID
        WHERE h.HOTEL_ID = :hotel_id
    """, {"hotel_id": hotel_id})
    
    return OwnerHotelResponse(**hotel)


@router.get("/hotels/{hotel_id}", response_model=OwnerHotelResponse)
async def get_owner_hotel(hotel_id: int, current_user: Dict[str, Any] = Depends(require_owner)):
    """Get a specific hotel owned by the current owner."""
    owner_id = current_user["user_id"]
    
    if not await verify_hotel_ownership(hotel_id, owner_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, 
                          detail="You can only access your own hotels.")
    
    hotel = await _fetch_one("""
        SELECT h.HOTEL_ID, h.NAME, h.DESCRIPTION, h.ADDRESS, h.CONTACT_NUMBER,
               h.EMAIL, h.STAR_RATING, h.STATUS, h.DESTINATION_ID,
               d.NAME AS DESTINATION_NAME,
               (SELECT COUNT(*) FROM ROOM WHERE HOTEL_ID = h.HOTEL_ID) AS ROOM_COUNT
        FROM HOTEL h
        JOIN DESTINATION d ON h.DESTINATION_ID = d.DESTINATION_ID
        WHERE h.HOTEL_ID = :hotel_id
    """, {"hotel_id": hotel_id})
    
    if not hotel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found.")
    
    return OwnerHotelResponse(**hotel)


@router.put("/hotels/{hotel_id}", response_model=OwnerHotelResponse)
async def update_hotel(hotel_id: int, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_owner)):
    """Update a hotel owned by the current owner."""
    owner_id = current_user["user_id"]
    
    if not await verify_hotel_ownership(hotel_id, owner_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, 
                          detail="You can only update your own hotels.")
    
    # Get current values for audit
    old_hotel = await _fetch_one("SELECT * FROM HOTEL WHERE HOTEL_ID = :hotel_id", {"hotel_id": hotel_id})
    
    # Build update query dynamically
    allowed_fields = ["NAME", "DESCRIPTION", "ADDRESS", "CONTACT_NUMBER", "EMAIL", "STAR_RATING", "STATUS", "DESTINATION_ID"]
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
    
    await log_update(owner_id, "HOTEL", hotel_id, str(old_hotel), str(payload))
    
    hotel = await _fetch_one("""
        SELECT h.HOTEL_ID, h.NAME, h.DESCRIPTION, h.ADDRESS, h.CONTACT_NUMBER,
               h.EMAIL, h.STAR_RATING, h.STATUS, h.DESTINATION_ID,
               d.NAME AS DESTINATION_NAME,
               (SELECT COUNT(*) FROM ROOM WHERE HOTEL_ID = h.HOTEL_ID) AS ROOM_COUNT
        FROM HOTEL h
        JOIN DESTINATION d ON h.DESTINATION_ID = d.DESTINATION_ID
        WHERE h.HOTEL_ID = :hotel_id
    """, {"hotel_id": hotel_id})
    
    return OwnerHotelResponse(**hotel)


@router.delete("/hotels/{hotel_id}")
async def deactivate_hotel(hotel_id: int, current_user: Dict[str, Any] = Depends(require_owner)):
    """Deactivate (soft delete) a hotel owned by the current owner."""
    owner_id = current_user["user_id"]
    
    if not await verify_hotel_ownership(hotel_id, owner_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, 
                          detail="You can only deactivate your own hotels.")
    
    # Check for active bookings
    active_bookings = await _fetch_one("""
        SELECT COUNT(*) as cnt FROM BOOKING b
        JOIN HOTEL_BOOKING hb ON b.BOOKING_ID = hb.BOOKING_ID
        JOIN ROOM r ON hb.ROOM_ID = r.ROOM_ID
        WHERE r.HOTEL_ID = :hotel_id AND b.STATUS NOT IN ('CANCELLED', 'COMPLETED')
    """, {"hotel_id": hotel_id})
    
    if active_bookings and active_bookings.get('cnt', 0) > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                          detail="Cannot deactivate hotel with active bookings. Cancel bookings first.")
    
    old_hotel = await _fetch_one("SELECT * FROM HOTEL WHERE HOTEL_ID = :hotel_id", {"hotel_id": hotel_id})
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE HOTEL SET STATUS = 'INACTIVE' WHERE HOTEL_ID = :hotel_id",
                {"hotel_id": hotel_id}
            )
            # Also deactivate rooms
            cur.execute(
                "UPDATE ROOM SET STATUS = 'MAINTENANCE' WHERE HOTEL_ID = :hotel_id",
                {"hotel_id": hotel_id}
            )
            conn.commit()
    
    await log_deactivate(owner_id, "HOTEL", hotel_id, str(old_hotel))
    return {"message": "Hotel deactivated successfully."}


# ============================================================
# OWNER ROOM MANAGEMENT
# ============================================================

@router.get("/hotels/{hotel_id}/rooms", response_model=List[OwnerRoomResponse])
async def list_hotel_rooms(hotel_id: int, current_user: Dict[str, Any] = Depends(require_owner)):
    """List all rooms for a hotel owned by the current owner."""
    owner_id = current_user["user_id"]
    
    if not await verify_hotel_ownership(hotel_id, owner_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, 
                          detail="You can only access rooms in your own hotels.")
    
    rows = await _fetch_rows("""
        SELECT r.ROOM_ID, r.HOTEL_ID, h.NAME AS HOTEL_NAME, r.ROOM_NUMBER, r.ROOM_TYPE,
               r.CAPACITY, r.PRICE_PER_NIGHT, r.STATUS
        FROM ROOM r
        JOIN HOTEL h ON r.HOTEL_ID = h.HOTEL_ID
        WHERE r.HOTEL_ID = :hotel_id
        ORDER BY r.ROOM_NUMBER
    """, {"hotel_id": hotel_id})
    return rows


@router.post("/hotels/{hotel_id}/rooms", response_model=OwnerRoomResponse)
async def create_room(hotel_id: int, payload: RoomCreateRequest, current_user: Dict[str, Any] = Depends(require_owner)):
    """Add a room to a hotel owned by the current owner."""
    owner_id = current_user["user_id"]
    
    if not await verify_hotel_ownership(hotel_id, owner_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, 
                          detail="You can only add rooms to your own hotels.")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT NVL(MAX(ROOM_ID),0) + 1 FROM ROOM")
            room_id = cur.fetchone()[0]
            
            cur.execute(
                """
                INSERT INTO ROOM (
                    ROOM_ID, HOTEL_ID, ROOM_NUMBER, ROOM_TYPE, CAPACITY, PRICE_PER_NIGHT, STATUS
                ) VALUES (
                    :room_id, :hotel_id, :room_number, :room_type, :capacity, :price_per_night, :status
                )
                """,
                {
                    "room_id": room_id,
                    "hotel_id": hotel_id,
                    "room_number": payload.room_number.strip(),
                    "room_type": payload.room_type.strip(),
                    "capacity": payload.capacity,
                    "price_per_night": payload.price_per_night,
                    "status": payload.status.upper(),
                },
            )
            conn.commit()
    
    await log_create(owner_id, "ROOM", room_id, f"Hotel: {hotel_id}, Room: {payload.room_number}")
    
    room = await _fetch_one("""
        SELECT r.ROOM_ID, r.HOTEL_ID, h.NAME AS HOTEL_NAME, r.ROOM_NUMBER, r.ROOM_TYPE,
               r.CAPACITY, r.PRICE_PER_NIGHT, r.STATUS
        FROM ROOM r
        JOIN HOTEL h ON r.HOTEL_ID = h.HOTEL_ID
        WHERE r.ROOM_ID = :room_id
    """, {"room_id": room_id})
    
    return OwnerRoomResponse(**room)


@router.put("/hotels/{hotel_id}/rooms/{room_id}", response_model=OwnerRoomResponse)
async def update_room(hotel_id: int, room_id: int, payload: RoomUpdateRequest, current_user: Dict[str, Any] = Depends(require_owner)):
    """Update a room in a hotel owned by the current owner."""
    owner_id = current_user["user_id"]
    
    if not await verify_hotel_ownership(hotel_id, owner_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, 
                          detail="You can only update rooms in your own hotels.")
    
    if not await verify_room_ownership(room_id, owner_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found in your hotels.")
    
    old_room = await _fetch_one("SELECT * FROM ROOM WHERE ROOM_ID = :room_id", {"room_id": room_id})
    
    allowed_fields = ["ROOM_NUMBER", "ROOM_TYPE", "CAPACITY", "PRICE_PER_NIGHT", "STATUS"]
    updates = []
    params = {"room_id": room_id}
    
    for field in allowed_fields:
        if field.lower() in payload.model_dump(exclude_unset=True):
            value = getattr(payload, field.lower())
            if value is not None:
                updates.append(f"{field} = :{field.lower()}")
                params[field.lower()] = value
    
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields to update.")
    
    query = f"UPDATE ROOM SET {', '.join(updates)} WHERE ROOM_ID = :room_id"
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
    
    await log_update(owner_id, "ROOM", room_id, str(old_room), str(payload.model_dump(exclude_unset=True)))
    
    room = await _fetch_one("""
        SELECT r.ROOM_ID, r.HOTEL_ID, h.NAME AS HOTEL_NAME, r.ROOM_NUMBER, r.ROOM_TYPE,
               r.CAPACITY, r.PRICE_PER_NIGHT, r.STATUS
        FROM ROOM r
        JOIN HOTEL h ON r.HOTEL_ID = h.HOTEL_ID
        WHERE r.ROOM_ID = :room_id
    """, {"room_id": room_id})
    
    return OwnerRoomResponse(**room)


@router.delete("/hotels/{hotel_id}/rooms/{room_id}")
async def deactivate_room(hotel_id: int, room_id: int, current_user: Dict[str, Any] = Depends(require_owner)):
    """Deactivate (soft delete) a room in a hotel owned by the current owner."""
    owner_id = current_user["user_id"]
    
    if not await verify_hotel_ownership(hotel_id, owner_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, 
                          detail="You can only deactivate rooms in your own hotels.")
    
    if not await verify_room_ownership(room_id, owner_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found in your hotels.")
    
    # Check for active bookings
    active_bookings = await _fetch_one("""
        SELECT COUNT(*) as cnt FROM BOOKING b
        JOIN HOTEL_BOOKING hb ON b.BOOKING_ID = hb.BOOKING_ID
        WHERE hb.ROOM_ID = :room_id AND b.STATUS NOT IN ('CANCELLED', 'COMPLETED')
    """, {"room_id": room_id})
    
    if active_bookings and active_bookings.get('cnt', 0) > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                          detail="Cannot deactivate room with active bookings. Cancel bookings first.")
    
    old_room = await _fetch_one("SELECT * FROM ROOM WHERE ROOM_ID = :room_id", {"room_id": room_id})
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ROOM SET STATUS = 'MAINTENANCE' WHERE ROOM_ID = :room_id",
                {"room_id": room_id}
            )
            conn.commit()
    
    await log_deactivate(owner_id, "ROOM", room_id, str(old_room))
    return {"message": "Room deactivated successfully."}


# ============================================================
# OWNER BOOKINGS VIEW (bookings for own hotels/rooms)
# ============================================================

@router.get("/bookings", response_model=List[OwnerBookingResponse])
async def list_owner_bookings(current_user: Dict[str, Any] = Depends(require_owner)):
    """List all bookings for hotels/rooms owned by the current owner."""
    owner_id = current_user["user_id"]
    
    hotel_ids = await get_owner_hotel_ids(owner_id)
    if not hotel_ids:
        return []
    
    placeholders = ",".join([f":hid{i}" for i in range(len(hotel_ids))])
    params = {f"hid{i}": hid for i, hid in enumerate(hotel_ids)}
    
    rows = await _fetch_rows(f"""
        SELECT b.BOOKING_ID, b.BOOKING_TYPE, b.BOOKING_DATE, b.TOTAL_AMOUNT, b.STATUS,
               u.FIRST_NAME || ' ' || u.LAST_NAME AS CUSTOMER_NAME,
               u.EMAIL AS CUSTOMER_EMAIL,
               h.NAME AS HOTEL_NAME,
               r.ROOM_NUMBER,
               hb.CHECK_IN_DATE, hb.CHECK_OUT_DATE
        FROM BOOKING b
        JOIN APP_USER u ON b.USER_ID = u.USER_ID
        JOIN HOTEL_BOOKING hb ON b.BOOKING_ID = hb.BOOKING_ID
        JOIN ROOM r ON hb.ROOM_ID = r.ROOM_ID
        JOIN HOTEL h ON r.HOTEL_ID = h.HOTEL_ID
        WHERE h.HOTEL_ID IN ({placeholders})
        ORDER BY b.BOOKING_DATE DESC
    """, params)
    return rows


@router.get("/bookings/{booking_id}", response_model=OwnerBookingResponse)
async def get_owner_booking(booking_id: int, current_user: Dict[str, Any] = Depends(require_owner)):
    """Get a specific booking for a hotel/room owned by the current owner."""
    owner_id = current_user["user_id"]
    
    hotel_ids = await get_owner_hotel_ids(owner_id)
    if not hotel_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")
    
    placeholders = ",".join([f":hid{i}" for i in range(len(hotel_ids))])
    params = {f"hid{i}": hid for i, hid in enumerate(hotel_ids)}
    params["booking_id"] = booking_id
    
    booking = await _fetch_one(f"""
        SELECT b.BOOKING_ID, b.BOOKING_TYPE, b.BOOKING_DATE, b.TOTAL_AMOUNT, b.STATUS,
               u.FIRST_NAME || ' ' || u.LAST_NAME AS CUSTOMER_NAME,
               u.EMAIL AS CUSTOMER_EMAIL,
               h.NAME AS HOTEL_NAME,
               r.ROOM_NUMBER,
               hb.CHECK_IN_DATE, hb.CHECK_OUT_DATE
        FROM BOOKING b
        JOIN APP_USER u ON b.USER_ID = u.USER_ID
        JOIN HOTEL_BOOKING hb ON b.BOOKING_ID = hb.BOOKING_ID
        JOIN ROOM r ON hb.ROOM_ID = r.ROOM_ID
        JOIN HOTEL h ON r.HOTEL_ID = h.HOTEL_ID
        WHERE b.BOOKING_ID = :booking_id AND h.HOTEL_ID IN ({placeholders})
    """, params)
    
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")
    
    return OwnerBookingResponse(**booking)


# ============================================================
# OWNER TRIPS VIEW (trips with bookings for own hotels)
# ============================================================

@router.get("/trips", response_model=List[OwnerTripResponse])
async def list_owner_trips(current_user: Dict[str, Any] = Depends(require_owner)):
    """List all customer trips that have bookings for hotels owned by the current owner."""
    owner_id = current_user["user_id"]
    
    hotel_ids = await get_owner_hotel_ids(owner_id)
    if not hotel_ids:
        return []
    
    placeholders = ",".join([f":hid{i}" for i in range(len(hotel_ids))])
    params = {f"hid{i}": hid for i, hid in enumerate(hotel_ids)}
    
    # Get unique trips that have bookings for owner's hotels
    trip_rows = await _fetch_rows(f"""
        SELECT DISTINCT t.TRIP_ID, t.TRIP_NAME, t.START_DATE, t.END_DATE, t.STATUS,
               u.FIRST_NAME || ' ' || u.LAST_NAME AS CUSTOMER_NAME,
               u.EMAIL AS CUSTOMER_EMAIL
        FROM TRIP t
        JOIN APP_USER u ON t.USER_ID = u.USER_ID
        JOIN BOOKING b ON t.TRIP_ID = b.TRIP_ID
        JOIN HOTEL_BOOKING hb ON b.BOOKING_ID = hb.BOOKING_ID
        JOIN ROOM r ON hb.ROOM_ID = r.ROOM_ID
        JOIN HOTEL h ON r.HOTEL_ID = h.HOTEL_ID
        WHERE h.HOTEL_ID IN ({placeholders})
        ORDER BY t.START_DATE DESC
    """, params)
    
    # Add bookings for each trip (only those for owner's hotels)
    for trip in trip_rows:
        bookings = await _fetch_rows(f"""
            SELECT b.BOOKING_ID, b.BOOKING_TYPE, b.BOOKING_DATE, b.TOTAL_AMOUNT, b.STATUS,
                   h.NAME AS HOTEL_NAME, r.ROOM_NUMBER,
                   hb.CHECK_IN_DATE, hb.CHECK_OUT_DATE
            FROM BOOKING b
            JOIN HOTEL_BOOKING hb ON b.BOOKING_ID = hb.BOOKING_ID
            JOIN ROOM r ON hb.ROOM_ID = r.ROOM_ID
            JOIN HOTEL h ON r.HOTEL_ID = h.HOTEL_ID
            WHERE b.TRIP_ID = :trip_id AND h.HOTEL_ID IN ({placeholders})
            ORDER BY b.BOOKING_DATE
        """, {**params, "trip_id": trip["trip_id"]})
        trip["bookings"] = bookings
    
    return trip_rows


@router.get("/trips/{trip_id}", response_model=OwnerTripResponse)
async def get_owner_trip(trip_id: int, current_user: Dict[str, Any] = Depends(require_owner)):
    """Get a specific trip that has bookings for hotels owned by the current owner."""
    owner_id = current_user["user_id"]
    
    hotel_ids = await get_owner_hotel_ids(owner_id)
    if not hotel_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
    
    placeholders = ",".join([f":hid{i}" for i in range(len(hotel_ids))])
    params = {f"hid{i}": hid for i, hid in enumerate(hotel_ids)}
    params["trip_id"] = trip_id
    
    trip = await _fetch_one(f"""
        SELECT t.TRIP_ID, t.TRIP_NAME, t.START_DATE, t.END_DATE, t.STATUS,
               u.FIRST_NAME || ' ' || u.LAST_NAME AS CUSTOMER_NAME,
               u.EMAIL AS CUSTOMER_EMAIL
        FROM TRIP t
        JOIN APP_USER u ON t.USER_ID = u.USER_ID
        JOIN BOOKING b ON t.TRIP_ID = b.TRIP_ID
        JOIN HOTEL_BOOKING hb ON b.BOOKING_ID = hb.BOOKING_ID
        JOIN ROOM r ON hb.ROOM_ID = r.ROOM_ID
        JOIN HOTEL h ON r.HOTEL_ID = h.HOTEL_ID
        WHERE t.TRIP_ID = :trip_id AND h.HOTEL_ID IN ({placeholders})
    """, params)
    
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
    
    bookings = await _fetch_rows(f"""
        SELECT b.BOOKING_ID, b.BOOKING_TYPE, b.BOOKING_DATE, b.TOTAL_AMOUNT, b.STATUS,
               h.NAME AS HOTEL_NAME, r.ROOM_NUMBER,
               hb.CHECK_IN_DATE, hb.CHECK_OUT_DATE
        FROM BOOKING b
        JOIN HOTEL_BOOKING hb ON b.BOOKING_ID = hb.BOOKING_ID
        JOIN ROOM r ON hb.ROOM_ID = r.ROOM_ID
        JOIN HOTEL h ON r.HOTEL_ID = h.HOTEL_ID
        WHERE b.TRIP_ID = :trip_id AND h.HOTEL_ID IN ({placeholders})
        ORDER BY b.BOOKING_DATE
    """, params)
    
    trip["bookings"] = bookings
    return OwnerTripResponse(**trip)