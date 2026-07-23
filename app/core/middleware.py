import time
import logging
from starlette.types import ASGIApp, Receive, Scope, Send
from app.db.session import SessionLocal
from app.modules.logs.models import LogSystem
from app.modules.auth.service.access_context_service import AccessContextService
from app.core.enums import UserRole

logger = logging.getLogger("app.middleware.logging")


class SystemLoggingMiddleware:
    """
    Pure ASGI middleware for global request-response logging.
    Avoids using BaseHTTPMiddleware to prevent event loop mismatch issues in async test environments.
    """
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        path = scope["path"]

        # Only log write operations (POST, PUT, PATCH, DELETE) and skip logging endpoint itself
        if method not in ["POST", "PUT", "PATCH", "DELETE"] or "/api/v1/logs" in path:
            await self.app(scope, receive, send)
            return

        status_code = [200]
        start_time = time.time()

        # Wrap send function to capture the response status code
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code[0] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            # Execute logging in the finally block after the request/response completes
            try:
                duration = time.time() - start_time
                sc = status_code[0]

                # Severity mapping
                if sc >= 500:
                    severity = "ERROR"
                elif sc >= 400:
                    severity = "WARNING"
                else:
                    severity = "INFO"

                user_id = None
                user_email = None
                platform = "system"

                # Parse headers from scope (headers are key-value tuples of bytes)
                headers_dict = dict(scope.get("headers", []))
                
                authorization = headers_dict.get(b"authorization", b"").decode("utf-8", errors="ignore")
                if authorization and authorization.startswith("Bearer "):
                    token = authorization.split(" ")[1]
                    try:
                        token_user = await AccessContextService.get_token_user(token)
                        user_id = token_user.id
                        user_email = token_user.email

                        # Map default platform from user role
                        role = token_user.role
                        if role == UserRole.ADMIN:
                            platform = "web_superadmin"
                        elif role == UserRole.CUSTOMER:
                            platform = "mobile_client"
                        elif role == UserRole.SELLER:
                            platform = "web_merchant"
                        elif role == UserRole.OWNER:
                            platform = "web_enterprise"
                    except Exception:
                        pass

                custom_platform = headers_dict.get(b"x-platform", b"").decode("utf-8", errors="ignore")
                if custom_platform in ["mobile_client", "web_merchant", "web_enterprise", "web_superadmin", "system"]:
                    platform = custom_platform

                # Client IP address from scope
                client_ip = None
                if "client" in scope and scope["client"]:
                    client_ip = scope["client"][0]

                clean_path = path.replace("/api/v1", "")
                action_map = {
                    "POST": "Membuat data baru",
                    "PUT": "Memperbarui data",
                    "PATCH": "Memperbarui sebagian data",
                    "DELETE": "Menghapus data"
                }
                action_desc = action_map.get(method, "Aktivitas")
                event_desc = f"{action_desc} di {clean_path} (Status: {sc})"

                details = {
                    "method": method,
                    "path": path,
                    "status_code": sc,
                    "duration_seconds": round(duration, 4),
                    "ip_address": client_ip
                }

                # Record log
                async with SessionLocal() as db:
                    log_entry = LogSystem(
                        platform=platform,
                        severity=severity,
                        event=event_desc,
                        user_id=user_id,
                        user_email=user_email,
                        ip_address=client_ip,
                        details=details
                    )
                    db.add(log_entry)
                    await db.commit()
            except Exception as e:
                logger.error(f"Error in SystemLoggingMiddleware: {e}", exc_info=True)
