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
    CANCELLED = "cancelled"
    COMPLETED = "completed"


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
