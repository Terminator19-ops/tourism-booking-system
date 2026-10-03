from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from backend.database.connection import get_connection
from backend.schemas.authentication import (
    BookingCreateRequest,
    BookingResponse,
    PaymentCreateRequest,
    PaymentResponse,
    ReviewCreateRequest,
    ReviewResponse,
    TripCreateRequest,
    TripResponse,
)
from backend.utils.audit import log_create
from backend.utils.authorization import get_current_user, require_customer

router = APIRouter(prefix="/api/customer")


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
# PUBLIC DATA ENDPOINTS (available to all authenticated users)
# ============================================================

@router.get("/hotels")
async def list_hotels(current_user: Dict[str, Any] = Depends(get_current_user)):
    """List all active hotels with basic info."""
    rows = await _fetch_rows("""
        SELECT h.HOTEL_ID, h.NAME, h.ADDRESS, h.STAR_RATING, h.STATUS,
               d.DESTINATION_ID, d.NAME AS DESTINATION_NAME, d.CITY, d.COUNTRY
        FROM HOTEL h
        JOIN DESTINATION d ON h.DESTINATION_ID = d.DESTINATION_ID
        WHERE h.STATUS = 'ACTIVE' AND d.STATUS = 'ACTIVE'
        ORDER BY h.NAME
    """)
    return rows


@router.get("/hotels/{hotel_id}")
async def get_hotel_details(hotel_id: int, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get hotel details with available rooms."""
    hotel = await _fetch_one("""
        SELECT h.HOTEL_ID, h.NAME, h.DESCRIPTION, h.ADDRESS, h.CONTACT_NUMBER,
               h.EMAIL, h.STAR_RATING, h.STATUS,
               d.DESTINATION_ID, d.NAME AS DESTINATION_NAME, d.CITY, d.COUNTRY
        FROM HOTEL h
        JOIN DESTINATION d ON h.DESTINATION_ID = d.DESTINATION_ID
        WHERE h.HOTEL_ID = :hotel_id AND h.STATUS = 'ACTIVE'
    """, {"hotel_id": hotel_id})
    
    if not hotel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found.")
    
    rooms = await _fetch_rows("""
        SELECT ROOM_ID, ROOM_NUMBER, ROOM_TYPE, CAPACITY, PRICE_PER_NIGHT, STATUS
        FROM ROOM
        WHERE HOTEL_ID = :hotel_id AND STATUS = 'AVAILABLE'
        ORDER BY ROOM_NUMBER
    """, {"hotel_id": hotel_id})
    
    hotel["rooms"] = rooms
    return hotel


@router.get("/activities")
async def list_activities(current_user: Dict[str, Any] = Depends(get_current_user)):
    """List all active activities."""
    rows = await _fetch_rows("""
        SELECT a.ACTIVITY_ID, a.NAME, a.DESCRIPTION, a.CATEGORY, a.DURATION_HOURS,
               a.PRICE, a.CAPACITY, a.STATUS,
               d.DESTINATION_ID, d.NAME AS DESTINATION_NAME, d.CITY, d.COUNTRY
        FROM ACTIVITY a
        JOIN DESTINATION d ON a.DESTINATION_ID = d.DESTINATION_ID
        WHERE a.STATUS = 'ACTIVE' AND d.STATUS = 'ACTIVE'
        ORDER BY d.NAME, a.NAME
    """)
    return rows


@router.get("/tour-packages")
async def list_tour_packages(current_user: Dict[str, Any] = Depends(get_current_user)):
    """List all active tour packages."""
    rows = await _fetch_rows("""
        SELECT PACKAGE_ID, NAME, DESCRIPTION, DURATION_DAYS, PRICE, MAX_CAPACITY, STATUS
        FROM TOUR_PACKAGE
        WHERE STATUS = 'ACTIVE'
        ORDER BY NAME
    """)
    
    # Add destinations and activities for each package
    for pkg in rows:
        destinations = await _fetch_rows("""
            SELECT d.DESTINATION_ID, d.NAME, pd.VISIT_ORDER, pd.DAYS
            FROM PACKAGE_DESTINATION pd
            JOIN DESTINATION d ON pd.DESTINATION_ID = d.DESTINATION_ID
            WHERE pd.PACKAGE_ID = :package_id
            ORDER BY pd.VISIT_ORDER
        """, {"package_id": pkg["package_id"]})
        
        activities = await _fetch_rows("""
            SELECT a.ACTIVITY_ID, a.NAME, pa.ACTIVITY_DAY
            FROM PACKAGE_ACTIVITY pa
            JOIN ACTIVITY a ON pa.ACTIVITY_ID = a.ACTIVITY_ID
            WHERE pa.PACKAGE_ID = :package_id
            ORDER BY pa.ACTIVITY_DAY
        """, {"package_id": pkg["package_id"]})
        
        pkg["destinations"] = destinations
        pkg["activities"] = activities
    
    return rows


@router.get("/travel")
async def list_travel_segments(current_user: Dict[str, Any] = Depends(get_current_user)):
    """List all scheduled travel segments."""
    rows = await _fetch_rows("""
        SELECT ts.TRAVEL_SEGMENT_ID, ts.TRANSPORT_TYPE, ts.OPERATOR_NAME,
               ts.DEPARTURE_TIME, ts.ARRIVAL_TIME, ts.PRICE, ts.CAPACITY, ts.STATUS,
               od.NAME AS ORIGIN_NAME, od.CITY AS ORIGIN_CITY,
               dd.NAME AS DESTINATION_NAME, dd.CITY AS DESTINATION_CITY
        FROM TRAVEL_SEGMENT ts
        JOIN DESTINATION od ON ts.ORIGIN_DESTINATION_ID = od.DESTINATION_ID
        JOIN DESTINATION dd ON ts.DESTINATION_DESTINATION_ID = dd.DESTINATION_ID
        WHERE ts.STATUS = 'SCHEDULED' AND od.STATUS = 'ACTIVE' AND dd.STATUS = 'ACTIVE'
        ORDER BY ts.DEPARTURE_TIME
    """)
    return rows


# ============================================================
# CUSTOMER TRIP MANAGEMENT
# ============================================================

@router.post("/trips", response_model=TripResponse)
async def create_trip(payload: TripCreateRequest, current_user: Dict[str, Any] = Depends(require_customer)):
    """Create a new trip for the customer."""
    user_id = current_user["user_id"]
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            trip_id = cur.var(int)
            cur.execute(
                """
                BEGIN
                    sp_create_trip(:user_id, :trip_name, TO_DATE(:start_date, 'YYYY-MM-DD'), 
                                 TO_DATE(:end_date, 'YYYY-MM-DD'), :trip_id);
                END;
                """,
                {
                    "user_id": user_id,
                    "trip_name": payload.trip_name.strip(),
                    "start_date": payload.start_date,
                    "end_date": payload.end_date,
                    "trip_id": trip_id,
                },
            )
            created_trip_id = trip_id.getvalue()
            conn.commit()
    
    await log_create(user_id, "TRIP", created_trip_id, f"Trip: {payload.trip_name}")
    
    return TripResponse(
        trip_id=created_trip_id,
        trip_name=payload.trip_name,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status="PLANNED",
        destinations=[],
        bookings=[]
    )


@router.get("/trips")
async def list_trips(current_user: Dict[str, Any] = Depends(require_customer)):
    """List all trips for the current customer."""
    user_id = current_user["user_id"]
    rows = await _fetch_rows("""
        SELECT TRIP_ID, TRIP_NAME, START_DATE, END_DATE, STATUS, CREATED_AT
        FROM TRIP
        WHERE USER_ID = :user_id
        ORDER BY CREATED_AT DESC
    """, {"user_id": user_id})
    
    # Add destinations and bookings for each trip
    for trip in rows:
        destinations = await _fetch_rows("""
            SELECT d.NAME, td.VISIT_ORDER, td.ARRIVAL_DATE, td.DEPARTURE_DATE
            FROM TRIP_DESTINATION td
            JOIN DESTINATION d ON td.DESTINATION_ID = d.DESTINATION_ID
            WHERE td.TRIP_ID = :trip_id
            ORDER BY td.VISIT_ORDER
        """, {"trip_id": trip["trip_id"]})
        
        bookings = await _fetch_rows("""
            SELECT b.BOOKING_ID, b.BOOKING_TYPE, b.TOTAL_AMOUNT, b.STATUS
            FROM BOOKING b
            WHERE b.TRIP_ID = :trip_id
            ORDER BY b.BOOKING_DATE
        """, {"trip_id": trip["trip_id"]})
        
        trip["destinations"] = destinations
        trip["bookings"] = bookings
    
    return rows


@router.get("/trips/{trip_id}")
async def get_trip_details(trip_id: int, current_user: Dict[str, Any] = Depends(require_customer)):
    """Get detailed trip information."""
    user_id = current_user["user_id"]
    
    trip = await _fetch_one("""
        SELECT TRIP_ID, TRIP_NAME, START_DATE, END_DATE, STATUS, CREATED_AT
        FROM TRIP
        WHERE TRIP_ID = :trip_id AND USER_ID = :user_id
    """, {"trip_id": trip_id, "user_id": user_id})
    
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
    
    destinations = await _fetch_rows("""
        SELECT d.DESTINATION_ID, d.NAME, td.VISIT_ORDER, td.ARRIVAL_DATE, td.DEPARTURE_DATE
        FROM TRIP_DESTINATION td
        JOIN DESTINATION d ON td.DESTINATION_ID = d.DESTINATION_ID
        WHERE td.TRIP_ID = :trip_id
        ORDER BY td.VISIT_ORDER
    """, {"trip_id": trip_id})
    
    bookings = await _fetch_rows("""
        SELECT b.BOOKING_ID, b.BOOKING_TYPE, b.BOOKING_DATE, b.TOTAL_AMOUNT, b.STATUS,
               hb.CHECK_IN_DATE, hb.CHECK_OUT_DATE, hb.NUMBER_OF_GUESTS,
               r.ROOM_NUMBER, r.ROOM_TYPE, h.NAME AS HOTEL_NAME,
               pb.NUMBER_OF_PEOPLE, pb.TRAVEL_DATE, tp.NAME AS PACKAGE_NAME,
               ab.ACTIVITY_DATE, ab.NUMBER_OF_PEOPLE AS ACT_PEOPLE, a.NAME AS ACTIVITY_NAME,
               tb.NUMBER_OF_PASSENGERS, ts.TRANSPORT_TYPE, ts.OPERATOR_NAME,
               od.NAME AS ORIGIN, dd.NAME AS DESTINATION
        FROM BOOKING b
        LEFT JOIN HOTEL_BOOKING hb ON b.BOOKING_ID = hb.BOOKING_ID
        LEFT JOIN ROOM r ON hb.ROOM_ID = r.ROOM_ID
        LEFT JOIN HOTEL h ON r.HOTEL_ID = h.HOTEL_ID
        LEFT JOIN PACKAGE_BOOKING pb ON b.BOOKING_ID = pb.BOOKING_ID
        LEFT JOIN TOUR_PACKAGE tp ON pb.PACKAGE_ID = tp.PACKAGE_ID
        LEFT JOIN ACTIVITY_BOOKING ab ON b.BOOKING_ID = ab.BOOKING_ID
        LEFT JOIN ACTIVITY a ON ab.ACTIVITY_ID = a.ACTIVITY_ID
        LEFT JOIN TRAVEL_BOOKING tb ON b.BOOKING_ID = tb.BOOKING_ID
        LEFT JOIN TRAVEL_SEGMENT ts ON tb.TRAVEL_SEGMENT_ID = ts.TRAVEL_SEGMENT_ID
        LEFT JOIN DESTINATION od ON ts.ORIGIN_DESTINATION_ID = od.DESTINATION_ID
        LEFT JOIN DESTINATION dd ON ts.DESTINATION_DESTINATION_ID = dd.DESTINATION_ID
        WHERE b.TRIP_ID = :trip_id
        ORDER BY b.BOOKING_DATE
    """, {"trip_id": trip_id})
    
    trip["destinations"] = destinations
    trip["bookings"] = bookings
    return trip


@router.post("/trips/{trip_id}/destinations")
async def add_trip_destination(
    trip_id: int,
    destination_id: int,
    visit_order: int,
    arrival_date: str,
    departure_date: str,
    current_user: Dict[str, Any] = Depends(require_customer)
):
    """Add a destination to a trip."""
    user_id = current_user["user_id"]
    
    # Verify trip ownership
    trip = await _fetch_one(
        "SELECT TRIP_ID FROM TRIP WHERE TRIP_ID = :trip_id AND USER_ID = :user_id",
        {"trip_id": trip_id, "user_id": user_id}
    )
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                BEGIN
                    sp_add_trip_destination(:trip_id, :destination_id, :visit_order,
                                          TO_DATE(:arrival_date, 'YYYY-MM-DD'),
                                          TO_DATE(:departure_date, 'YYYY-MM-DD'));
                END;
                """,
                {
                    "trip_id": trip_id,
                    "destination_id": destination_id,
                    "visit_order": visit_order,
                    "arrival_date": arrival_date,
                    "departure_date": departure_date,
                },
            )
            conn.commit()
    
    await log_create(user_id, "TRIP_DESTINATION", trip_id, f"Destination: {destination_id}")
    return {"message": "Destination added to trip successfully."}


# ============================================================
# CUSTOMER BOOKING MANAGEMENT
# ============================================================

@router.post("/bookings", response_model=BookingResponse)
async def create_booking(payload: BookingCreateRequest, current_user: Dict[str, Any] = Depends(require_customer)):
    """Create a new booking (hotel, package, activity, or travel)."""
    user_id = current_user["user_id"]
    trip_id = payload.trip_id
    
    # Verify trip ownership if provided
    if trip_id:
        trip = await _fetch_one(
            "SELECT TRIP_ID FROM TRIP WHERE TRIP_ID = :trip_id AND USER_ID = :user_id",
            {"trip_id": trip_id, "user_id": user_id}
        )
        if not trip:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
    
    booking_id = None
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            if payload.booking_type == "HOTEL":
                if not all([payload.room_id, payload.check_in_date, payload.check_out_date, payload.number_of_guests]):
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                                      detail="Hotel booking requires room_id, check_in_date, check_out_date, number_of_guests")
                
                booking_id = cur.var(int)
                cur.execute(
                    """
                    BEGIN
                        sp_book_hotel(:user_id, :trip_id, :room_id, 
                                    TO_DATE(:check_in, 'YYYY-MM-DD'), TO_DATE(:check_out, 'YYYY-MM-DD'),
                                    :guests, :booking_id);
                    END;
                    """,
                    {
                        "user_id": user_id,
                        "trip_id": trip_id or 0,
                        "room_id": payload.room_id,
                        "check_in": payload.check_in_date,
                        "check_out": payload.check_out_date,
                        "guests": payload.number_of_guests,
                        "booking_id": booking_id,
                    },
                )
                
            elif payload.booking_type == "PACKAGE":
                if not all([payload.package_id, payload.number_of_people, payload.travel_date]):
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                      detail="Package booking requires package_id, number_of_people, travel_date")
                
                booking_id = cur.var(int)
                cur.execute(
                    """
                    BEGIN
                        sp_book_package(:user_id, :trip_id, :package_id, :people,
                                      TO_DATE(:travel_date, 'YYYY-MM-DD'), :booking_id);
                    END;
                    """,
                    {
                        "user_id": user_id,
                        "trip_id": trip_id or 0,
                        "package_id": payload.package_id,
                        "people": payload.number_of_people,
                        "travel_date": payload.travel_date,
                        "booking_id": booking_id,
                    },
                )
                
            elif payload.booking_type == "ACTIVITY":
                if not all([payload.activity_id, payload.activity_date, payload.number_of_people]):
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                      detail="Activity booking requires activity_id, activity_date, number_of_people")
                
                booking_id = cur.var(int)
                cur.execute(
                    """
                    BEGIN
                        sp_book_activity(:user_id, :trip_id, :activity_id,
                                       TO_DATE(:activity_date, 'YYYY-MM-DD'), :people, :booking_id);
                    END;
                    """,
                    {
                        "user_id": user_id,
                        "trip_id": trip_id or 0,
                        "activity_id": payload.activity_id,
                        "activity_date": payload.activity_date,
                        "people": payload.number_of_people,
                        "booking_id": booking_id,
                    },
                )
                
            elif payload.booking_type == "TRAVEL":
                if not all([payload.travel_segment_id, payload.number_of_passengers]):
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                      detail="Travel booking requires travel_segment_id, number_of_passengers")
                
                booking_id = cur.var(int)
                cur.execute(
                    """
                    BEGIN
                        sp_book_travel(:user_id, :trip_id, :segment_id, :passengers, :booking_id);
                    END;
                    """,
                    {
                        "user_id": user_id,
                        "trip_id": trip_id or 0,
                        "segment_id": payload.travel_segment_id,
                        "passengers": payload.number_of_passengers,
                        "booking_id": booking_id,
                    },
                )
            else:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                                  detail="Invalid booking type. Must be HOTEL, PACKAGE, ACTIVITY, or TRAVEL")
            
            created_booking_id = booking_id.getvalue()
            conn.commit()
    
    await log_create(user_id, "BOOKING", created_booking_id, f"Type: {payload.booking_type}")
    
    # Fetch booking details
    booking = await _fetch_one("""
        SELECT b.BOOKING_ID, b.BOOKING_TYPE, b.BOOKING_DATE, b.TOTAL_AMOUNT, b.STATUS, b.TRIP_ID
        FROM BOOKING b
        WHERE b.BOOKING_ID = :booking_id
    """, {"booking_id": created_booking_id})
    
    return BookingResponse(**booking, details={})


@router.get("/bookings")
async def list_bookings(current_user: Dict[str, Any] = Depends(require_customer)):
    """List all bookings for the current customer."""
    user_id = current_user["user_id"]
    rows = await _fetch_rows("""
        SELECT b.BOOKING_ID, b.BOOKING_TYPE, b.BOOKING_DATE, b.TOTAL_AMOUNT, b.STATUS, b.TRIP_ID,
               t.TRIP_NAME
        FROM BOOKING b
        LEFT JOIN TRIP t ON b.TRIP_ID = t.TRIP_ID
        WHERE b.USER_ID = :user_id
        ORDER BY b.BOOKING_DATE DESC
    """, {"user_id": user_id})
    return rows


@router.get("/bookings/{booking_id}")
async def get_booking_details(booking_id: int, current_user: Dict[str, Any] = Depends(require_customer)):
    """Get detailed booking information."""
    user_id = current_user["user_id"]
    
    # Verify ownership
    booking = await _fetch_one("""
        SELECT b.BOOKING_ID, b.BOOKING_TYPE, b.BOOKING_DATE, b.TOTAL_AMOUNT, b.STATUS, b.TRIP_ID
        FROM BOOKING b
        WHERE b.BOOKING_ID = :booking_id AND b.USER_ID = :user_id
    """, {"booking_id": booking_id, "user_id": user_id})
    
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")
    
    # Get type-specific details
    details = {}
    if booking["booking_type"] == "HOTEL":
        details = await _fetch_one("""
            SELECT hb.CHECK_IN_DATE, hb.CHECK_OUT_DATE, hb.NUMBER_OF_GUESTS,
                   r.ROOM_NUMBER, r.ROOM_TYPE, r.PRICE_PER_NIGHT,
                   h.NAME AS HOTEL_NAME, h.ADDRESS AS HOTEL_ADDRESS
            FROM HOTEL_BOOKING hb
            JOIN ROOM r ON hb.ROOM_ID = r.ROOM_ID
            JOIN HOTEL h ON r.HOTEL_ID = h.HOTEL_ID
            WHERE hb.BOOKING_ID = :booking_id
        """, {"booking_id": booking_id})
    elif booking["booking_type"] == "PACKAGE":
        details = await _fetch_one("""
            SELECT pb.NUMBER_OF_PEOPLE, pb.TRAVEL_DATE,
                   tp.NAME AS PACKAGE_NAME, tp.DURATION_DAYS, tp.PRICE AS PACKAGE_PRICE
            FROM PACKAGE_BOOKING pb
            JOIN TOUR_PACKAGE tp ON pb.PACKAGE_ID = tp.PACKAGE_ID
            WHERE pb.BOOKING_ID = :booking_id
        """, {"booking_id": booking_id})
    elif booking["booking_type"] == "ACTIVITY":
        details = await _fetch_one("""
            SELECT ab.ACTIVITY_DATE, ab.NUMBER_OF_PEOPLE,
                   a.NAME AS ACTIVITY_NAME, a.DESCRIPTION, a.DURATION_HOURS, a.PRICE,
                   d.NAME AS DESTINATION_NAME
            FROM ACTIVITY_BOOKING ab
            JOIN ACTIVITY a ON ab.ACTIVITY_ID = a.ACTIVITY_ID
            JOIN DESTINATION d ON a.DESTINATION_ID = d.DESTINATION_ID
            WHERE ab.BOOKING_ID = :booking_id
        """, {"booking_id": booking_id})
    elif booking["booking_type"] == "TRAVEL":
        details = await _fetch_one("""
            SELECT tb.NUMBER_OF_PASSENGERS,
                   ts.TRANSPORT_TYPE, ts.OPERATOR_NAME, ts.DEPARTURE_TIME, ts.ARRIVAL_TIME, ts.PRICE,
                   od.NAME AS ORIGIN, dd.NAME AS DESTINATION
            FROM TRAVEL_BOOKING tb
            JOIN TRAVEL_SEGMENT ts ON tb.TRAVEL_SEGMENT_ID = ts.TRAVEL_SEGMENT_ID
            JOIN DESTINATION od ON ts.ORIGIN_DESTINATION_ID = od.DESTINATION_ID
            JOIN DESTINATION dd ON ts.DESTINATION_DESTINATION_ID = dd.DESTINATION_ID
            WHERE tb.BOOKING_ID = :booking_id
        """, {"booking_id": booking_id})
    
    booking["details"] = details or {}
    return booking


@router.delete("/bookings/{booking_id}")
async def cancel_booking(booking_id: int, current_user: Dict[str, Any] = Depends(require_customer)):
    """Cancel a booking."""
    user_id = current_user["user_id"]
    
    # Verify ownership
    booking = await _fetch_one(
        "SELECT BOOKING_ID FROM BOOKING WHERE BOOKING_ID = :booking_id AND USER_ID = :user_id",
        {"booking_id": booking_id, "user_id": user_id}
    )
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                BEGIN
                    sp_cancel_booking(:booking_id, :user_id);
                END;
                """,
                {"booking_id": booking_id, "user_id": user_id},
            )
            conn.commit()
    
    await log_delete(user_id, "BOOKING", booking_id, f"Cancelled by customer")
    return {"message": "Booking cancelled successfully."}


# ============================================================
# CUSTOMER PAYMENTS
# ============================================================

@router.post("/payments", response_model=PaymentResponse)
async def make_payment(payload: PaymentCreateRequest, current_user: Dict[str, Any] = Depends(require_customer)):
    """Make a payment for a booking."""
    user_id = current_user["user_id"]
    
    # Verify booking ownership
    booking = await _fetch_one(
        "SELECT BOOKING_ID, TOTAL_AMOUNT FROM BOOKING WHERE BOOKING_ID = :booking_id AND USER_ID = :user_id",
        {"booking_id": payload.booking_id, "user_id": user_id}
    )
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            payment_id = cur.var(int)
            cur.execute(
                """
                BEGIN
                    sp_make_payment(:booking_id, :amount, :method, :user_id, :payment_id);
                END;
                """,
                {
                    "booking_id": payload.booking_id,
                    "amount": payload.amount,
                    "method": payload.payment_method,
                    "user_id": user_id,
                    "payment_id": payment_id,
                },
            )
            created_payment_id = payment_id.getvalue()
            conn.commit()
    
    await log_create(user_id, "PAYMENT", created_payment_id, f"Booking: {payload.booking_id}, Amount: {payload.amount}")
    
    payment = await _fetch_one("""
        SELECT PAYMENT_ID, BOOKING_ID, TRANSACTION_REFERENCE, AMOUNT, PAYMENT_METHOD,
               PAYMENT_DATE, STATUS, REFUND_AMOUNT
        FROM PAYMENT
        WHERE PAYMENT_ID = :payment_id
    """, {"payment_id": created_payment_id})
    
    return PaymentResponse(**payment)


@router.get("/payments")
async def list_payments(current_user: Dict[str, Any] = Depends(require_customer)):
    """List all payments for the current customer."""
    user_id = current_user["user_id"]
    rows = await _fetch_rows("""
        SELECT p.PAYMENT_ID, p.BOOKING_ID, p.TRANSACTION_REFERENCE, p.AMOUNT,
               p.PAYMENT_METHOD, p.PAYMENT_DATE, p.STATUS, p.REFUND_AMOUNT,
               b.BOOKING_TYPE
        FROM PAYMENT p
        JOIN BOOKING b ON p.BOOKING_ID = b.BOOKING_ID
        WHERE b.USER_ID = :user_id
        ORDER BY p.PAYMENT_DATE DESC
    """, {"user_id": user_id})
    return rows


# ============================================================
# CUSTOMER REVIEWS
# ============================================================

@router.post("/reviews", response_model=ReviewResponse)
async def submit_review(payload: ReviewCreateRequest, current_user: Dict[str, Any] = Depends(require_customer)):
    """Submit a review for a completed trip."""
    user_id = current_user["user_id"]
    
    # Verify trip ownership
    trip = await _fetch_one(
        "SELECT TRIP_ID FROM TRIP WHERE TRIP_ID = :trip_id AND USER_ID = :user_id",
        {"trip_id": payload.trip_id, "user_id": user_id}
    )
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                BEGIN
                    sp_submit_review(:user_id, :trip_id, :rating, :comment);
                END;
                """,
                {
                    "user_id": user_id,
                    "trip_id": payload.trip_id,
                    "rating": payload.rating,
                    "comment": payload.comment or "",
                },
            )
            conn.commit()
    
    # Get the created review
    review = await _fetch_one("""
        SELECT REVIEW_ID, TRIP_ID, RATING, USER_COMMENT, REVIEW_DATE
        FROM REVIEW
        WHERE TRIP_ID = :trip_id
    """, {"trip_id": payload.trip_id})
    
    await log_create(user_id, "REVIEW", review["review_id"], f"Trip: {payload.trip_id}, Rating: {payload.rating}")
    return ReviewResponse(**review)


@router.get("/reviews")
async def list_reviews(current_user: Dict[str, Any] = Depends(require_customer)):
    """List all reviews by the current customer."""
    user_id = current_user["user_id"]
    rows = await _fetch_rows("""
        SELECT r.REVIEW_ID, r.TRIP_ID, r.RATING, r.USER_COMMENT, r.REVIEW_DATE,
               t.TRIP_NAME
        FROM REVIEW r
        JOIN TRIP t ON r.TRIP_ID = t.TRIP_ID
        WHERE t.USER_ID = :user_id
        ORDER BY r.REVIEW_DATE DESC
    """, {"user_id": user_id})
    return rows