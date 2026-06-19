from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx
from app.config import settings

security = HTTPBearer()

_jwks_cache: dict = {}

async def _get_jwks() -> dict:
    if _jwks_cache:
        return _jwks_cache
    url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
    _jwks_cache.update(resp.json())
    return _jwks_cache

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")

        if alg == "ES256":
            jwks = await _get_jwks()
            kid = header.get("kid")
            key = next((k for k in jwks["keys"] if k["kid"] == kid), None)
            if not key:
                raise HTTPException(status_code=401, detail="Unknown signing key")
            secret = key
        else:
            secret = settings.jwt_secret

        payload = jwt.decode(
            token,
            secret,
            algorithms=[alg],
            options={"verify_aud": False}
        )
        user_id = payload.get("sub")
        email = payload.get("email")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        return {"id": user_id, "email": email}

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
