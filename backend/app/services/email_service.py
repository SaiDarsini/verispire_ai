"""
Email delivery service.
Sends real emails via SMTP when SMTP_HOST/SMTP_USER/SMTP_PASSWORD are set in
.env (see .env.example). If they're left blank, falls back to logging the
email to the console so the auth flow is still testable without a mail
server.
"""
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger("victorus.email")
logging.basicConfig(level=logging.INFO)


BRAND_COLOR = "#7C5CFF"
BRAND_NAME = "VICTORUS AI"


def _wrap_html(title: str, heading: str, body_html: str) -> str:
    return f"""\
<!DOCTYPE html>
<html>
  <body style="margin:0;padding:0;background:#0B0B14;font-family:Segoe UI,Helvetica,Arial,sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#0B0B14;padding:40px 0;">
      <tr>
        <td align="center">
          <table width="480" cellpadding="0" cellspacing="0" style="background:#14141F;border-radius:16px;overflow:hidden;border:1px solid #23232F;">
            <tr>
              <td style="padding:32px 40px 0 40px;">
                <div style="display:flex;align-items:center;gap:10px;">
                  <span style="display:inline-block;width:32px;height:32px;border-radius:9px;background:{BRAND_COLOR};color:#fff;font-weight:700;text-align:center;line-height:32px;font-size:16px;">V</span>
                  <span style="color:#fff;font-weight:700;font-size:16px;letter-spacing:0.5px;">{BRAND_NAME}</span>
                </div>
              </td>
            </tr>
            <tr>
              <td style="padding:28px 40px 8px 40px;">
                <h1 style="color:#fff;font-size:20px;margin:0 0 12px 0;">{heading}</h1>
                <div style="color:#9E9EB3;font-size:14px;line-height:1.6;">{body_html}</div>
              </td>
            </tr>
            <tr>
              <td style="padding:28px 40px 32px 40px;">
                <p style="color:#5A5A6E;font-size:12px;margin:0;">If you didn't request this, you can safely ignore this email.</p>
              </td>
            </tr>
          </table>
          <p style="color:#3F3F4E;font-size:11px;margin-top:20px;">© {BRAND_NAME}. All rights reserved.</p>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


class EmailService:
    def _send(self, to_email: str, subject: str, html_body: str, text_fallback: str) -> None:
        if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            # No SMTP configured — log to console instead (dev mode).
            logger.info("[EMAIL - DEV MODE, no SMTP configured] To: %s | Subject: %s | %s",
                         to_email, subject, text_fallback)
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.EMAIL_FROM or settings.SMTP_USER
        msg["To"] = to_email
        msg.attach(MIMEText(text_fallback, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls(context=context)
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(msg["From"], [to_email], msg.as_string())
            logger.info("[EMAIL] Sent '%s' to %s", subject, to_email)
        except Exception as exc:  # noqa: BLE001
            # Never crash the request because email delivery failed — log it
            # and also print the code/link to console so dev/testing can continue.
            logger.error("[EMAIL] Failed to send to %s: %s", to_email, exc)
            logger.info("[EMAIL - FALLBACK] To: %s | Subject: %s | %s", to_email, subject, text_fallback)

    def send_otp_email(self, to_email: str, otp_code: str) -> None:
        body_html = f"""
          <p>Use the verification code below to confirm your email address.
          This code expires in 10 minutes.</p>
          <div style="margin:20px 0;text-align:center;">
            <span style="display:inline-block;background:#1D1D2B;border:1px solid #2E2E3E;
              border-radius:10px;padding:16px 28px;font-size:28px;letter-spacing:8px;
              color:#fff;font-weight:700;">{otp_code}</span>
          </div>
        """
        html = _wrap_html("Verify your email", "Verify your email", body_html)
        self._send(
            to_email,
            subject=f"{otp_code} is your {BRAND_NAME} verification code",
            html_body=html,
            text_fallback=f"Your {BRAND_NAME} verification code is: {otp_code} (expires in 10 minutes)",
        )

    def send_password_reset_email(self, to_email: str, reset_token: str) -> None:
        body_html = f"""
          <p>We received a request to reset your password. Use the code below,
          or contact support if you didn't request this.</p>
          <div style="margin:20px 0;text-align:center;">
            <span style="display:inline-block;background:#1D1D2B;border:1px solid #2E2E3E;
              border-radius:10px;padding:16px 28px;font-size:22px;letter-spacing:4px;
              color:#fff;font-weight:700;">{reset_token}</span>
          </div>
        """
        html = _wrap_html("Reset your password", "Reset your password", body_html)
        self._send(
            to_email,
            subject=f"Reset your {BRAND_NAME} password",
            html_body=html,
            text_fallback=f"Your {BRAND_NAME} password reset code is: {reset_token}",
        )

    def send_welcome_email(self, to_email: str, full_name: str) -> None:
        body_html = f"""
          <p>Hi {full_name}, your account is verified and ready to go.
          Log in to set up your workspace and start chatting with your AI agents.</p>
        """
        html = _wrap_html("Welcome", f"Welcome to {BRAND_NAME}, {full_name}", body_html)
        self._send(
            to_email,
            subject=f"Welcome to {BRAND_NAME}",
            html_body=html,
            text_fallback=f"Welcome to {BRAND_NAME}, {full_name}! Your account is ready.",
        )


email_service = EmailService()
