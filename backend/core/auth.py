import logging
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from core.config import settings

_auth = logging.getLogger("trading.auth")

_bearer = HTTPBearer(auto_error=False)
_ALGORITHM = "HS256"


def create_access_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    return jwt.encode(
        {"exp": expire, "iss": "trading-bot"},
        settings.JWT_SECRET_KEY,
        algorithm=_ALGORITHM,
    )


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    x_api_key: str | None = Header(default=None),
) -> None:
    # Accepte un token JWT Bearer (émis par POST /auth/token)
    if credentials and credentials.scheme == "Bearer":
        try:
            jwt.decode(credentials.credentials, settings.JWT_SECRET_KEY, algorithms=[_ALGORITHM])
            return
        except JWTError:
            _auth.warning("auth.jwt_invalid")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide ou expiré",
            )

    # Accepte la clé API brute dans X-API-Key (utilisé par le proxy serveur Next.js)
    if x_api_key and settings.API_SECRET_KEY and x_api_key == settings.API_SECRET_KEY:
        return

    _auth.warning("auth.failed — aucune credential valide fournie")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentification requise : fournir un JWT Bearer ou X-API-Key",
    )
