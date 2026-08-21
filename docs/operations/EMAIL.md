# Transactional Email Setup

FoxPilot sends account verification, password-reset, and security messages through SMTP. Resend is the recommended provider for staging and production. Gmail is supported only as a private local-development fallback.

## Recommendation

Use Resend with the `foxpilot.in` domain:

```text
Provider: Resend SMTP
Host: smtp.resend.com
Port: 587
Username: resend
Password: Resend API key
Sender: accounts@foxpilot.in
```

Resend currently offers a free transactional tier with a monthly allowance and a daily cap. Confirm current limits in the Resend account before relying on them. OpenAI usage, Railway usage, and email usage are separate billing concerns.

## Resend Setup

1. Create a Resend account.
2. Add `foxpilot.in` under Domains.
3. Resend will display DNS records for domain verification and email authentication.
4. In GoDaddy DNS, add the exact records Resend provides. Do not invent or alter their values.
5. Complete SPF and DKIM verification.
6. Add a DMARC record after confirming the sender domain works. Start with a monitoring policy appropriate to the domain’s existing email use.
7. Create a restricted Resend API key for FoxPilot staging.
8. Store the key as `EMAIL_SMTP_PASSWORD` in Railway or the deployment secret manager.
9. Do not put the key in the repository, frontend variables, Docker image, or chat.

## Environment Variables

```env
EMAIL_FROM=FoxPilot <accounts@foxpilot.in>
EMAIL_SMTP_HOST=smtp.resend.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USERNAME=resend
EMAIL_SMTP_PASSWORD=<secret>
EMAIL_SMTP_TLS=true
```

Configure these only on the API service. The worker does not need email credentials unless email delivery is moved into the worker later.

## Local Test

For a local test, put the values in an untracked `.env` file and run the API locally. Register a test account and verify that the verification email arrives. Also test one password-reset request. Remove the secret after testing if it was created only for local use.

## Gmail Fallback

Gmail is acceptable for a private local test:

```env
EMAIL_FROM=your-address@gmail.com
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USERNAME=your-address@gmail.com
EMAIL_SMTP_PASSWORD=<Google app password>
EMAIL_SMTP_TLS=true
```

Use a Google App Password with two-step verification enabled. Never use the normal Gmail password. Gmail has account sending limits, consumer-account deliverability constraints, and is not a reliable transactional sender for a product.

## Verification Checklist

- [ ] `foxpilot.in` is verified in Resend.
- [ ] SPF and DKIM pass.
- [ ] DMARC is configured appropriately.
- [ ] Sender address is on the verified domain.
- [ ] Railway secret is set only on the API service.
- [ ] Account verification succeeds.
- [ ] Password reset succeeds.
- [ ] No credentials appear in logs.
- [ ] Test email does not contain resume text or other unnecessary personal data.
