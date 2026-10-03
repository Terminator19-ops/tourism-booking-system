from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.admin import router as admin_router
from backend.routes.authentication import router as auth_router
from backend.routes.customer import router as customer_router
from backend.routes.owner import router as owner_router

app = FastAPI(title="Tourism Booking Platform API")

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
