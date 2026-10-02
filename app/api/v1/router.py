from fastapi import APIRouter
from app.api.v1.endpoints import auth, catalogue, bookings, payments

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(catalogue.router)
api_router.include_router(bookings.router)
api_router.include_router(payments.router)
