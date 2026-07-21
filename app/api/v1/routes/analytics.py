import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.analytics.schemas import (
    FinancialAnalyticsResponse,
    SalesAnalyticsResponse,
    InventoryRecommendationResponse,
    EnterpriseFinanceAnalyticsResponse,
    EnterpriseLeaderboardResponse,
    SustainabilityAnalyticsResponse,
    EnterpriseWrappedResponse,
    EnterpriseWasteImpactAnalyticsResponse,
    SuperadminDashboardStatsResponse,
)
from app.modules.analytics.service.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/enterprise/finance", response_model=EnterpriseFinanceAnalyticsResponse)
async def get_enterprise_financial_analytics(
    business_id: uuid.UUID = Query(..., description="Business UUID"),
    db: AsyncSession = Depends(get_db_session),
):
    service = AnalyticsService(db)
    return await service.get_enterprise_finance_analytics(business_id=business_id)


@router.get("/enterprise/leaderboard", response_model=EnterpriseLeaderboardResponse)
async def get_enterprise_leaderboard(
    business_id: uuid.UUID = Query(..., description="Business UUID"),
    period: str = Query("Bulan Ini", description="Bulan Ini, Bulan Lalu, or Tahun Ini"),
    category: str = Query("Semua Kategori", description="Filter category"),
    sort_by: str = Query("revenue", description="revenue, saved_kg, or co2e"),
    db: AsyncSession = Depends(get_db_session),
):
    service = AnalyticsService(db)
    return await service.get_enterprise_leaderboard(
        business_id=business_id,
        period=period,
        category=category,
        sort_by=sort_by
    )


@router.get("/enterprise/sustainability", response_model=SustainabilityAnalyticsResponse)
async def get_enterprise_sustainability(
    business_id: uuid.UUID = Query(..., description="Business UUID"),
    period: str = Query("6bulan", description="6bulan, tahun_ini, or semua"),
    db: AsyncSession = Depends(get_db_session),
):
    service = AnalyticsService(db)
    return await service.get_enterprise_sustainability(
        business_id=business_id,
        period=period
    )


@router.get("/enterprise/wrapped", response_model=EnterpriseWrappedResponse)
async def get_enterprise_wrapped(
    business_id: uuid.UUID = Query(..., description="Business UUID"),
    year: int = Query(2024, description="Target year"),
    db: AsyncSession = Depends(get_db_session),
):
    service = AnalyticsService(db)
    return await service.get_enterprise_wrapped(
        business_id=business_id,
        year=year
    )


@router.get("/enterprise/waste-impact", response_model=EnterpriseWasteImpactAnalyticsResponse)
async def get_enterprise_waste_impact_analytics(
    business_id: uuid.UUID = Query(..., description="Business UUID"),
    db: AsyncSession = Depends(get_db_session),
):
    service = AnalyticsService(db)
    return await service.get_enterprise_waste_impact_analytics(business_id=business_id)





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


@router.get("/superadmin/stats", response_model=SuperadminDashboardStatsResponse)
async def get_superadmin_dashboard_stats(
    db: AsyncSession = Depends(get_db_session)
):
    service = AnalyticsService(db)
    return await service.get_superadmin_stats()
