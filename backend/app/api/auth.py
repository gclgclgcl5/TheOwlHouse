from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserOut
from app.services import auth as auth_service
from app.services.storage import media_url, save_avatar

router = APIRouter(prefix="/auth", tags=["auth"])


def user_to_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        nickname=user.nickname,
        avatar_url=media_url(user.avatar_path),
        created_at=user.created_at,
    )


@router.post("/register", response_model=TokenResponse)
async def register(
    nickname: str = Form(..., min_length=1, max_length=64),
    password: str = Form(..., min_length=4, max_length=128),
    avatar: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> TokenResponse:
    nickname = nickname.strip()
    if not nickname:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="昵称不能为空")
    from app.services import users as users_service

    # 仅与活跃用户比重名；已注销用户占用同名时先释放昵称
    users_service.release_deleted_nickname(db, nickname)
    exists = db.scalar(
        select(User).where(User.nickname == nickname, User.is_deleted.is_(False))
    )
    if exists is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="昵称已被使用")
    avatar_path = await save_avatar(avatar)
    user = User(
        nickname=nickname,
        password_hash=auth_service.hash_password(password),
        avatar_path=avatar_path,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = auth_service.create_access_token(subject=str(user.id), role="user")
    return TokenResponse(access_token=token, role="user")


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.nickname == body.nickname.strip()))
    if user is None or user.is_deleted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="昵称或密码错误")
    if not auth_service.verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="昵称或密码错误")
    token = auth_service.create_access_token(subject=str(user.id), role="user")
    return TokenResponse(access_token=token, role="user")


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return user_to_out(current_user)
