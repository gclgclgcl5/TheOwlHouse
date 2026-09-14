from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.schemas.auth import AdminLoginRequest, TokenResponse
from app.services import auth as auth_service

router = APIRouter(prefix="/admin", tags=["admin-api"])


@router.post("/login", response_model=TokenResponse)
def admin_login(body: AdminLoginRequest) -> TokenResponse:
    if (
        body.username != settings.admin_username
        or body.password != settings.admin_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="管理员账号或密码错误",
        )
    token = auth_service.create_access_token(subject=body.username, role="admin")
    return TokenResponse(access_token=token, role="admin")
