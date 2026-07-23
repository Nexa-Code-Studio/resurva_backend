from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.mcp  # Trigger MCP tool registration automatically
from app.api.v1.router import api_router
from app.core.config import settings
from app.modules.business.models import Business
from app.modules.carbon.models import CarbonLog
from app.modules.chat.models import ChatMemory, ChatMessage, Conversation, ToolCall
from app.modules.discounts.models import Discount
from app.modules.orders.models import Order, OrderDiscount, OrderItem, OrderItemBatch
from app.modules.inventory.models import ExpiryAlert, InventoryBatch
from app.modules.products.models import Ingredient, Product, ProductIngredient
from app.modules.reviews.models import Review
from app.modules.stores.models import Store
from app.modules.summaries.models import DailySummary, MonthlySummary
from app.modules.transactions.models import Transaction

# Import all models to ensure they are registered with SQLAlchemy Base metadata at startup
from app.modules.auth.models import RefreshToken
from app.modules.users.models import User
from app.modules.wallets.models import Wallet, WalletTransaction


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Food Waste Marketplace Modular Monolith API Backend",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app.core.middleware import SystemLoggingMiddleware

# Set up Allowed Hosts middleware
allowed_hosts = settings.ALLOWED_HOSTS if isinstance(settings.ALLOWED_HOSTS, list) else [h.strip() for h in settings.ALLOWED_HOSTS.split(",")]
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=allowed_hosts,
)

# Register System Logging Middleware
app.add_middleware(SystemLoggingMiddleware)

# Set up CORS middleware
cors_origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [o.strip() for o in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https?://([a-zA-Z0-9-]+\.)*resurva\.my\.id\.?|http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register central routers
app.include_router(api_router, prefix=settings.API_V1_STR)

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger("uvicorn.error")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.error(f"Validation error: {exc.errors()}")
    logger.error(f"Validation body: {await request.body()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": (await request.body()).decode("utf-8", errors="ignore")},
    )

from fastapi.staticfiles import StaticFiles
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/", tags=["Health"])
async def root():
    return {
        "project": settings.PROJECT_NAME,
        "status": "online",
        "documentation": "/docs" if settings.DEBUG else "disabled"
    }
