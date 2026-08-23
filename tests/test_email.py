from career_agent import email
from career_agent.email import configured


def test_email_requires_complete_smtp_configuration(monkeypatch) -> None:
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    for name in (
        "EMAIL_SMTP_HOST",
        "EMAIL_FROM",
        "EMAIL_SMTP_USERNAME",
        "EMAIL_SMTP_PASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)

    assert not configured()

    monkeypatch.setenv("EMAIL_SMTP_HOST", "smtp.resend.com")
    monkeypatch.setenv("EMAIL_FROM", "FoxPilot <accounts@foxpilot.in>")
    monkeypatch.setenv("EMAIL_SMTP_USERNAME", "resend")
    monkeypatch.setenv("EMAIL_SMTP_PASSWORD", "test-secret")

    assert configured()


def test_send_email_uses_resend_https_api(monkeypatch) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("EMAIL_FROM", "FoxPilot <accounts@foxpilot.in>")

    calls = []

    class Response:
        def raise_for_status(self) -> None:
            pass

    def post(*args, **kwargs):
        calls.append((args, kwargs))
        return Response()

    monkeypatch.setattr(email.httpx, "post", post)
    monkeypatch.setattr(email.smtplib, "SMTP", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("SMTP should not be used")))

    email.send_email("user@example.com", "Verify", "Verification body")

    assert calls == [
        (
            ("https://api.resend.com/emails",),
            {
                "headers": {"Authorization": "Bearer re_test"},
                "json": {
                    "from": "FoxPilot <accounts@foxpilot.in>",
                    "to": ["user@example.com"],
                    "subject": "Verify",
                    "text": "Verification body",
                },
                "timeout": 10,
            },
        )
    ]
