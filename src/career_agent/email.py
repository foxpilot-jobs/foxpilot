"""Minimal SMTP email delivery for account verification and recovery."""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

import httpx


def configured() -> bool:
    if os.getenv("RESEND_API_KEY", "").strip() and os.getenv("EMAIL_FROM", "").strip():
        return True
    return all(
        os.getenv(name, "").strip()
        for name in (
            "EMAIL_SMTP_HOST",
            "EMAIL_FROM",
            "EMAIL_SMTP_USERNAME",
            "EMAIL_SMTP_PASSWORD",
        )
    )


def send_email(recipient: str, subject: str, body: str) -> None:
    if not configured():
        raise RuntimeError(
            "RESEND_API_KEY and EMAIL_FROM or complete SMTP configuration are required"
        )
    message = EmailMessage()
    message["From"] = os.environ["EMAIL_FROM"]
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    resend_key = os.getenv("RESEND_API_KEY", "").strip()
    if resend_key:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {resend_key}"},
            json={
                "from": os.environ["EMAIL_FROM"],
                "to": [recipient],
                "subject": subject,
                "text": body,
            },
            timeout=10,
        )
        response.raise_for_status()
        return
    port = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    with smtplib.SMTP(os.environ["EMAIL_SMTP_HOST"], port, timeout=10) as server:
        if os.getenv("EMAIL_SMTP_TLS", "true").lower() == "true":
            server.starttls()
        username = os.getenv("EMAIL_SMTP_USERNAME")
        if username:
            server.login(username, os.getenv("EMAIL_SMTP_PASSWORD", ""))
        server.send_message(message)
