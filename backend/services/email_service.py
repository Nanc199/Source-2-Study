"""
Source2Study - Email Service
Handles email delivery for user verification and password resets using SMTP.
"""

import os
import smtplib
import socket
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, Tuple

from config import settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """Custom exception raised when email delivery fails."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.detail = message
        self.status_code = status_code


class EmailService:
    """Service for sending transactional emails (Verification, Password Reset)."""

    def is_configured(self) -> bool:
        """Check if SMTP credentials and host are configured (or dev fallback explicitly allowed)."""
        allow_dev = getattr(self, "allow_dev_fallback", settings.SMTP_ALLOW_DEV_FALLBACK)
        if allow_dev:
            return True
        return bool(settings.SMTP_HOST and settings.SMTP_HOST.strip())

    def _get_from_address(self) -> Tuple[str, str]:
        """Resolve valid From email and display name."""
        from_email = (settings.SMTP_FROM_EMAIL or "").strip()
        smtp_user = (settings.SMTP_USER or "").strip()

        # If SMTP_FROM_EMAIL is not customized or is generic, prefer SMTP_USER for services like Gmail
        if not from_email or from_email == "noreply@source2study.com":
            if smtp_user and "@" in smtp_user:
                from_email = smtp_user
            else:
                from_email = "noreply@source2study.com"

        from_name = (settings.SMTP_FROM_NAME or "Source2Study Support").strip()
        return from_email, from_name

    def _record_email_for_dev(self, recipient: str, subject: str, link: str, token: str, email_type: str):
        """Record dispatched email locally for development, testing, and auditing."""
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        log_path = os.path.join(settings.UPLOAD_DIR, "sent_emails.log")
        entry = (
            f"[{datetime.utcnow().isoformat()}] TYPE={email_type} TO={recipient} "
            f"SUBJECT='{subject}' LINK={link} TOKEN={token}\n"
        )
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            logger.warning(f"Could not append to email log: {e}")
        logger.info(f"📧 [Email Dispatched] {email_type} to {recipient} | Link: {link}")

    def send_verification_email(self, to_email: str, full_name: str, token: str) -> bool:
        """Send an account verification email containing a secure token link."""
        frontend_url = settings.FRONTEND_URL.rstrip("/")
        verification_url = f"{frontend_url}/verify-email?token={token}"
        subject = f"Verify your {settings.APP_NAME} Account"

        text_content = (
            f"Hello {full_name},\n\n"
            f"Thank you for registering with {settings.APP_NAME}.\n"
            f"Please verify your email address by opening the following link:\n\n"
            f"{verification_url}\n\n"
            f"This link will expire in {settings.VERIFICATION_TOKEN_EXPIRE_HOURS} hours.\n"
            f"If you did not create an account, you can safely ignore this email.\n\n"
            f"— The {settings.APP_NAME} Team"
        )

        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{subject}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }}
    .container {{ max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; overflow: hidden; }}
    .header {{ background: linear-gradient(135deg, #7c3aed, #4f46e5); padding: 32px 24px; text-align: center; color: white; }}
    .header h1 {{ margin: 0; font-size: 24px; font-weight: 700; }}
    .header p {{ margin: 6px 0 0; opacity: 0.85; font-size: 14px; }}
    .content {{ padding: 32px 28px; line-height: 1.6; font-size: 15px; }}
    .btn {{ display: inline-block; background: #7c3aed; color: #ffffff !important; text-decoration: none; padding: 12px 28px; border-radius: 10px; font-weight: 600; font-size: 15px; margin: 20px 0; }}
    .footer {{ padding: 20px 28px; background: #f8fafc; border-top: 1px solid #e2e8f0; font-size: 12px; color: #64748b; text-align: center; }}
    .link-fallback {{ word-break: break-all; color: #7c3aed; font-size: 13px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>{settings.APP_NAME}</h1>
      <p>AI-Powered Learning & Exam Preparation</p>
    </div>
    <div class="content">
      <p>Hello <strong>{full_name}</strong>,</p>
      <p>Welcome to {settings.APP_NAME}! Please confirm your email address to activate your account and access all study features.</p>
      <p style="text-align: center;">
        <a href="{verification_url}" class="btn" target="_blank">Verify Email Address</a>
      </p>
      <p>Or paste this link into your browser:</p>
      <p class="link-fallback"><a href="{verification_url}">{verification_url}</a></p>
      <p style="color: #64748b; font-size: 13px;">This verification link will expire in {settings.VERIFICATION_TOKEN_EXPIRE_HOURS} hours and can only be used once.</p>
    </div>
    <div class="footer">
      <p>If you didn't create an account with {settings.APP_NAME}, please ignore this email.</p>
      <p>&copy; {settings.APP_NAME}. All rights reserved.</p>
    </div>
  </div>
</body>
</html>"""

        return self._send_email(to_email, subject, text_content, html_content, verification_url, token, "VERIFICATION")

    def send_password_reset_email(self, to_email: str, full_name: str, token: str) -> bool:
        """Send a password reset email with a secure time-limited token."""
        frontend_url = settings.FRONTEND_URL.rstrip("/")
        reset_url = f"{frontend_url}/reset-password?token={token}"
        subject = f"Reset your {settings.APP_NAME} Password"

        text_content = (
            f"Hello {full_name},\n\n"
            f"We received a request to reset your {settings.APP_NAME} password.\n"
            f"Click the link below to set a new password:\n\n"
            f"{reset_url}\n\n"
            f"This link will expire in {settings.RESET_TOKEN_EXPIRE_HOURS} hour.\n"
            f"If you did not request a password reset, you can safely ignore this email.\n\n"
            f"— The {settings.APP_NAME} Team"
        )

        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{subject}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }}
    .container {{ max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; overflow: hidden; }}
    .header {{ background: linear-gradient(135deg, #7c3aed, #4f46e5); padding: 32px 24px; text-align: center; color: white; }}
    .header h1 {{ margin: 0; font-size: 24px; font-weight: 700; }}
    .content {{ padding: 32px 28px; line-height: 1.6; font-size: 15px; }}
    .btn {{ display: inline-block; background: #7c3aed; color: #ffffff !important; text-decoration: none; padding: 12px 28px; border-radius: 10px; font-weight: 600; font-size: 15px; margin: 20px 0; }}
    .footer {{ padding: 20px 28px; background: #f8fafc; border-top: 1px solid #e2e8f0; font-size: 12px; color: #64748b; text-align: center; }}
    .link-fallback {{ word-break: break-all; color: #7c3aed; font-size: 13px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>{settings.APP_NAME}</h1>
      <p>Password Reset Request</p>
    </div>
    <div class="content">
      <p>Hello <strong>{full_name}</strong>,</p>
      <p>We received a request to reset your password. Click the button below to choose a new password satisfying our security requirements.</p>
      <p style="text-align: center;">
        <a href="{reset_url}" class="btn" target="_blank">Reset Password</a>
      </p>
      <p>Or paste this link into your browser:</p>
      <p class="link-fallback"><a href="{reset_url}">{reset_url}</a></p>
      <p style="color: #64748b; font-size: 13px;">This reset link will expire in {settings.RESET_TOKEN_EXPIRE_HOURS} hour and can only be used once.</p>
      <p style="color: #64748b; font-size: 13px;">If you did not request this change, please ignore this email; your account remains secure.</p>
    </div>
    <div class="footer">
      <p>&copy; {settings.APP_NAME}. All rights reserved.</p>
    </div>
  </div>
</body>
</html>"""

        return self._send_email(to_email, subject, text_content, html_content, reset_url, token, "PASSWORD_RESET")

    def _send_email(
        self,
        to_email: str,
        subject: str,
        text_content: str,
        html_content: str,
        link: str,
        token: str,
        email_type: str,
    ) -> bool:
        """Deliver email via SMTP if configured, raising specific errors on failure."""
        # Always record to local log for debugging and tracking
        self._record_email_for_dev(to_email, subject, link, token, email_type)

        smtp_host = (settings.SMTP_HOST or "").strip()
        allow_dev = getattr(self, "allow_dev_fallback", settings.SMTP_ALLOW_DEV_FALLBACK)
        if not smtp_host:
            if allow_dev:
                logger.info(f"SMTP_ALLOW_DEV_FALLBACK=True: Recorded {email_type} email for {to_email} to uploads/sent_emails.log")
                return True
            # SMTP is not configured
            err_msg = (
                "Email delivery service is not configured on the server. "
                "Please configure SMTP_HOST, SMTP_PORT, SMTP_USER, and SMTP_PASSWORD in the .env file."
            )
            logger.error(f"Cannot dispatch {email_type} to {to_email}: {err_msg}")
            raise EmailDeliveryError(err_msg, status_code=503)

        from_email, from_name = self._get_from_address()
        smtp_port = settings.SMTP_PORT
        smtp_user = (settings.SMTP_USER or "").strip()
        smtp_password = settings.SMTP_PASSWORD or ""

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = to_email

        part1 = MIMEText(text_content, "plain", "utf-8")
        part2 = MIMEText(html_content, "html", "utf-8")
        msg.attach(part1)
        msg.attach(part2)

        server = None
        try:
            if settings.SMTP_SSL:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=12)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=12)
                if settings.SMTP_TLS:
                    server.starttls()

            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)

            server.sendmail(from_email, [to_email], msg.as_string())
            logger.info(f"Successfully sent {email_type} email to {to_email} via SMTP ({smtp_host}:{smtp_port})")
            return True

        except smtplib.SMTPAuthenticationError as e:
            detail = e.smtp_error.decode("utf-8", errors="ignore") if hasattr(e, "smtp_error") and isinstance(e.smtp_error, bytes) else str(e)
            error_msg = f"SMTP authentication failed for user '{smtp_user}'. Please check your email credentials or App Password. ({detail})"
            logger.error(error_msg)
            raise EmailDeliveryError(error_msg, status_code=500)

        except smtplib.SMTPConnectError as e:
            error_msg = f"Could not connect to SMTP server ({smtp_host}:{smtp_port}). Please verify the host and port."
            logger.error(error_msg)
            raise EmailDeliveryError(error_msg, status_code=502)

        except (socket.timeout, TimeoutError):
            error_msg = f"Connection to SMTP server ({smtp_host}:{smtp_port}) timed out."
            logger.error(error_msg)
            raise EmailDeliveryError(error_msg, status_code=504)

        except smtplib.SMTPServerDisconnected:
            error_msg = f"SMTP server disconnected unexpectedly ({smtp_host}:{smtp_port})."
            logger.error(error_msg)
            raise EmailDeliveryError(error_msg, status_code=502)

        except Exception as e:
            error_msg = f"Failed to send {email_type} email to {to_email}: {str(e)}"
            logger.error(error_msg)
            raise EmailDeliveryError(error_msg, status_code=500)

        finally:
            if server:
                try:
                    server.quit()
                except Exception:
                    try:
                        server.close()
                    except Exception:
                        pass


email_service = EmailService()
