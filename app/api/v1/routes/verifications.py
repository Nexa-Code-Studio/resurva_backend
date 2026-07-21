import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.verifications.schemas import (
    PartnerVerificationCreate,
    PartnerVerificationResponse,
    PartnerVerificationStatusUpdate,
)
from app.modules.verifications.service.verification_service import VerificationService

router = APIRouter()


@router.post("/", response_model=PartnerVerificationResponse, status_code=status.HTTP_201_CREATED)
async def create_verification_request(
    schema: PartnerVerificationCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Submit a new partner registration (Merchant or Enterprise) from the landing page."""
    service = VerificationService(db)
    return await service.create_verification_request(schema)


@router.get("/", response_model=List[PartnerVerificationResponse])
async def list_verifications(
    partner_type: str | None = None,
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Retrieve all verification requests, filtered by type (MERCHANT, ENTERPRISE) or status."""
    service = VerificationService(db)
    return await service.list_verifications(partner_type=partner_type, status_filter=status_filter)


@router.get("/{verification_id}", response_model=PartnerVerificationResponse)
async def get_verification(
    verification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Retrieve a single partner verification request by UUID."""
    service = VerificationService(db)
    verification = await service.get_verification(verification_id)
    if not verification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pengajuan verifikasi tidak ditemukan."
        )
    return verification


@router.patch("/{verification_id}/status", response_model=PartnerVerificationResponse)
async def update_verification_status(
    verification_id: uuid.UUID,
    schema: PartnerVerificationStatusUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Approve or reject a verification request (Superadmin Action)."""
    service = VerificationService(db)
    return await service.update_verification_status(verification_id, schema)
