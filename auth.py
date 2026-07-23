"""
Reusable auth dependency for protected routes.

Any route that declares `user = Depends(get_current_user)` is automatically
protected: FastAPI runs this function first, and the route body only runs
if it returns successfully. This replaces writing the same token-check
code inside every protected route (Stage 3's version, now removed).

Uses FastAPI's HTTPBearer security scheme rather than reading the
Authorization header manually — this also registers the route with
OpenAPI as bearer-protected, which is what makes Swagger UI's
"Authorize" padlock appear automatically in Stage 5.
"""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase_client import supabase
from supabase_auth.errors import AuthApiError

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    """Verify the bearer token with Supabase and return the Supabase User.

    Raises 401 if the header is missing/malformed, or if Supabase says
    the token is invalid or expired.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Access token required")

    token = credentials.credentials

    try:
        result = supabase.auth.get_user(token)
    except AuthApiError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if not result or not result.user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return result.user


def get_current_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    """Return the raw bearer token string, still validating the header shape.

    Used by /auth/logout, which needs the literal token (to hand to
    Supabase's logout endpoint) rather than the decoded user object.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Access token required")
    return credentials.credentials
