from fastapi import Depends, HTTPException, Cookie
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.auth import decode_token


def get_current_user(
    token: str = Cookie(None),
    db: Session = Depends(get_db),
):
    if not token:
        raise HTTPException(status_code=401, detail="Not logged in")
    try:
        payload = decode_token(token)
        user = db.query(models.User).get(int(payload["sub"]))
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_role(*allowed_roles):
    """Returns a dependency that only allows users with certain roles."""
    def check(user=Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"This action requires one of: {', '.join(allowed_roles)}",
            )
        return user
    return check