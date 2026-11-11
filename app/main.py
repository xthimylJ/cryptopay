"""
Entry point. Run locally with:   uvicorn app.main:app --reload
Then open http://localhost:8000  (API docs: http://localhost:8000/docs)
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import checkout, demo_shop, merchants, payments
from app.config import settings
from app.database import Base, engine
from app.services.errors import DomainError

logging.basicConfig(level=logging.INFO)
STATIC = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup if they don't exist yet.
    # (A bigger project would use migrations - Alembic.)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="CryptoPay",
    description="A Stripe-like gateway that lets businesses accept crypto (ETH) payments.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    """Translate business errors into HTTP responses in one place."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


app.include_router(merchants.router)
app.include_router(payments.router)
app.include_router(checkout.router)
app.include_router(demo_shop.router)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


# ---------- HTML pages ----------

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(STATIC / "index.html")


@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(STATIC / "dashboard.html")


@app.get("/pay/{payment_id}", include_in_schema=False)
def pay_page(payment_id: str):
    return FileResponse(STATIC / "checkout.html")


@app.get("/health", tags=["System"], summary="Health check for the cloud platform")
def health():
    return {"status": "ok", "blockchain_mode": settings.BLOCKCHAIN_MODE}
