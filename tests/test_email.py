from career_agent.email import configured


def test_email_requires_complete_smtp_configuration(monkeypatch) -> None:
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
