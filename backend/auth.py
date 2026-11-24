"""
Source2Study - Authentication Module
JWT-based authentication with password hashing, email verification, and password reset.
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import User
from schemas import TokenData, validate_strong_password
from services.email_service import email_service, EmailDeliveryError

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token extraction from Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a plain text password using bcrypt."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token with the given data and expiration."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """Verify and decode a JWT token, returning the embedded token data."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("sub")
        email: str = payload.get("email")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return TokenData(user_id=int(user_id), email=email)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency that extracts and validates the current user from the JWT token."""
    token_data = verify_token(token)
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def register_user(db: Session, email: str, full_name: str, password: str) -> Tuple[User, str]:
    """Register a new user in an unverified state and dispatch verification email."""
    # Normalize email
    clean_email = email.strip().lower()
    clean_name = full_name.strip()

    # Validate strong password
    try:
        validate_strong_password(password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    existing_user = db.query(User).filter(User.email == clean_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address is already registered.",
        )

    verification_token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=settings.VERIFICATION_TOKEN_EXPIRE_HOURS)

    hashed_password = get_password_hash(password)
    new_user = User(
        email=clean_email,
        full_name=clean_name,
        hashed_password=hashed_password,
        is_verified=False,
        verification_token=verification_token,
        verification_token_expires_at=expires_at,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Dispatch verification email
    email_service.send_verification_email(new_user.email, new_user.full_name, verification_token)

    return new_user, verification_token


def authenticate_user(db: Session, email: str, password: str) -> User:
    """Authenticate a user by email and password, ensuring account is verified."""
    clean_email = email.strip().lower()
    user = db.query(User).filter(User.email == clean_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email address not verified. Please check your inbox for the verification link or request a new one.",
        )
    return user


def verify_user_email(db: Session, token: str) -> User:
    """Validate verification token, mark account verified, and invalidate token."""
    clean_token = token.strip()
    user = db.query(User).filter(User.verification_token == clean_token).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token. Please request a new verification email.",
        )

    if user.verification_token_expires_at and user.verification_token_expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This verification link has expired. Please request a new verification email.",
        )

    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires_at = None
    db.commit()
    db.refresh(user)
    return user


def resend_verification_email(db: Session, email: str) -> bool:
    """Regenerate verification token and resend verification email."""
    if not email_service.is_configured():
        raise EmailDeliveryError(
            "Email service is not configured on the server. Please configure SMTP settings (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD) in the .env file.",
            status_code=503,
        )

    clean_email = email.strip().lower()
    user = db.query(User).filter(User.email == clean_email).first()
    if not user:
        # Avoid user enumeration while giving sensible feedback
        return True

    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account is already verified. You can log in directly.",
        )

    token = secrets.token_urlsafe(32)
    user.verification_token = token
    user.verification_token_expires_at = datetime.utcnow() + timedelta(
        hours=settings.VERIFICATION_TOKEN_EXPIRE_HOURS
    )
    db.commit()

    email_service.send_verification_email(user.email, user.full_name, token)
    return True


def initiate_password_reset(db: Session, email: str) -> bool:
    """Generate password reset token and dispatch email without leaking account existence."""
    if not email_service.is_configured():
        raise EmailDeliveryError(
            "Email service is not configured on the server. Please configure SMTP settings (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD) in the .env file.",
            status_code=503,
        )

    clean_email = email.strip().lower()
    user = db.query(User).filter(User.email == clean_email).first()
    if user:
        token = secrets.token_urlsafe(32)
        user.reset_password_token = token
        user.reset_password_expires_at = datetime.utcnow() + timedelta(
            hours=settings.RESET_TOKEN_EXPIRE_HOURS
        )
        db.commit()
        email_service.send_password_reset_email(user.email, user.full_name, token)
        return True

    return False


def complete_password_reset(db: Session, token: str, new_password: str) -> User:
    """Validate password reset token, check strong password, update hash, and invalidate token."""
    clean_token = token.strip()
    user = db.query(User).filter(User.reset_password_token == clean_token).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset link. Please request a new one.",
        )

    if user.reset_password_expires_at and user.reset_password_expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link has expired. Please request a new one.",
        )

    # Validate password policy
    try:
        validate_strong_password(new_password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    user.hashed_password = get_password_hash(new_password)
    user.reset_password_token = None
    user.reset_password_expires_at = None
    # Resetting password also confirms email ownership
    user.is_verified = True
    db.commit()
    db.refresh(user)
    return user
