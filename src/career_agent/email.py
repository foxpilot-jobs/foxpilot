"""Minimal SMTP email delivery for account verification and recovery."""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


def configured() -> bool:
    return bool(os.getenv("EMAIL_SMTP_HOST") and os.getenv("EMAIL_FROM"))


def send_email(recipient: str, subject: str, body: str) -> None:
    if not configured():
        raise RuntimeError("EMAIL_SMTP_HOST and EMAIL_FROM are required")
    message = EmailMessage()
    message["From"] = os.environ["EMAIL_FROM"]
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    port = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    with smtplib.SMTP(os.environ["EMAIL_SMTP_HOST"], port, timeout=10) as server:
        if os.getenv("EMAIL_SMTP_TLS", "true").lower() == "true":
            server.starttls()
        username = os.getenv("EMAIL_SMTP_USERNAME")
        if username:
            server.login(username, os.getenv("EMAIL_SMTP_PASSWORD", ""))
        server.send_message(message)
