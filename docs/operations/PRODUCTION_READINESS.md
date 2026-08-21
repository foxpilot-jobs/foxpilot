# Production Readiness Runbook

This runbook is the gate for deploying FoxPilot. Do not deploy production until every blocking item is complete and verified. The target region is AWS `ap-south-1` (Mumbai). The system design is documented in `docs/architecture/SYSTEM_DESIGN.md`.

## Deployment Decision

Use the managed AWS shape for production:

```text
CloudFront/S3       React frontend
ECS Fargate         FastAPI API
ECS Fargate         Python worker
RDS PostgreSQL      application database
SQS                 durable background jobs
S3 + KMS            original resumes and exports
Secrets Manager     credentials and API keys
CloudWatch          logs, metrics, alarms
ACM/Route 53        TLS and domain routing
```

A single VM or Docker Compose deployment is acceptable only for a private staging rehearsal. It is not the production target because it lacks managed database failover, durable job execution, and independent service scaling.

## Current Staging Domain

The current domain is `foxpilot.in`, registered and managed at GoDaddy. The planned hostnames are:

```text
https://foxpilot.in       frontend
https://api.foxpilot.in   API
```

Keep GoDaddy as the DNS provider initially. Do not publish records until the corresponding staging services and certificates are ready. Regional API certificates belong in `ap-south-1`. If CloudFront serves the frontend, its ACM certificate must be created in `us-east-1`, even though the application region is Mumbai.

## Free-Tier Staging Profile

For the prototype, use free-tier or account-credit resources only as a private staging environment:

- Deploy the frontend on a free static CDN host or S3/CloudFront.
- Use one small Mumbai compute service for API and worker only if the AWS account is eligible.
- Use free-tier-eligible RDS PostgreSQL when available; otherwise use a temporary private database only for rehearsal and plan migration before production.
- Keep S3, SQS, CloudWatch, and data volumes within documented free/credit limits.
- Apply a monthly AWS budget and billing alarm before provisioning anything.
- Apply an OpenAI project spending limit separately; AWS free usage does not cover OpenAI calls.
- Do not onboard public users, store unreviewed sensitive data, or claim availability from this profile.

The free-tier profile is a cost-controlled staging path, not a production approval. Production requires the managed service shape and recovery controls below.

## Manual Prerequisites

Complete these steps before requesting a deployment:

### AWS account

1. Create or select the AWS account that will own FoxPilot.
2. Enable billing alerts and a monthly budget before creating resources.
3. Enable MFA on the root account.
4. Do not use the root account for deployments.
5. Create an admin/bootstrap identity only for infrastructure setup.
6. Create a least-privilege deployment role for CI/CD after the first setup.
7. Select region `ap-south-1` (Mumbai) for all regional resources.
8. Record the AWS account ID privately; do not commit it to the repository.
9. Choose the AWS Free Plan or apply available new-account credits for prototype staging, understanding that AWS and OpenAI usage are billed separately.

### Domain and DNS

1. Confirm control of the domain registrar/DNS provider.
2. Use `foxpilot.in` for the frontend and `api.foxpilot.in` for the API.
3. Keep DNS at the current provider or transfer it to Route 53.
4. Do not change DNS until the staging deployment has passed health and TLS checks.
5. Plan temporary validation records for ACM certificates.

### OpenAI

1. Create or select the OpenAI project for FoxPilot.
2. Create a restricted API key for the production worker only.
3. Set a project spending limit and usage alert.
4. Confirm the selected model is available to the project.
5. Confirm that sending resume text and job descriptions to OpenAI is acceptable for the product’s privacy policy.
6. Store the key only in AWS Secrets Manager.
7. Never put the key in `.env`, CI logs, source code, or issue comments.

### Google OAuth

1. Create a Google OAuth web client for production.
2. Add the exact callback URL:
   ```text
   https://api.your-domain.example/api/v1/auth/google/callback
   ```
3. Keep the client secret in AWS Secrets Manager.
4. Add the production frontend URL to the allowed origin configuration.
5. Test both new Google registration and linking to an existing email account in staging.

### Email delivery

1. Select an SMTP provider or transactional email provider.
2. Verify the sender domain and sender address.
3. Configure SPF, DKIM, and DMARC according to the provider instructions.
4. Create credentials limited to sending FoxPilot account email.
5. Store credentials in AWS Secrets Manager.
6. Test verification and password-reset messages in staging.

## Required Code Gates

The following are blocking engineering items, not optional deployment configuration:

- [ ] API-only authenticated CLI operations are implemented.
- [ ] Production clients cannot connect directly to PostgreSQL.
- [ ] FastAPI in-process background tasks are replaced by a durable worker/queue.
- [ ] Job claiming is atomic and workers use leases/heartbeats.
- [ ] Profile and match jobs are revision-safe and idempotent.
- [ ] Source retries are bounded and classified as transient/permanent.
- [ ] PostgreSQL migrations run as a release step.
- [ ] PostgreSQL indexes and connection pool limits are configured.
- [ ] Original resumes use encrypted private object storage.
- [ ] Resume deletion and retention controls are implemented and tested.
- [ ] API responses are paginated and do not return unnecessary resume/job payloads.
- [ ] Production rate limiting uses shared infrastructure rather than process memory.
- [ ] Structured logs omit API keys, resume text, and full job descriptions.
- [ ] Health checks distinguish liveness, readiness, database, queue, and provider availability.
- [ ] Python pre-ranking limits semantic AI calls to necessary candidates.
- [ ] Full browser/API/multi-user E2E tests pass against staging.
- [ ] Backup restore has been tested, not just backup creation.
- [ ] Dependency and container image scanning pass.

## AWS Provisioning Order

Create resources in this order:

1. AWS account controls, MFA, budget, region, and deployment identity.
2. VPC, private subnets, public load-balancer subnets, security groups, and egress controls.
3. RDS PostgreSQL in private subnets with encryption, backups, deletion protection, and restricted inbound access.
4. S3 resume bucket with Block Public Access, versioning, lifecycle policy, and SSE-KMS.
5. SQS queues for profile, scan, and matching jobs with dead-letter queues.
6. Secrets Manager entries for database, OpenAI, SMTP, Google OAuth, and session configuration.
7. ECR repositories and immutable image tags for API and worker images.
8. ECS cluster, API service, worker service, task roles, autoscaling, and health checks.
9. CloudWatch log groups, metrics, alarms, and notification destination.
10. S3/CloudFront frontend deployment.
11. ACM certificates and API/frontend domain routing.
12. Staging smoke tests and backup-restore rehearsal.
13. Production promotion only after staging approval.

## Secret Names

Use platform secret references rather than raw values in task definitions where supported. The application configuration should map at least:

```text
DATABASE_URL
OPENAI_API_KEY
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
EMAIL_SMTP_HOST
EMAIL_SMTP_USERNAME
EMAIL_SMTP_PASSWORD
SESSION_SECRET
FOXPILOT_PUBLIC_URL
```

Production must use:

```env
FOXPILOT_ENV=production
FOXPILOT_AUTH_MODE=native
LLM_PROVIDER=openai
```

Do not use the development PostgreSQL password, token auth, localhost origins, or `FOXPILOT_AUTH_MODE=local` in production.

## Migration And Release Procedure

1. Build immutable API and worker images from a reviewed commit.
2. Run unit, integration, lint, type, dependency, and image checks.
3. Create a staging database from the production schema migrations.
4. Run:
   ```bash
   alembic upgrade head
   ```
5. Execute profile upload, scan, matching, auth, OAuth, password-reset, and application-tracking smoke tests.
6. Verify user A cannot access user B’s profile, matches, applications, or job actions.
7. Verify worker retries and dead-letter behavior.
8. Verify logs contain no resume text or secrets.
9. Verify backup creation and restore into an isolated database.
10. Promote the same image digest and migration set to production.
11. Run production health checks.
12. Monitor errors, latency, queue depth, database connections, OpenAI usage, and source failures.

## Rollback

Rollback must cover both application and schema changes:

- Keep the previous API and worker image available.
- Prefer backward-compatible migrations.
- Stop new job intake before rollback when schema compatibility is uncertain.
- Revert the API/worker image, not the database destructively.
- Restore the database only after incident review confirms data corruption or loss.
- Preserve logs and job records for investigation.

## Go/No-Go Checklist

Production is **no-go** if any of these are true:

- Database credentials are present on a client machine.
- Resumes are publicly readable.
- Production jobs run only inside an API web process.
- There is no tested restore path.
- Authenticated user isolation is not tested.
- OpenAI consent/disclosure is missing.
- SMTP, OAuth, or session secrets are placeholders.
- The API has no TLS or production origin restriction.
- The deployment depends on a mutable `latest` image.
- Billing alerts are not configured.
- The staging flow has not completed successfully.
