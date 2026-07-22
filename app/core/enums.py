from enum import Enum


class UserRole(str, Enum):
    CUSTOMER = "customer"
    SELLER = "seller"
    OWNER = "owner"
    ADMIN = "admin"


class ProductType(str, Enum):
    READY_TO_EAT = "ready-to-eat"
    PACKAGED = "packaged"
    BAKERY = "bakery"
    PRODUCE = "produce"
    OTHER = "other"


class ExpiryAlertStatus(str, Enum):
    UPCOMING = "upcoming"
    CRITICAL = "critical"
    EXPIRED = "expired"


class DiscountType(str, Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"


class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    CONFIRMED = "confirmed"
    PREPARED = "prepared"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

    @classmethod
    def _missing_(cls, value):
        if not isinstance(value, str):
            return None
        val_lower = value.lower().strip()
        for member in cls:
            if member.value == val_lower or member.name.lower() == val_lower:
                return member
        id_map = {
            "menunggu pembayaran": cls.PENDING,
            "menunggu konfirmasi": cls.PAID,
            "baru": cls.PAID,
            "disiapkan": cls.CONFIRMED,
            "siap diambil": cls.PREPARED,
            "selesai": cls.COMPLETED,
            "dibatalkan": cls.CANCELLED,
            "batal": cls.CANCELLED
        }
        if val_lower in id_map:
            return id_map[val_lower]
        return None


class OrderChannel(str, Enum):
    MARKETPLACE = "marketplace"
    KASIR = "kasir"


class TransactionStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    QRIS = "qris"
    TRANSFER = "transfer"
    CASH = "cash"
    OVO = "ovo"
    GOPAY = "gopay"
    OTHER = "other"


class WalletTransactionType(str, Enum):
    CREDIT = "credit"
    DEBIT = "debit"
    WITHDRAWAL = "withdrawal"


class WalletType(str, Enum):
    DIGITAL = "digital"
    OFFLINE = "offline"
    HQ = "hq"


class WalletTransactionCategory(str, Enum):
    # Pemasukan (Credit)
    CAT_SALES = "catSales"
    CAT_CAPITAL = "catCapital"
    CAT_ADJUSTMENT = "catAdjustment"
    CAT_BRANCH_DEPOSIT = "catBranchDeposit"
    CAT_INVESTMENT = "catInvestment"
    CAT_SPONSORSHIP = "catSponsorship"

    # Pengeluaran (Debit)
    CAT_INGREDIENTS = "catIngredients"
    CAT_SALARY = "catSalary"
    CAT_UTILITIES = "catUtilities"
    CAT_RENT = "catRent"
    CAT_LOGISTICS = "catLogistics"
    CAT_MARKETING = "catMarketing"
    CAT_MAINTENANCE = "catMaintenance"
    CAT_WITHDRAWAL = "catWithdrawal"
    CAT_IT_INFRA = "catItInfra"
    CAT_NATIONAL_MARKETING = "catNationalMarketing"
    CAT_OFFICE_OPS = "catOfficeOps"

    # Umum
    CAT_OTHERS = "catOthers"

    @classmethod
    def _missing_(cls, value):
        if not isinstance(value, str):
            return None
        val_lower = value.lower().strip()
        for member in cls:
            if member.value.lower() == val_lower or member.name.lower() == val_lower:
                return member
        cat_map = {
            "setoran cabang": cls.CAT_BRANCH_DEPOSIT,
            "investasi": cls.CAT_INVESTMENT,
            "pendanaan / investasi": cls.CAT_INVESTMENT,
            "sponsorship": cls.CAT_SPONSORSHIP,
            "sponsorship terpusat": cls.CAT_SPONSORSHIP,
            "gaji & kompensasi": cls.CAT_SALARY,
            "gaji staf hq": cls.CAT_SALARY,
            "marketing nasional": cls.CAT_NATIONAL_MARKETING,
            "biaya marketing nasional": cls.CAT_NATIONAL_MARKETING,
            "infrastruktur it": cls.CAT_IT_INFRA,
            "sewa server & infrastruktur it": cls.CAT_IT_INFRA,
            "operasional kantor": cls.CAT_OFFICE_OPS,
            "biaya operasional kantor hq": cls.CAT_OFFICE_OPS,
            "pemasukan lainnya": cls.CAT_OTHERS,
            "pengeluaran lainnya": cls.CAT_OTHERS,
            "lainnya": cls.CAT_OTHERS,
        }
        if val_lower in cat_map:
            return cat_map[val_lower]
        return None


