from fastapi import APIRouter

from app.api.v1.routes import (
    auth,
    business,
    chat,
    discounts,
    inventory,
    orders,
    products,
    reports,
    stores,
    users,
    wallets,
    transactions,
    reviews,
    carbon,
    analytics,
    verifications,
    cart,
    logs,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(logs.router, prefix="/logs", tags=["System Logs"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(business.router, prefix="/businesses", tags=["Businesses"])
api_router.include_router(business.router, prefix="/business", tags=["Businesses"])

api_router.include_router(stores.router, prefix="/stores", tags=["Stores"])
api_router.include_router(products.router, prefix="/products", tags=["Products"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["Inventory"])
api_router.include_router(orders.router, prefix="/orders", tags=["Orders"])
api_router.include_router(cart.router, prefix="/cart", tags=["Cart"])
api_router.include_router(discounts.router, prefix="/discounts", tags=["Discounts"])
api_router.include_router(wallets.router, prefix="/wallets", tags=["Wallets"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["Reviews"])
api_router.include_router(carbon.router, prefix="/carbon", tags=["Carbon Logs"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(verifications.router, prefix="/verifications", tags=["Verifications"])


