import uuid
from typing import Sequence
from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.verifications.models import PartnerVerification
from app.modules.verifications.schemas import PartnerVerificationCreate, PartnerVerificationStatusUpdate
from app.modules.business.models import Business
from app.modules.stores.models import Store, StoreCategory
from app.modules.wallets.models import Wallet
from app.core.enums import WalletType, UserRole
from app.modules.users.models import User
from app.core.security import get_password_hash


class VerificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_verification_request(self, schema: PartnerVerificationCreate) -> PartnerVerification:
        # Check if email is already taken in verifications or users
        if schema.email:
            existing_user_query = await self.db.execute(select(User).where(User.email == schema.email))
            if existing_user_query.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email sudah terdaftar di sistem."
                )

        verification = PartnerVerification(
            partner_type=schema.partner_type.upper(),
            name=schema.name,
            owner_or_director=schema.owner_or_director,
            category=schema.category,
            branch_count=schema.branch_count,
            address=schema.address,
            email=schema.email,
            phone=schema.phone,
            documents=schema.documents,
            status="PENDING"
        )
        self.db.add(verification)
        await self.db.commit()
        await self.db.refresh(verification)
        return verification

    async def list_verifications(
        self, partner_type: str | None = None, status_filter: str | None = None
    ) -> Sequence[PartnerVerification]:
        query = select(PartnerVerification)
        conditions = []
        if partner_type:
            conditions.append(PartnerVerification.partner_type == partner_type.upper())
        if status_filter:
            conditions.append(PartnerVerification.status == status_filter.upper())
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(PartnerVerification.created_at.desc())
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_verification(self, verification_id: uuid.UUID) -> PartnerVerification | None:
        result = await self.db.execute(
            select(PartnerVerification).where(PartnerVerification.id == verification_id)
        )
        return result.scalar_one_or_none()

    async def update_verification_status(
        self, verification_id: uuid.UUID, schema: PartnerVerificationStatusUpdate
    ) -> PartnerVerification:
        verification = await self.get_verification(verification_id)
        if not verification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pengajuan verifikasi tidak ditemukan."
            )
        
        if verification.status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pengajuan ini sudah diproses sebelumnya."
            )

        new_status = schema.status.upper()
        verification.status = new_status
        if new_status == "REJECTED":
            verification.rejection_reason = schema.rejection_reason
        elif new_status == "APPROVED":
            # Automatically provision Business, Store, User accounts
            if verification.partner_type == "MERCHANT":
                # 1. Create a Business entity for the single-outlet merchant
                business = Business(
                    name=verification.name,
                    email=verification.email or f"{uuid.uuid4().hex[:8]}@merchant.resurva.id",
                    phone=verification.phone,
                    address=verification.address,
                    pic=verification.owner_or_director,
                )
                self.db.add(business)
                await self.db.flush()

                # Resolve category
                category_id = None
                if verification.category:
                    cat_res = await self.db.execute(
                        select(StoreCategory).where(StoreCategory.name == verification.category)
                    )
                    cat_obj = cat_res.scalar_one_or_none()
                    if not cat_obj:
                        cat_obj = StoreCategory(name=verification.category)
                        self.db.add(cat_obj)
                        await self.db.flush()
                    category_id = cat_obj.id

                # 2. Create the Store entity
                store = Store(
                    business_id=business.id,
                    name=verification.name,
                    address=verification.address,
                    city="Malang",  # default
                    latitude=-7.98,
                    longitude=112.63,
                    category_id=category_id,
                    is_active=True,
                )
                self.db.add(store)
                await self.db.flush()

                # 3. Initialize digital & offline wallets
                digital_wallet = Wallet(store_id=store.id, type=WalletType.DIGITAL, balance=0)
                offline_wallet = Wallet(store_id=store.id, type=WalletType.OFFLINE, balance=0)
                self.db.add_all([digital_wallet, offline_wallet])
                await self.db.flush()

                # 4. Create User (SELLER) account
                username = verification.email.split("@")[0] if verification.email else f"merchant_{uuid.uuid4().hex[:6]}"
                password_hash = get_password_hash("password123")  # default temporary password
                user = User(
                    username=username,
                    email=verification.email or f"{username}@merchant.resurva.id",
                    password=password_hash,
                    role=UserRole.SELLER,
                    store_id=store.id,
                    business_id=business.id
                )
                self.db.add(user)
                await self.db.flush()

            elif verification.partner_type == "ENTERPRISE":
                # 1. Create a Business entity for the enterprise
                business = Business(
                    name=verification.name,
                    email=verification.email or f"{uuid.uuid4().hex[:8]}@enterprise.resurva.id",
                    phone=verification.phone,
                    address=verification.address,
                    pic=verification.owner_or_director,
                )
                self.db.add(business)
                await self.db.flush()

                # 2. Create User (OWNER) account
                username = verification.email.split("@")[0] if verification.email else f"enterprise_{uuid.uuid4().hex[:6]}"
                password_hash = get_password_hash("password123")  # default temporary password
                user = User(
                    username=username,
                    email=verification.email or f"{username}@enterprise.resurva.id",
                    password=password_hash,
                    role=UserRole.OWNER,
                    business_id=business.id
                )
                self.db.add(user)
                await self.db.flush()

        await self.db.commit()
        await self.db.refresh(verification)
        return verification
