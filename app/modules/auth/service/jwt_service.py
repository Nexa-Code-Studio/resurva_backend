
from typing import Any

import jwt
from fastapi import HTTPException, status

from app.core import security


class JWTService:
    @staticmethod
    def generate_access_token(
        user_id: Any,
        role: str,
        email: str,
        username: str,
        business_id: Any = None,
        store_id: Any = None,
        created_at: Any = None
    ) -> str:
        data = {
            "role": role,
            "email": email,
            "username": username,
            "business_id": str(business_id) if business_id else None,
            "store_id": str(store_id) if store_id else None,
            "created_at": created_at.isoformat() if created_at else None,
        }
        return security.create_access_token(user_id, data=data)

    @staticmethod
    def generate_refresh_token(user_id: Any) -> str:
        return security.create_refresh_token(user_id)

    @staticmethod
    def verify_token(token: str) -> str | None:
        """
        Verify access token and return subject (user_id).
        Raises HTTPException if token is invalid or expired.
        """
        try:
            payload = security.decode_token(token)
            if payload.get("type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type, access token expected"
                )
            sub = payload.get("sub")
            if not sub:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing subject"
                )
            return str(sub)
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token credentials"
            )

    @staticmethod
    def verify_refresh_token(token: str) -> str | None:
        """
        Verify refresh token and return subject (user_id).
        Raises HTTPException if token is invalid or expired.
        """
        try:
            payload = security.decode_token(token)
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type, refresh token expected"
                )
            sub = payload.get("sub")
            if not sub:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing subject"
                )
            return str(sub)
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired"
            )
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token credentials"
            )

