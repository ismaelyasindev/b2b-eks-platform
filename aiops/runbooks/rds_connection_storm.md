# Runbook: RDS Connection Storm via Signup Fan-Out

## Symptoms
- Prometheus alert: RDSConnectionStorm (active connections > 50)
- OTEL traces: high db wait time on /auth/signup spans
- WAF status: Normal

## Remediation Strategy
Do NOT mutate AWS WAFv2 directly — ArgoCD/Terraform own that state and
self-heal would revert the change (GitOps drift).
Apply the emergency application throttle: write a temporary rate-limit
flag for /auth/signup to the DynamoDB ai-throttle-config table.
The item must carry an ExpiresAt TTL so it auto-purges.
