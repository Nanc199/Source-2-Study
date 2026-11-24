"""
Source2Study - Auth Router
Endpoints for user registration, email verification, login, and password reset.
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from schemas import (
    UserCreate, UserLogin, UserResponse, Token,
    VerifyEmailRequest, ResendVerificationRequest,
    ForgotPasswordRequest, ResetPasswordRequest, MessageResponse,
)
from auth import (
    register_user, authenticate_user, verify_user_email,
    resend_verification_email, initiate_password_reset,
    complete_password_reset, create_access_token, get_current_user,
)
from services.email_service import EmailDeliveryError
from config import settings
from models import User

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=MessageResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user in unverified state and dispatch verification email."""
    try:
        user, _ = register_user(db, user_data.email, user_data.full_name, user_data.password)
        return MessageResponse(
            message="Account created successfully! Please check your email inbox to verify your account before signing in.",
            email=user.email,
        )
    except EmailDeliveryError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=f"Registration succeeded but verification email could not be sent: {e.message}",
        )


@router.post("/verify-email", response_model=MessageResponse)
def verify_email(data: VerifyEmailRequest, db: Session = Depends(get_db)):
    """Verify email token and activate account."""
    user = verify_user_email(db, data.token)
    return MessageResponse(
        message="Your email address has been successfully verified! You may now sign in.",
        email=user.email,
    )


@router.post("/resend-verification", response_model=MessageResponse)
def resend_verification(data: ResendVerificationRequest, db: Session = Depends(get_db)):
    """Resend account verification email."""
    try:
        resend_verification_email(db, data.email)
        return MessageResponse(
            message="If an unverified account exists for this email address, a new verification link has been dispatched.",
            email=data.email,
        )
    except EmailDeliveryError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Initiate password reset process by email."""
    try:
        sent = initiate_password_reset(db, data.email)
        if sent:
            return MessageResponse(
                message="Password reset instructions have been sent to your email address.",
                email=data.email,
            )
        else:
            return MessageResponse(
                message="If an account exists with this email address, password reset instructions have been sent to your inbox.",
                email=data.email,
            )
    except EmailDeliveryError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Complete password reset with secure token."""
    user = complete_password_reset(db, data.token, data.new_password)
    return MessageResponse(
        message="Your password has been successfully updated! You can now log in with your new credentials.",
        email=user.email,
    )


@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Authenticate verified user and issue JWT access token."""
    user = authenticate_user(db, user_data.email, user_data.password)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(
        access_token=access_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_verified=user.is_verified,
            created_at=user.created_at,
            updated_at=user.updated_at,
        ),
    )


@router.get("/me", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    """Get profile of authenticated user."""
    return current_user
