import uuid

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.core.enums import WalletType, UserRole
from app.modules.wallets.schemas import (
    WalletResponse,
    WalletTransactionResponse,
    WalletTransactionCreate,
    WithdrawalRequestCreate,
    WithdrawalRequestResponse
)
from app.modules.wallets.service.wallets_service import WalletService
from app.core.pagination import PaginatedResponse, PaginationMetadata
from app.modules.auth.service.access_context_service import AccessContextService, TokenUser
from app.modules.logs.schemas import LogCreate
from app.modules.logs.service import LogSystemService

router = APIRouter()


@router.get("/store/{store_id}", response_model=WalletResponse)
async def get_wallet(
    store_id: uuid.UUID,
    type: WalletType = WalletType.DIGITAL,
    db: AsyncSession = Depends(get_db_session)
):
    service = WalletService(db)
    wallet = await service.get_wallet_by_store(store_id, type)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return wallet


@router.get("/business/{business_id}/hq", response_model=WalletResponse)
async def get_business_hq_wallet(
    business_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    service = WalletService(db)
    return await service.get_or_create_business_hq_wallet(business_id)


@router.get("/business/{business_id}/transactions", response_model=list[WalletTransactionResponse])
async def get_business_hq_transactions(
    business_id: uuid.UUID,
    type: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db_session)
):
    service = WalletService(db)
    return list(await service.get_business_hq_transactions(business_id, tx_type=type, search=search))


@router.post("/business/{business_id}/transactions", response_model=WalletTransactionResponse)
async def create_business_hq_transaction(
    business_id: uuid.UUID,
    schema: WalletTransactionCreate,
    request: Request,
    current_user: TokenUser = Depends(AccessContextService.get_token_user),
    db: AsyncSession = Depends(get_db_session)
):
    service = WalletService(db)
    tx = await service.create_business_hq_transaction(
        business_id=business_id,
        type=schema.type,
        category=schema.category,
        amount=schema.amount,
        notes=schema.note,
        date=schema.transaction_date
    )
    await db.commit()
    
    try:
        log_service = LogSystemService(db)
        platform = "web_enterprise"
        if current_user.role == UserRole.ADMIN:
            platform = "web_superadmin"
        elif current_user.role == UserRole.CUSTOMER:
            platform = "mobile_client"
        elif current_user.role == UserRole.SELLER:
            platform = "web_merchant"

        custom_platform = request.headers.get("X-Platform")
        if custom_platform in ["mobile_client", "web_merchant", "web_enterprise", "web_superadmin", "system"]:
            platform = custom_platform

        await log_service.create_log(
            schema=LogCreate(
                platform=platform,
                severity="INFO",
                event=f"Created HQ wallet transaction: {tx.type.value} ({tx.category.value}) - Amount: {tx.amount}",
                user_email=current_user.email,
                ip_address=request.client.host if request.client else None,
                details={
                    "transaction_id": str(tx.id),
                    "amount": float(tx.amount),
                    "type": tx.type.value,
                    "category": tx.category.value,
                    "business_id": str(business_id)
                }
            ),
            user_id=current_user.id
        )
    except Exception:
        pass
        
    return tx


@router.get("/store/{store_id}/balances")
async def get_store_wallet_balances(
    store_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    service = WalletService(db)
    digital_wallet = await service.get_wallet_by_store(store_id, WalletType.DIGITAL)
    offline_wallet = await service.get_wallet_by_store(store_id, WalletType.OFFLINE)
    return {
        "digital": digital_wallet.balance if digital_wallet else 0,
        "offline": offline_wallet.balance if offline_wallet else 0,
        "escrow": await service.get_store_escrow_balance(store_id)
    }


@router.get("/store/{store_id}/transactions", response_model=list[WalletTransactionResponse])
async def get_store_wallet_transactions(
    store_id: uuid.UUID,
    type: WalletType | None = None,
    db: AsyncSession = Depends(get_db_session)
):
    service = WalletService(db)
    return list(await service.get_store_all_transactions(store_id, type))


@router.post("/store/{store_id}/transactions", response_model=WalletTransactionResponse)
async def create_store_manual_transaction(
    store_id: uuid.UUID,
    schema: WalletTransactionCreate,
    request: Request,
    current_user: TokenUser = Depends(AccessContextService.get_token_user),
    db: AsyncSession = Depends(get_db_session)
):
    service = WalletService(db)
    tx = await service.create_manual_transaction(
        store_id=store_id,
        wallet_type=schema.wallet_type,
        type=schema.type,
        category=schema.category,
        amount=schema.amount,
        date=schema.transaction_date,
        notes=schema.note
    )
    await db.commit()
    
    try:
        log_service = LogSystemService(db)
        platform = "web_merchant"
        if current_user.role == UserRole.ADMIN:
            platform = "web_superadmin"
        elif current_user.role == UserRole.CUSTOMER:
            platform = "mobile_client"
        elif current_user.role == UserRole.OWNER:
            platform = "web_enterprise"

        custom_platform = request.headers.get("X-Platform")
        if custom_platform in ["mobile_client", "web_merchant", "web_enterprise", "web_superadmin", "system"]:
            platform = custom_platform

        await log_service.create_log(
            schema=LogCreate(
                platform=platform,
                severity="INFO",
                event=f"Created manual store transaction: {tx.type.value} - Amount: {tx.amount}",
                user_email=current_user.email,
                ip_address=request.client.host if request.client else None,
                details={
                    "transaction_id": str(tx.id),
                    "amount": float(tx.amount),
                    "type": tx.type.value,
                    "store_id": str(store_id)
                }
            ),
            user_id=current_user.id
        )
    except Exception:
        pass
        
    return tx


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_manual_transaction(
    transaction_id: uuid.UUID,
    request: Request,
    current_user: TokenUser = Depends(AccessContextService.get_token_user),
    db: AsyncSession = Depends(get_db_session)
):
    service = WalletService(db)
    await service.delete_manual_transaction(transaction_id)
    await db.commit()
    
    try:
        log_service = LogSystemService(db)
        platform = "web_merchant"
        if current_user.role == UserRole.ADMIN:
            platform = "web_superadmin"
        elif current_user.role == UserRole.CUSTOMER:
            platform = "mobile_client"
        elif current_user.role == UserRole.OWNER:
            platform = "web_enterprise"

        custom_platform = request.headers.get("X-Platform")
        if custom_platform in ["mobile_client", "web_merchant", "web_enterprise", "web_superadmin", "system"]:
            platform = custom_platform

        await log_service.create_log(
            schema=LogCreate(
                platform=platform,
                severity="INFO",
                event=f"Deleted manual transaction #{transaction_id}",
                user_email=current_user.email,
                ip_address=request.client.host if request.client else None,
                details={"transaction_id": str(transaction_id)}
            ),
            user_id=current_user.id
        )
    except Exception:
        pass


@router.post("/store/{store_id}/withdrawals", response_model=WithdrawalRequestResponse)
async def submit_store_withdrawal(
    store_id: uuid.UUID,
    schema: WithdrawalRequestCreate,
    request: Request,
    current_user: TokenUser = Depends(AccessContextService.get_token_user),
    db: AsyncSession = Depends(get_db_session)
):
    service = WalletService(db)
    payout = await service.submit_withdrawal(
        store_id=store_id,
        bank_name=schema.bank_name,
        account_number=schema.account_number,
        account_holder=schema.account_holder,
        amount=schema.amount,
        save_account=schema.save_account
    )
    await db.commit()
    
    try:
        log_service = LogSystemService(db)
        platform = "web_merchant"
        if current_user.role == UserRole.ADMIN:
            platform = "web_superadmin"
        elif current_user.role == UserRole.CUSTOMER:
            platform = "mobile_client"
        elif current_user.role == UserRole.OWNER:
            platform = "web_enterprise"

        custom_platform = request.headers.get("X-Platform")
        if custom_platform in ["mobile_client", "web_merchant", "web_enterprise", "web_superadmin", "system"]:
            platform = custom_platform

        await log_service.create_log(
            schema=LogCreate(
                platform=platform,
                severity="INFO",
                event=f"Submitted withdrawal request of {schema.amount} for store {store_id}",
                user_email=current_user.email,
                ip_address=request.client.host if request.client else None,
                details={
                    "withdrawal_id": str(payout.id),
                    "amount": float(schema.amount),
                    "store_id": str(store_id),
                    "bank_name": schema.bank_name
                }
            ),
            user_id=current_user.id
        )
    except Exception:
        pass
        
    return payout


@router.get("/store/{store_id}/withdrawals", response_model=list[WithdrawalRequestResponse])
async def get_store_withdrawals(
    store_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    service = WalletService(db)
    return list(await service.list_withdrawals(store_id))


@router.post("/withdrawals/{withdrawal_id}/cancel", response_model=WithdrawalRequestResponse)
async def cancel_store_withdrawal(
    withdrawal_id: uuid.UUID,
    request: Request,
    current_user: TokenUser = Depends(AccessContextService.get_token_user),
    db: AsyncSession = Depends(get_db_session)
):
    service = WalletService(db)
    payout = await service.cancel_withdrawal(withdrawal_id)
    await db.commit()
    
    try:
        log_service = LogSystemService(db)
        platform = "web_merchant"
        if current_user.role == UserRole.ADMIN:
            platform = "web_superadmin"
        elif current_user.role == UserRole.CUSTOMER:
            platform = "mobile_client"
        elif current_user.role == UserRole.OWNER:
            platform = "web_enterprise"

        custom_platform = request.headers.get("X-Platform")
        if custom_platform in ["mobile_client", "web_merchant", "web_enterprise", "web_superadmin", "system"]:
            platform = custom_platform

        await log_service.create_log(
            schema=LogCreate(
                platform=platform,
                severity="INFO",
                event=f"Cancelled withdrawal request #{withdrawal_id}",
                user_email=current_user.email,
                ip_address=request.client.host if request.client else None,
                details={"withdrawal_id": str(withdrawal_id)}
            ),
            user_id=current_user.id
        )
    except Exception:
        pass
        
    return payout


@router.get("/{wallet_id}/transactions", response_model=list[WalletTransactionResponse])
async def list_wallet_transactions(
    wallet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    service = WalletService(db)
    return list(await service.get_wallet_transactions(wallet_id))


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
