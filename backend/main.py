from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.admin import router as admin_router
from backend.routes.authentication import router as auth_router
from backend.routes.customer import router as customer_router
from backend.routes.owner import router as owner_router

import re
import oracledb
from fastapi.responses import JSONResponse

app = FastAPI(title="Tourism Booking Platform API")

@app.exception_handler(oracledb.DatabaseError)
async def oracle_error_handler(request, exc):
    text = str(exc)
    m = re.search(r"ORA-(\d+):\s*([^\n]+)", text)
    if m and 20000 <= int(m.group(1)) <= 20999:   # your RAISE_APPLICATION_ERROR messages
        return JSONResponse(status_code=400, content={"detail": m.group(2).strip()})
    return JSONResponse(status_code=500, content={"detail": "Database error: " + (m.group(0) if m else text[:200])})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(customer_router)
app.include_router(owner_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
