import logging
from datetime import UTC, datetime, timedelta

import jwt

from src.domain.auth.ports.token_port import TokenPort

logger = logging.getLogger("iaph.auth.jwt")


class JWTTokenAdapter(TokenPort):
    def __init__(
        self,
        secret_key: str,
        algorithm: str,
        access_expire_minutes: int,
        refresh_expire_days: int,
    ) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._access_expire_minutes = access_expire_minutes
        self._refresh_expire_days = refresh_expire_days

    def create_access_token(self, username: str) -> str:
        payload = {
            "sub": username,
            "exp": datetime.now(UTC)
            + timedelta(minutes=self._access_expire_minutes),
            "type": "access",
        }
        return jwt.encode(
            payload, self._secret_key, algorithm=self._algorithm
        )

    def create_refresh_token(self, username: str) -> str:
        payload = {
            "sub": username,
            "exp": datetime.now(UTC)
            + timedelta(days=self._refresh_expire_days),
            "type": "refresh",
        }
        return jwt.encode(
            payload, self._secret_key, algorithm=self._algorithm
        )

    def validate_token(self, token: str) -> str | None:
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
            )
            return payload.get("sub")
        except jwt.ExpiredSignatureError:
            logger.debug("Token expired")
            return None
        except jwt.InvalidTokenError as exc:
            logger.warning("Invalid token: %s", exc)
            return None
