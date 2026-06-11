
from typing import Any

import jwt
from fastapi import HTTPException, status

from app.core import security


class JWTService:
    @staticmethod
    def generate_access_token(user_id: Any) -> str:
        return security.create_access_token(user_id)

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
