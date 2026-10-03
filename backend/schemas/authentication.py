from typing import Optional

from pydantic import BaseModel, Field


class RegistrationRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: str = Field(..., min_length=3, max_length=100)
    phone: str = Field(..., min_length=7, max_length=15)
    password: str = Field(..., min_length=8, max_length=128)

    @property
    def normalized_email(self) -> str:
        return self.email.strip().lower()


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="CUSTOMER")


class ProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=8, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)


class UserPublic(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    role: str
    status: str


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class DestinationCreateRequest(BaseModel):
    name: str
    city: str
    country: str
    description: Optional[str] = None
    state: Optional[str] = None
    status: str = "ACTIVE"


class HotelCreateRequest(BaseModel):
    destination_id: int
    name: str
    address: str
    contact_number: Optional[str] = None
    email: Optional[str] = None
    star_rating: Optional[float] = 4.5
    description: Optional[str] = None
    status: str = "ACTIVE"
    owner_id: Optional[int] = None


class TourPackageCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    duration_days: int = 1
    price: float = 0.0
    status: str = "ACTIVE"


class ActivityCreateRequest(BaseModel):
    destination_id: int
    name: str
    description: Optional[str] = None
    category: str = "General"
    duration_hours: float = 1.0
    price: float = 0.0
    capacity: int = 1
    status: str = "ACTIVE"


# Customer schemas
class TripCreateRequest(BaseModel):
    trip_name: str = Field(..., min_length=1, max_length=100)
    start_date: str  # ISO format date
    end_date: str    # ISO format date


class TripResponse(BaseModel):
    trip_id: int
    trip_name: str
    start_date: str
    end_date: str
    status: str
    destinations: list = []
    bookings: list = []


class BookingCreateRequest(BaseModel):
    trip_id: Optional[int] = None
    booking_type: str  # HOTEL, PACKAGE, ACTIVITY, TRAVEL
    # Hotel booking
    room_id: Optional[int] = None
    check_in_date: Optional[str] = None
    check_out_date: Optional[str] = None
    number_of_guests: Optional[int] = None
    # Package booking
    package_id: Optional[int] = None
    number_of_people: Optional[int] = None
    travel_date: Optional[str] = None
    # Activity booking
    activity_id: Optional[int] = None
    activity_date: Optional[str] = None
    # Travel booking
    travel_segment_id: Optional[int] = None
    number_of_passengers: Optional[int] = None


class BookingResponse(BaseModel):
    booking_id: int
    booking_type: str
    booking_date: str
    total_amount: float
    status: str
    trip_id: Optional[int] = None
    details: dict = {}


class PaymentCreateRequest(BaseModel):
    booking_id: int
    amount: float
    payment_method: str  # CREDIT_CARD, DEBIT_CARD, UPI, NET_BANKING, WALLET, CASH


class PaymentResponse(BaseModel):
    payment_id: int
    booking_id: int
    transaction_reference: str
    amount: float
    payment_method: str
    payment_date: str
    status: str


class ReviewCreateRequest(BaseModel):
    trip_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class ReviewResponse(BaseModel):
    review_id: int
    trip_id: int
    rating: int
    comment: Optional[str]
    review_date: str


# Owner schemas
class OwnerHotelResponse(BaseModel):
    hotel_id: int
    name: str
    description: Optional[str]
    address: str
    contact_number: Optional[str]
    email: Optional[str]
    star_rating: Optional[float]
    status: str
    destination_id: int
    destination_name: Optional[str] = None
    room_count: int = 0


class OwnerRoomResponse(BaseModel):
    room_id: int
    hotel_id: int
    hotel_name: str
    room_number: str
    room_type: str
    capacity: int
    price_per_night: float
    status: str


class RoomCreateRequest(BaseModel):
    room_number: str
    room_type: str
    capacity: int
    price_per_night: float
    status: str = "AVAILABLE"


class RoomUpdateRequest(BaseModel):
    room_number: Optional[str] = None
    room_type: Optional[str] = None
    capacity: Optional[int] = None
    price_per_night: Optional[float] = None
    status: Optional[str] = None


class OwnerBookingResponse(BaseModel):
    booking_id: int
    booking_type: str
    booking_date: str
    total_amount: float
    status: str
    customer_name: str
    customer_email: str
    hotel_name: str
    room_number: Optional[str] = None
    check_in_date: Optional[str] = None
    check_out_date: Optional[str] = None


class OwnerTripResponse(BaseModel):
    trip_id: int
    trip_name: str
    customer_name: str
    customer_email: str
    start_date: str
    end_date: str
    status: str
    bookings: list = []


# Admin schemas
class AdminUserCreateRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: str = Field(..., min_length=3, max_length=100)
    phone: str = Field(..., min_length=7, max_length=15)
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="CUSTOMER")  # CUSTOMER, OWNER, ADMIN
    status: str = Field(default="ACTIVE")  # ACTIVE, INACTIVE


class AdminUserUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None


class AdminUserResponse(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    role: str
    status: str
    created_at: str


class AdminHotelResponse(BaseModel):
    hotel_id: int
    owner_id: int
    owner_name: str
    destination_id: int
    destination_name: str
    name: str
    description: Optional[str]
    address: str
    contact_number: Optional[str]
    email: Optional[str]
    star_rating: Optional[float]
    status: str


class AdminRoomResponse(BaseModel):
    room_id: int
    hotel_id: int
    hotel_name: str
    room_number: str
    room_type: str
    capacity: int
    price_per_night: float
    status: str


class AdminActivityResponse(BaseModel):
    activity_id: int
    destination_id: int
    destination_name: str
    name: str
    description: Optional[str]
    category: str
    duration_hours: float
    price: float
    capacity: int
    status: str


class AdminTourPackageResponse(BaseModel):
    package_id: int
    name: str
    description: Optional[str]
    duration_days: int
    price: float
    max_capacity: Optional[int] = None
    status: str
    destinations: list = []
    activities: list = []


class AdminTravelSegmentResponse(BaseModel):
    travel_segment_id: int
    origin_destination_id: int
    origin_name: str
    destination_destination_id: int
    destination_name: str
    transport_type: str
    operator_name: Optional[str]
    departure_time: str
    arrival_time: str
    price: float
    capacity: int
    status: str


class AdminDestinationResponse(BaseModel):
    destination_id: int
    name: str
    city: str
    state: Optional[str]
    country: str
    description: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    status: str


class AdminTripResponse(BaseModel):
    trip_id: int
    user_id: int
    customer_name: str
    trip_name: str
    start_date: str
    end_date: str
    status: str
    created_at: str


class AdminBookingResponse(BaseModel):
    booking_id: int
    user_id: int
    customer_name: str
    trip_id: Optional[int]
    booking_type: str
    booking_date: str
    total_amount: float
    status: str
    cancelled_at: Optional[str] = None


class AdminReportResponse(BaseModel):
    total_users: int
    total_bookings: int
    total_revenue: float
    bookings_by_type: dict
    bookings_by_status: dict
    revenue_by_type: dict


class AuditLogResponse(BaseModel):
    audit_id: int
    user_id: Optional[int]
    performed_by: Optional[str]
    action: str
    entity_name: str
    record_id: Optional[int]
    old_value: Optional[str]
    new_value: Optional[str]
    action_timestamp: str
