import uuid
import json
from datetime import date, datetime
from typing import Any
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.base_tool import BaseMCPTool
from app.modules.summaries.models import DailySummary, MonthlySummary
from app.core.redis import get_redis_client
from app.modules.chat.service.tool_call_service import json_serial



class SalesSummaryInput(BaseModel):
    store_id: str = Field(description="UUID of the store to fetch sales data for")
    period: str = Field("daily", description="Summary period: 'daily', 'monthly', or 'range'")
    date: str | None = Field(None, description="For 'daily' period: Date in format YYYY-MM-DD. Defaults to today.")
    year: int | None = Field(None, description="For 'monthly' period: Year of the summary.")
    month: int | None = Field(None, description="For 'monthly' period: Month (1-12) of the summary.")
    start_date: str | None = Field(None, description="For 'range' period: Start date in format YYYY-MM-DD.")
    end_date: str | None = Field(None, description="For 'range' period: End date in format YYYY-MM-DD.")


class SalesSummaryTool(BaseMCPTool):
    name = "sales_summary"
    description = (
        "Retrieves sales statistics, revenue summaries, platform fees, refunds, and order counts for a store. "
        "Supports 'daily' period, 'monthly' period, and 'range' period (requires start_date and end_date)."
    )
    input_schema = SalesSummaryInput

    async def execute(
        self,
        db: AsyncSession,
        store_id: str,
        period: str = "daily",
        date: str | None = None,
        year: int | None = None,
        month: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None
    ) -> dict[str, Any]:
        cache_key = f"cache:sales_summary:{store_id}:{period}:{date or 'none'}:{year or 'none'}:{month or 'none'}:{start_date or 'none'}:{end_date or 'none'}"
        try:
            redis_client = await get_redis_client()
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception:
            redis_client = None

        result = await self._execute_db(db, store_id, period, date, year, month, start_date, end_date)

        if redis_client and "error" not in result and "message" not in result:

            try:
                await redis_client.set(cache_key, json.dumps(result, default=json_serial), ex=300)
            except Exception:
                pass


        return result

    async def _execute_db(
        self,
        db: AsyncSession,
        store_id: str,
        period: str = "daily",
        date_str: str | None = None,
        year: int | None = None,
        month: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None
    ) -> dict[str, Any]:
        store_uuid = uuid.UUID(store_id)
        from sqlalchemy import func, extract
        from app.modules.transactions.models import Transaction
        from app.core.enums import TransactionStatus

        if period == "daily":
            if date_str:
                try:
                    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    return {"error": "Format tanggal salah. Gunakan YYYY-MM-DD."}
            else:
                from datetime import date as dt_date
                target_date = dt_date.today()

            q = select(DailySummary).where(
                DailySummary.store_id == store_uuid,
                DailySummary.summary_date == target_date
            )
            result = await db.execute(q)
            row = result.scalar_one_or_none()
            
            # Query platform fee, refund, failed for target_date
            fee_q = select(func.coalesce(func.sum(Transaction.platform_fee), 0)).where(
                Transaction.store_id == store_uuid,
                func.date(Transaction.created_at) == target_date,
                Transaction.status == TransactionStatus.SUCCESS
            )
            fee_res = await db.execute(fee_q)
            total_platform_fee = fee_res.scalar()

            refund_q = select(func.coalesce(func.sum(Transaction.gross_amount), 0)).where(
                Transaction.store_id == store_uuid,
                func.date(Transaction.created_at) == target_date,
                Transaction.status == TransactionStatus.REFUNDED
            )
            refund_res = await db.execute(refund_q)
            total_refunded_amount = refund_res.scalar()

            failed_q = select(func.count(Transaction.id)).where(
                Transaction.store_id == store_uuid,
                func.date(Transaction.created_at) == target_date,
                Transaction.status == TransactionStatus.FAILED
            )
            failed_res = await db.execute(failed_q)
            failed_orders_count = failed_res.scalar()

            if not row:
                return {
                    "store_id": store_id,
                    "period": period,
                    "date": str(target_date),
                    "message": f"Belum ada data ringkasan harian untuk tanggal {target_date}",
                    "total_platform_fee": int(total_platform_fee),
                    "total_refunded_amount": int(total_refunded_amount),
                    "failed_orders_count": int(failed_orders_count)
                }

            return {
                "store_id": store_id,
                "period": period,
                "date": str(row.summary_date),
                "total_orders": row.total_orders,
                "total_revenue": row.total_revenue,
                "total_discount_given": row.total_discount_given,
                "items_sold": row.items_sold,
                "carbon_saved_kg": round(row.carbon_saved_kg, 2),
                "expiry_alerts_count": row.expiry_alerts_count,
                "total_platform_fee": int(total_platform_fee),
                "total_refunded_amount": int(total_refunded_amount),
                "failed_orders_count": int(failed_orders_count)
            }

        elif period == "monthly":
            target_year = year or datetime.now().year
            target_month = month or datetime.now().month

            q = select(MonthlySummary).where(
                MonthlySummary.store_id == store_uuid,
                MonthlySummary.year == target_year,
                MonthlySummary.month == target_month
            )
            result = await db.execute(q)
            row = result.scalar_one_or_none()

            # Query platform fee, refund, failed for target_month/year
            fee_q = select(func.coalesce(func.sum(Transaction.platform_fee), 0)).where(
                Transaction.store_id == store_uuid,
                extract('year', Transaction.created_at) == target_year,
                extract('month', Transaction.created_at) == target_month,
                Transaction.status == TransactionStatus.SUCCESS
            )
            fee_res = await db.execute(fee_q)
            total_platform_fee = fee_res.scalar()

            refund_q = select(func.coalesce(func.sum(Transaction.gross_amount), 0)).where(
                Transaction.store_id == store_uuid,
                extract('year', Transaction.created_at) == target_year,
                extract('month', Transaction.created_at) == target_month,
                Transaction.status == TransactionStatus.REFUNDED
            )
            refund_res = await db.execute(refund_q)
            total_refunded_amount = refund_res.scalar()

            failed_q = select(func.count(Transaction.id)).where(
                Transaction.store_id == store_uuid,
                extract('year', Transaction.created_at) == target_year,
                extract('month', Transaction.created_at) == target_month,
                Transaction.status == TransactionStatus.FAILED
            )
            failed_res = await db.execute(failed_q)
            failed_orders_count = failed_res.scalar()

            if not row:
                return {
                    "store_id": store_id,
                    "period": period,
                    "year": target_year,
                    "month": target_month,
                    "message": f"Belum ada data ringkasan bulanan untuk periode {target_year}-{target_month:02d}",
                    "total_platform_fee": int(total_platform_fee),
                    "total_refunded_amount": int(total_refunded_amount),
                    "failed_orders_count": int(failed_orders_count)
                }

            return {
                "store_id": store_id,
                "period": period,
                "year": row.year,
                "month": row.month,
                "total_orders": row.total_orders,
                "total_revenue": row.total_revenue,
                "total_discount_given": row.total_discount_given,
                "new_customers": row.new_customers,
                "carbon_saved_kg": round(row.carbon_saved_kg, 2),
                "avg_rating": round(row.avg_rating, 1),
                "total_platform_fee": int(total_platform_fee),
                "total_refunded_amount": int(total_refunded_amount),
                "failed_orders_count": int(failed_orders_count)
            }

        elif period == "range":
            if not start_date or not end_date:
                return {"error": "Untuk period 'range', start_date dan end_date wajib diisi dengan format YYYY-MM-DD."}
            
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
                end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                return {"error": "Format tanggal salah. Gunakan YYYY-MM-DD."}

            if start_dt > end_dt:
                return {"error": "start_date tidak boleh lebih besar dari end_date."}

            # Query DailySummary for the range and sum
            q = select(
                func.coalesce(func.sum(DailySummary.total_orders), 0).label("total_orders"),
                func.coalesce(func.sum(DailySummary.total_revenue), 0).label("total_revenue"),
                func.coalesce(func.sum(DailySummary.total_discount_given), 0).label("total_discount_given"),
                func.coalesce(func.sum(DailySummary.items_sold), 0).label("items_sold"),
                func.coalesce(func.sum(DailySummary.carbon_saved_kg), 0.0).label("carbon_saved_kg"),
                func.coalesce(func.sum(DailySummary.expiry_alerts_count), 0).label("expiry_alerts_count")
            ).where(
                DailySummary.store_id == store_uuid,
                DailySummary.summary_date >= start_dt,
                DailySummary.summary_date <= end_dt
            )
            result = await db.execute(q)
            summary_row = result.fetchone()
            
            # Platform Fee sum
            fee_q = select(func.coalesce(func.sum(Transaction.platform_fee), 0)).where(
                Transaction.store_id == store_uuid,
                func.date(Transaction.created_at) >= start_dt,
                func.date(Transaction.created_at) <= end_dt,
                Transaction.status == TransactionStatus.SUCCESS
            )
            fee_res = await db.execute(fee_q)
            total_platform_fee = fee_res.scalar()

            # Refunded gross amount sum
            refund_q = select(func.coalesce(func.sum(Transaction.gross_amount), 0)).where(
                Transaction.store_id == store_uuid,
                func.date(Transaction.created_at) >= start_dt,
                func.date(Transaction.created_at) <= end_dt,
                Transaction.status == TransactionStatus.REFUNDED
            )
            refund_res = await db.execute(refund_q)
            total_refunded_amount = refund_res.scalar()

            # Count failed transactions
            failed_q = select(func.count(Transaction.id)).where(
                Transaction.store_id == store_uuid,
                func.date(Transaction.created_at) >= start_dt,
                func.date(Transaction.created_at) <= end_dt,
                Transaction.status == TransactionStatus.FAILED
            )
            failed_res = await db.execute(failed_q)
            failed_orders_count = failed_res.scalar()

            return {
                "store_id": store_id,
                "period": period,
                "start_date": str(start_dt),
                "end_date": str(end_dt),
                "total_orders": int(summary_row.total_orders) if summary_row else 0,
                "total_revenue": int(summary_row.total_revenue) if summary_row else 0,
                "total_discount_given": int(summary_row.total_discount_given) if summary_row else 0,
                "items_sold": int(summary_row.items_sold) if summary_row else 0,
                "carbon_saved_kg": round(float(summary_row.carbon_saved_kg), 2) if summary_row else 0.0,
                "expiry_alerts_count": int(summary_row.expiry_alerts_count) if summary_row else 0,
                "total_platform_fee": int(total_platform_fee),
                "total_refunded_amount": int(total_refunded_amount),
                "failed_orders_count": int(failed_orders_count)
            }

        else:
            return {"error": f"Period '{period}' tidak didukung. Gunakan 'daily', 'monthly', atau 'range'."}
