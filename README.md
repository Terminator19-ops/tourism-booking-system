# Tourism Booking Platform

A full-stack tourism booking platform built with **FastAPI (Python)** backend and **Vanilla HTML/CSS/JavaScript** frontend, using **Oracle Database** for data persistence.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Vanilla JS)                    │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │ Login   │ │Dashboard│ │ Trips   │ │ Hotels  │ │ Tours   │  │
│  │ Register│ │ Profile │ │ Activities│ │ Travel  │ │ Owner   │  │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘  │
│       │           │           │           │           │        │
│       └───────────┴─────┬─────┴───────────┴───────────┘        │
│                         ▼                                       │
│              ┌─────────────────────┐                            │
│              │   api.js (Shared)   │                            │
│              │  - Auth Management  │                            │
│              │  - API Fetch Wrapper│                            │
│              │  - Role Navigation  │                            │
│              └──────────┬──────────┘                            │
└─────────────────────────┼───────────────────────────────────────┘
                          │ HTTP/REST + JWT Bearer
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ /auth    │ │/customer │ │ /owner   │ │ /admin   │           │
│  │ - login  │ │ - trips  │ │ - hotels │ │ - users  │           │
│  │ - register│ │ - bookings│ │ - rooms  │ │ - dests  │           │
│  │ - profile│ │ - reviews│ │ - bookings│ │ - hotels │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│         │            │            │            │                │
│         └────────────┴────────────┴────────────┘                │
│                          ▼                                       │
│              ┌─────────────────────┐                            │
│              │  Oracle Database    │                            │
│              │  - Stored Procs     │                            │
│              │  - Sequences        │                            │
│              │  - Constraints      │                            │
│              └─────────────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Oracle Database (with wallet-based connection)
- Node.js (optional, for frontend tooling)

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
# Configure wallet/ directory with Oracle wallet files
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup
```bash
cd frontend
# Serve with any static file server
python -m http.server 3000
# Or use VS Code Live Server extension
```

### Database Setup
Run the SQL files in order:
1. `sql/tables1.sqlnb` - Core tables
2. `sql/tables3.sqlnb` - Additional tables
3. `sql/customer_procedures.sqlnb` - Stored procedures
4. `sql/sample_data1.sqlnb` - Sample data

## 👥 Mock Users & Credentials

All passwords are **`Password123!`** (hashed with PBKDF2-SHA256)

| Role | Email | Name | User ID | Description |
|------|-------|------|---------|-------------|
| **ADMIN** | `admin@tourism.com` | Admin User | 1 | Platform administrator |
| **OWNER** | `rahul.sharma@gmail.com` | Rahul Sharma | 2 | Hotel owner (Grand Palace Hotel, Goa Paradise Resort) |
| **CUSTOMER** | `priya.nair@gmail.com` | Priya Nair | 3 | Regular customer |
| **OWNER** | `arjun.kumar@gmail.com` | Arjun Kumar | 4 | Hotel owner (Royal Mysore Hotel) |

### Login Instructions
1. Open `frontend/login.html`
2. Select role (CUSTOMER, OWNER, or ADMIN)
3. Enter email and password: `Password123!`
4. Click Login

### Role-Based Routing
| Role | Redirects To | Navigation |
|------|--------------|------------|
| CUSTOMER | `dashboard.html` | Dashboard, Trips, Hotels, Tours, Travel, Activities, Profile |
| OWNER | `owner.html` | My Hotels, My Bookings, My Trips, Profile |
| ADMIN | `admin.html` | Profile, Admin (full management) |

## 📡 API Endpoints

### Authentication (`/api/auth`)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/register/customer` | Register new customer | ❌ |
| POST | `/register/owner` | Register new owner | ❌ |
| POST | `/login` | Login (email, password, role) | ❌ |
| GET | `/me` | Get current user profile | ✅ |
| PUT | `/me` | Update profile (name, phone) | ✅ |
| PUT | `/change-password` | Change password | ✅ |
| POST | `/logout` | Logout (invalidate session) | ✅ |

### Customer (`/api/customer`) - Requires CUSTOMER role
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/hotels` | List active hotels with destination info |
| GET | `/hotels/{id}` | Get hotel details with available rooms |
| GET | `/activities` | List active activities |
| GET | `/destinations` | List active destinations for trip planning |
| GET | `/tour-packages` | List active tour packages with destinations/activities |
| GET | `/travel` | List scheduled travel segments |
| POST | `/trips` | Create new trip |
| GET | `/trips` | List user's trips |
| GET | `/trips/{id}` | Get trip details (destinations, bookings) |
| POST | `/trips/{id}/destinations` | Add destination to trip |
| POST | `/bookings` | Create booking (HOTEL/PACKAGE/ACTIVITY/TRAVEL) |
| GET | `/bookings` | List user's bookings |
| GET | `/bookings/{id}` | Get booking details |
| DELETE | `/bookings/{id}` | Cancel booking |
| POST | `/payments` | Make payment for booking |
| GET | `/payments` | List user's payments |
| POST | `/reviews` | Submit review for completed trip |
| GET | `/reviews` | List user's reviews |
| GET | `/trips/{id}/review` | Get review for specific trip |

### Owner (`/api/owner`) - Requires OWNER role
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/hotels` | List owner's hotels |
| POST | `/hotels` | Create new hotel |
| GET | `/hotels/{id}` | Get hotel details with rooms |
| PUT | `/hotels/{id}` | Update hotel |
| DELETE | `/hotels/{id}` | Deactivate hotel (cascades to rooms) |
| GET | `/hotels/{id}/rooms` | List rooms for hotel |
| POST | `/hotels/{id}/rooms` | Create room |
| PUT | `/hotels/{id}/rooms/{room_id}` | Update room |
| DELETE | `/hotels/{id}/rooms/{room_id}` | Deactivate room |
| GET | `/bookings` | List bookings for owner's hotels |
| GET | `/trips` | List trips with bookings at owner's hotels |

### Admin (`/api/admin`) - Requires ADMIN role
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/users` | List/Create users |
| GET/PUT/DELETE | `/users/{id}` | Manage user (soft delete if dependencies) |
| GET/POST | `/destinations` | List/Create destinations |
| GET/PUT/DELETE | `/destinations/{id}` | Manage destination |
| GET/POST | `/hotels` | List/Create hotels |
| GET/PUT/DELETE | `/hotels/{id}` | Manage hotel |
| GET/POST | `/rooms` | List/Create rooms |
| GET/PUT/DELETE | `/rooms/{id}` | Manage room |
| GET/POST | `/activities` | List/Create activities |
| GET/PUT/DELETE | `/activities/{id}` | Manage activity |
| GET/POST | `/tour-packages` | List/Create packages |
| GET/PUT/DELETE | `/tour-packages/{id}` | Manage package |
| POST/DELETE | `/tour-packages/{id}/destinations` | Manage package destinations |
| POST/DELETE | `/tour-packages/{id}/activities` | Manage package activities |
| GET/POST | `/travel-segments` | List/Create travel segments |
| GET/PUT/DELETE | `/travel-segments/{id}` | Manage travel segment |
| GET | `/trips` | List all trips |
| GET/PUT/DELETE | `/trips/{id}` | Manage trip |
| GET | `/bookings` | List all bookings |
| GET/PUT/DELETE | `/bookings/{id}` | Manage booking |
| GET/POST | `/reports` | List/Create reports |
| GET/PUT/DELETE | `/reports/{id}` | Manage report |
| GET | `/audit-logs` | List audit logs (with filters) |

## 🗄️ Database Schema

### Core Tables
| Table | Description | Key Constraints |
|-------|-------------|-----------------|
| `APP_USER` | Users (customers, owners, admins) | PK: user_id, UK: email, phone, CHECK: role, status |
| `DESTINATION` | Travel destinations | PK: destination_id, CHECK: status |
| `HOTEL` | Hotels owned by owners | PK: hotel_id, FK: owner_id, destination_id, CHECK: status |
| `ROOM` | Hotel rooms | PK: room_id, FK: hotel_id, CHECK: status (AVAILABLE/OCCUPIED/MAINTENANCE) |
| `ACTIVITY` | Activities at destinations | PK: activity_id, FK: destination_id, CHECK: status |
| `TRAVEL_SEGMENT` | Transport between destinations | PK: travel_segment_id, FK: origin/dest, CHECK: status |
| `TOUR_PACKAGE` | Multi-destination packages | PK: package_id, CHECK: status |
| `PACKAGE_DESTINATION` | Package ↔ Destination mapping | PK: (package_id, destination_id) |
| `PACKAGE_ACTIVITY` | Package ↔ Activity mapping | PK: (package_id, activity_id) |
| `TRIP` | Customer trip plans | PK: trip_id, FK: user_id, CHECK: status |
| `TRIP_DESTINATION` | Trip ↔ Destination mapping | PK: (trip_id, destination_id) |
| `BOOKING` | Base booking record | PK: booking_id, FK: user_id, trip_id, CHECK: type, status |
| `HOTEL_BOOKING` | Hotel-specific booking details | PK: booking_id, FK: room_id |
| `PACKAGE_BOOKING` | Package booking details | PK: booking_id, FK: package_id |
| `ACTIVITY_BOOKING` | Activity booking details | PK: booking_id, FK: activity_id |
| `TRAVEL_BOOKING` | Travel booking details | PK: booking_id, FK: travel_segment_id |
| `PAYMENT` | Payment records | PK: payment_id, FK: booking_id, CHECK: status |
| `REVIEW` | Trip reviews | PK: review_id, FK: trip_id, CHECK: rating (1-5) |
| `REPORT` | Admin reports | PK: report_id, FK: user_id, CHECK: status |
| `AUDIT_LOG` | System audit trail | PK: audit_id, CHECK: action |

### Sequences
- `user_seq`, `destination_seq`, `hotel_seq`, `room_seq`, `activity_seq`
- `travel_segment_seq`, `tour_package_seq`, `booking_seq`, `payment_seq`
- `review_seq`, `report_seq`, `audit_log_seq`

### Key Stored Procedures
| Procedure | Purpose |
|-----------|---------|
| `sp_register_customer` | Register new customer |
| `sp_register_owner` | Register new owner |
| `sp_create_trip` | Create trip |
| `sp_add_trip_destination` | Add destination to trip |
| `sp_book_hotel` | Book hotel room |
| `sp_book_package` | Book tour package |
| `sp_book_activity` | Book activity |
| `sp_book_travel` | Book travel segment |
| `sp_make_payment` | Process payment |
| `sp_submit_review` | Submit trip review |
| `sp_cancel_booking` | Cancel booking |

## 🔐 Authentication & Authorization

### JWT Token Flow
1. User logs in via `/api/auth/login`
2. Server creates session, returns JWT token
3. Client stores token in `localStorage` (`authToken`)
4. All subsequent requests include `Authorization: Bearer <token>`
5. Server validates token via `get_current_user` dependency

### Role-Based Access Control
- **CUSTOMER**: Can access `/api/customer/*`, `/api/auth/me`, `/api/auth/change-password`
- **OWNER**: Can access `/api/owner/*`, `/api/auth/me`, `/api/auth/change-password`
- **ADMIN**: Can access `/api/admin/*`, `/api/auth/me`, `/api/auth/change-password`

### Frontend Route Guards
- `requireRole(['CUSTOMER'])` - Redirects to login if not customer
- `requireRole(['OWNER', 'ADMIN'])` - Allows owner or admin
- `requireRole(['ADMIN'])` - Admin only
- `renderNavigation()` - Dynamically renders nav based on role

## 🎨 Frontend Pages

| Page | Role | Description |
|------|------|-------------|
| `login.html` | All | Login/Register with role selection |
| `dashboard.html` | CUSTOMER | Overview of trips, bookings, payments |
| `trips.html` | CUSTOMER | Create/manage trips, add destinations, write reviews |
| `hotels.html` | CUSTOMER | Browse hotels, view details, book rooms |
| `tours.html` | CUSTOMER | Browse tour packages, book packages |
| `travel.html` | CUSTOMER | Browse travel segments, book travel |
| `activities.html` | CUSTOMER | Browse activities, book activities |
| `profile.html` | All | View/edit profile, change password |
| `owner.html` | OWNER | Manage hotels, rooms, view bookings/trips |
| `admin.html` | ADMIN | Full CRUD for all entities + audit logs |

## 🔧 Key Features

### Booking Flow
1. Customer creates trip (`/trips`)
2. Adds destinations to trip (`/trips/{id}/destinations`)
3. Books hotel/package/activity/travel (`/bookings`)
4. Makes payment (`/payments`)
5. Submits review after trip completion (`/reviews`)

### Admin Soft Delete Pattern
All admin DELETE endpoints check for dependencies:
- If dependencies exist → Soft delete (status = INACTIVE/MAINTENANCE/CANCELLED)
- If no dependencies → Hard delete
- All actions logged in `AUDIT_LOG`

### Audit Logging
Every CREATE/UPDATE/DELETE/LOGIN/LOGOUT/CANCEL/PAY action logged with:
- Entity name, record ID, action type
- Old/new values (JSON)
- User ID, timestamp

## 📁 Project Structure

```
Project/
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── db.py                   # Database connection
│   ├── database/
│   │   └── connection.py       # Oracle connection pool
│   ├── routes/
│   │   ├── authentication.py   # Auth endpoints
│   │   ├── customer.py         # Customer endpoints
│   │   ├── owner.py            # Owner endpoints
│   │   └── admin.py            # Admin endpoints
│   ├── schemas/
│   │   └── authentication.py   # Pydantic models
│   ├── utils/
│   │   ├── authentication.py   # JWT, password hashing
│   │   ├── authorization.py    # Role dependencies
│   │   └── audit.py            # Audit logging
│   └── requirements.txt
├── frontend/
│   ├── *.html                  # 10 HTML pages
│   ├── css/style.css           # Shared styles
│   └── js/
│       ├── api.js              # Shared API helper (auth, fetch, nav)
│       ├── login.js            # Login/register logic
│       ├── dashboard.js        # Customer dashboard
│       ├── trips.js            # Trip management
│       ├── hotels.js           # Hotel browsing/booking
│       ├── tours.js            # Tour package booking
│       ├── travel.js           # Travel booking
│       ├── activities.js       # Activity booking
│       ├── profile.js          # Profile management
│       ├── owner.js            # Owner dashboard
│       └── admin.js            # Admin management
├── sql/
│   ├── tables1.sqlnb           # Core tables
│   ├── tables3.sqlnb           # Additional tables
│   ├── customer_procedures.sqlnb # Stored procedures
│   ├── sample_data1.sqlnb      # Sample data
│   └── db_queries.sqlnb        # Useful queries
├── wallet/                     # Oracle wallet files
│   ├── cwallet.sso
│   ├── ojdbc.properties
│   ├── sqlnet.ora
│   └── tnsnames.ora
└── tests/
    └── test_auth_utils.py
```

## 🛠️ Development Notes

### Adding New Endpoints
1. Add route in appropriate `backend/routes/*.py`
2. Add Pydantic schema in `backend/schemas/authentication.py` if needed
3. Update frontend `api.js` if new auth patterns needed
4. Create/update frontend page and JS module

### Database Changes
1. Add migration SQL to `sql/` directory
2. Update stored procedures if needed
3. Run against Oracle database

### Frontend Conventions
- All pages include `<script src="js/api.js"></script>` first
- Use `apiFetch(path, options)` for all API calls
- Use `renderNavigation()` on DOMContentLoaded
- Use `loadCurrentUser()` for auth check
- Error handling via `handleApiError()`

## 🐛 Known Issues / TODO

1. **Hotel Booking Availability**: `sp_book_hotel` returns ORA-20003 if room not available for dates
2. **Admin User Delete**: ORA-00904 on USER_ID column in dependency check query
3. **Travel Segment Status**: CHECK constraint violation when setting INACTIVE (valid: SCHEDULED/CANCELLED/COMPLETED)
4. **Review Fetch**: ORA-00923 syntax error in GET `/trips/{id}/review` query
5. **Review Submit**: ORA-00923 syntax error in POST `/reviews` query

## 📝 License

Academic Project - SEM-5 DBMS Course