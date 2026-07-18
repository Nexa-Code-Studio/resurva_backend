import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.analytics.schemas import (
    FinancialAnalyticsResponse,
    SalesAnalyticsResponse,
    InventoryRecommendationResponse,
)
from app.modules.analytics.service.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/finance", response_model=FinancialAnalyticsResponse)
async def get_financial_analytics(
    store_id: uuid.UUID = Query(..., description="Store UUID"),
    timeframe: str = Query("weekly", description="weekly or monthly"),
    tx_type: str = Query("in", description="in or out for category breakdown"),
    db: AsyncSession = Depends(get_db_session),
):
    service = AnalyticsService(db)
    return await service.get_finance_analytics(
        store_id=store_id, timeframe=timeframe, tx_type=tx_type
    )


@router.get("/sales", response_model=SalesAnalyticsResponse)
async def get_sales_analytics(
    store_id: uuid.UUID = Query(..., description="Store UUID"),
    timeframe: str = Query("weekly", description="weekly or monthly"),
    date_offset: int = Query(0, description="Offset multiplier"),
    db: AsyncSession = Depends(get_db_session),
):
    service = AnalyticsService(db)
    return await service.get_sales_analytics(
        store_id=store_id, timeframe=timeframe, date_offset=date_offset
    )


@router.get("/inventory-recommendations", response_model=InventoryRecommendationResponse)
async def get_inventory_recommendations(
    store_id: uuid.UUID = Query(..., description="Store UUID"),
    db: AsyncSession = Depends(get_db_session),
):
    service = AnalyticsService(db)
    return await service.get_inventory_recommendations(store_id=store_id)
