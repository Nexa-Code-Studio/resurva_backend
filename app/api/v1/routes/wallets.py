import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.wallets.schemas import WalletResponse, WalletTransactionResponse
from app.modules.wallets.service.wallets_service import WalletService

from app.core.pagination import PaginatedResponse, PaginationMetadata

router = APIRouter()


@router.get("/store/{store_id}", response_model=WalletResponse)
async def get_wallet(
    store_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    service = WalletService(db)
    wallet = await service.get_wallet_by_store(store_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return wallet


@router.get("/store/{store_id}/transactions", response_model=list[WalletTransactionResponse])
async def get_store_wallet_transactions(
    store_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    service = WalletService(db)
    wallet = await service.get_wallet_by_store(store_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return await service.get_wallet_transactions(wallet.id)


@router.get("/{wallet_id}/transactions", response_model=list[WalletTransactionResponse])
async def list_wallet_transactions(
    wallet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    service = WalletService(db)
    return await service.get_wallet_transactions(wallet_id)


@router.get("/", response_model=PaginatedResponse[WalletResponse])
async def list_wallets_paginated(
    page: int = 1,
    page_size: int = 20,
    store_id: uuid.UUID | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_db_session)
):
    service = WalletService(db)
    items, total = await service.list_wallets_paginated(
        page=page,
        page_size=page_size,
        store_id=store_id,
        sort_by=sort_by,
        sort_order=sort_order
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        items=list(items),
        pagination=PaginationMetadata(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages
        )
    )


@router.get("/transactions/all", response_model=PaginatedResponse[WalletTransactionResponse])
async def list_all_wallet_transactions_paginated(
    page: int = 1,
    page_size: int = 20,
    wallet_id: uuid.UUID | None = None,
    store_id: uuid.UUID | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_db_session)
):
    service = WalletService(db)
    items, total = await service.list_wallet_transactions_paginated(
        page=page,
        page_size=page_size,
        wallet_id=wallet_id,
        store_id=store_id,
        sort_by=sort_by,
        sort_order=sort_order
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        items=list(items),
        pagination=PaginationMetadata(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages
        )
    )

