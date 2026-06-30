import logging
from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole
from app.mcp.registry import mcp_registry

logger = logging.getLogger(__name__)


class MCPOrchestrator:
    @staticmethod
    async def execute_tool(
        db: AsyncSession,
        role: UserRole,
        allowed_store_ids: list[str] | set[str],
        name: str,
        arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Looks up a tool in the global registry, validates role and store boundaries,
        and executes it with provided arguments and db session.
        """
        tool = mcp_registry.get_tool(name)
        if not tool:
            logger.error(f"MCP tool not found in registry: {name}")
            return {
                "success": False,
                "error": f"Tool '{name}' is not a registered MCP tool."
            }

        # Check role permissions
        if role not in tool.allowed_roles:
            logger.warning(f"User role '{role}' is not allowed to run tool '{name}'")
            return {
                "success": False,
                "error": f"Peran Anda ({role.value}) tidak diizinkan menggunakan tool '{name}'."
            }

        try:
            # Validate input arguments against Pydantic schema
            try:
                validated_input = tool.input_schema(**arguments)
                input_dict = validated_input.model_dump()
            except Exception as ve:
                logger.warning(f"Validation error for MCP tool '{name}': {ve}")
                return {
                    "success": False,
                    "error": (
                        f"Argumen input untuk tool '{name}' tidak valid. Detail: {ve}. "
                        "PENTING: Pastikan parameter ID (seperti 'product_id' atau 'store_id') menggunakan format UUID 36-karakter yang valid, bukan nama string mentah. "
                        "Jika Anda tidak memiliki UUID produk, panggil tool 'product_search' terlebih dahulu untuk mencarinya."
                    )
                }

            # Security Guard: verify store_id boundaries if present in tool input for Seller and Owner roles
            if role in [UserRole.SELLER, UserRole.OWNER]:
                store_id_arg = input_dict.get("store_id")
                if store_id_arg is not None:
                    # Normalize to string for comparison
                    store_id_str = str(store_id_arg)
                    allowed_strs = {str(sid) for sid in allowed_store_ids}
                    if store_id_str not in allowed_strs:
                        logger.warning(f"Access denied: store_id '{store_id_str}' not in allowed stores {allowed_strs}")
                        return {
                            "success": False,
                            "error": f"Akses ditolak ke store {store_id_str}."
                        }

            # Execute tool
            logger.info(f"Executing MCP tool '{name}' with arguments: {input_dict}")
            try:
                result = await tool.execute(db=db, **input_dict)
                return {
                    "success": True,
                    "tool": name,
                    "data": result
                }
            except ValueError as val_err:
                logger.warning(f"Value/Parsing error during execution of tool '{name}': {val_err}")
                return {
                    "success": False,
                    "error": (
                        f"Gagal memproses argumen karena format nilai salah. Detail: {val_err}. "
                        "PENTING: Nilai ID (seperti product_id atau store_id) harus berupa UUID heksadesimal 36-karakter yang valid (contoh: '123e4567-e89b-12d3-a456-426614174000'). "
                        "JANGAN mengirimkan nama produk (seperti 'muffin-blueberry') ke parameter ID. "
                        "Gunakan tool 'product_search' untuk mencari produk berdasarkan namanya terlebih dahulu agar mendapatkan UUID-nya."
                    )
                }
        except Exception as e:
            logger.error(f"Failed executing MCP tool '{name}': {e}", exc_info=True)
            return {
                "success": False,
                "tool": name,
                "error": str(e)
            }
