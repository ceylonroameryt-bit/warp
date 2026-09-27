"""
Warp Ladger — Email Service
Pluggable backend: console (dev) or SMTP (production).
"""
import smtplib
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import aiosmtplib
import structlog

from app.core.config import settings

log = structlog.get_logger(__name__)


# ─── Email Backends ───────────────────────────────────────────
class EmailBackend(ABC):
    @abstractmethod
    async def send(self, *, to: str, subject: str, html: str, text: str) -> None:
        ...


class ConsoleEmailBackend(EmailBackend):
    """Prints emails to stdout. Used in development."""

    async def send(self, *, to: str, subject: str, html: str, text: str) -> None:
        log.info(
            "email_console",
            to=to,
            subject=subject,
            preview=text[:200],
        )
        print(f"\n{'─'*60}")
        print(f"📧 EMAIL TO: {to}")
        print(f"   SUBJECT: {subject}")
        print(f"   BODY:\n{text}")
        print(f"{'─'*60}\n")


class SMTPEmailBackend(EmailBackend):
    """Sends real emails via SMTP (MailHog, Resend, Postmark, etc.)."""

    async def send(self, *, to: str, subject: str, html: str, text: str) -> None:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS}>"
        message["To"] = to
        message.attach(MIMEText(text, "plain"))
        message.attach(MIMEText(html, "html"))

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER or None,
                password=settings.SMTP_PASSWORD or None,
                use_tls=settings.SMTP_TLS,
                start_tls=False,
            )
            log.info("email_sent", to=to, subject=subject)
        except Exception as e:
            log.error("email_send_failed", to=to, subject=subject, error=str(e))
            raise


def get_email_backend() -> EmailBackend:
    if settings.EMAIL_BACKEND == "smtp":
        return SMTPEmailBackend()
    return ConsoleEmailBackend()


# ─── Email Service ────────────────────────────────────────────
class EmailService:
    def __init__(self) -> None:
        self.backend = get_email_backend()
        self.base_url = settings.APP_URL

    async def send_verification_email(
        self,
        *,
        to_email: str,
        full_name: Optional[str] = None,
        token: str,
    ) -> None:
        name = full_name or "there"
        verify_url = f"{self.base_url}/auth/verify-email?token={token}"
        subject = "Verify your Warp Ladger account"
        text = (
            f"Hi {name},\n\n"
            f"Please verify your email address by clicking the link below:\n\n"
            f"{verify_url}\n\n"
            f"This link expires in 24 hours.\n\n"
            f"If you didn't create this account, you can ignore this email.\n\n"
            f"— The Warp Ladger Team"
        )
        html = f"""
        <div style="font-family:Inter,sans-serif;max-width:560px;margin:0 auto;">
          <h2 style="color:#1e1b4b;">Verify your email</h2>
          <p>Hi {name},</p>
          <p>Click the button below to verify your Warp Ladger account:</p>
          <p style="margin:24px 0;">
            <a href="{verify_url}" style="
              background:linear-gradient(135deg,#4f46e5,#7c3aed);
              color:#fff;padding:12px 24px;border-radius:8px;
              text-decoration:none;font-weight:600;
            ">Verify Email</a>
          </p>
          <p style="color:#64748b;font-size:14px;">
            Link expires in 24 hours.
            If you didn't register, ignore this email.
          </p>
        </div>
        """
        await self.backend.send(to=to_email, subject=subject, html=html, text=text)

    async def send_password_reset_email(
        self,
        *,
        to_email: str,
        full_name: Optional[str] = None,
        token: str,
    ) -> None:
        name = full_name or "there"
        reset_url = f"{self.base_url}/auth/reset-password?token={token}"
        subject = "Reset your Warp Ladger password"
        text = (
            f"Hi {name},\n\n"
            f"Someone requested a password reset for your account.\n\n"
            f"Click the link below to reset your password:\n\n"
            f"{reset_url}\n\n"
            f"This link expires in 2 hours.\n\n"
            f"If you didn't request this, you can safely ignore this email.\n\n"
            f"— The Warp Ladger Team"
        )
        html = f"""
        <div style="font-family:Inter,sans-serif;max-width:560px;margin:0 auto;">
          <h2 style="color:#1e1b4b;">Reset your password</h2>
          <p>Hi {name},</p>
          <p>Click the button below to reset your password. This link expires in 2 hours.</p>
          <p style="margin:24px 0;">
            <a href="{reset_url}" style="
              background:linear-gradient(135deg,#4f46e5,#7c3aed);
              color:#fff;padding:12px 24px;border-radius:8px;
              text-decoration:none;font-weight:600;
            ">Reset Password</a>
          </p>
          <p style="color:#64748b;font-size:14px;">
            If you didn't request this, ignore this email. Your password won't change.
          </p>
        </div>
        """
        await self.backend.send(to=to_email, subject=subject, html=html, text=text)

    async def send_invitation_email(
        self,
        *,
        to_email: str,
        inviter_name: Optional[str],
        org_name: str,
        role_name: str,
        token: str,
    ) -> None:
        accept_url = f"{self.base_url}/auth/accept-invite/{token}"
        inviter = inviter_name or "Someone"
        subject = f"You've been invited to join {org_name} on Warp Ladger"
        text = (
            f"{inviter} has invited you to join {org_name} as {role_name}.\n\n"
            f"Accept your invitation:\n\n{accept_url}\n\n"
            f"This invitation expires in 7 days.\n\n"
            f"— The Warp Ladger Team"
        )
        html = f"""
        <div style="font-family:Inter,sans-serif;max-width:560px;margin:0 auto;">
          <h2 style="color:#1e1b4b;">You're invited to {org_name}</h2>
          <p><strong>{inviter}</strong> has invited you to join
             <strong>{org_name}</strong> as <strong>{role_name}</strong>.</p>
          <p style="margin:24px 0;">
            <a href="{accept_url}" style="
              background:linear-gradient(135deg,#4f46e5,#7c3aed);
              color:#fff;padding:12px 24px;border-radius:8px;
              text-decoration:none;font-weight:600;
            ">Accept Invitation</a>
          </p>
          <p style="color:#64748b;font-size:14px;">
            This invitation expires in 7 days.
          </p>
        </div>
        """
        await self.backend.send(to=to_email, subject=subject, html=html, text=text)
