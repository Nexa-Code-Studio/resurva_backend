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
    AIInsightsResponse,
    EnterpriseAIInsightsResponse,
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
    store_id: uuid.UUID | None = Query(None, description="Filter by Store UUID"),
    period: str = Query("6bulan", description="6bulan, tahun_ini, or semua"),
    db: AsyncSession = Depends(get_db_session),
):
    service = AnalyticsService(db)
    return await service.get_enterprise_waste_impact_analytics(
        business_id=business_id,
        store_id=store_id,
        period=period
    )


@router.get("/enterprise/ai-insights", response_model=EnterpriseAIInsightsResponse)
async def get_enterprise_ai_insights(
    business_id: uuid.UUID = Query(..., description="Business UUID"),
    db: AsyncSession = Depends(get_db_session),
):
    service = AnalyticsService(db)
    return await service.get_enterprise_ai_insights(business_id=business_id)





@router.get("/finance", response_model=FinancialAnalyticsResponse)
async def get_financial_analytics(
    store_id: uuid.UUID = Query(..., description="Store UUID"),
    timeframe: str = Query("weekly", description="weekly or monthly"),
    tx_type: str = Query("in", description="in or out for category breakdown"),
    date_offset: int = Query(0, description="Offset multiplier"),
    db: AsyncSession = Depends(get_db_session),
):
    service = AnalyticsService(db)
    return await service.get_finance_analytics(
        store_id=store_id, timeframe=timeframe, tx_type=tx_type, date_offset=date_offset
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
    timeframe: str = Query("all", description="Timeframe filter (all, today, 7d, 30d, this_month)"),
    city: str = Query("all", description="City filter"),
    db: AsyncSession = Depends(get_db_session)
):
    service = AnalyticsService(db)
    return await service.get_superadmin_stats(timeframe=timeframe, city=city)


@router.get("/superadmin/cities", response_model=list[str])
async def get_superadmin_cities(
    db: AsyncSession = Depends(get_db_session)
):
    service = AnalyticsService(db)
    return await service.get_superadmin_cities()


@router.get("/superadmin/ai-insights", response_model=EnterpriseAIInsightsResponse)
async def get_superadmin_ai_insights(
    db: AsyncSession = Depends(get_db_session)
):
    service = AnalyticsService(db)
    return await service.get_superadmin_ai_insights()


@router.get("/ai-insights", response_model=AIInsightsResponse)
async def get_ai_insights(
    store_id: uuid.UUID = Query(..., description="Store UUID"),
    db: AsyncSession = Depends(get_db_session),
):
    service = AnalyticsService(db)
    return await service.get_ai_insights(store_id=store_id)


