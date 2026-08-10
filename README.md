# b2b-eks-platform

B2B commerce microservices on Amazon EKS (eu-west-2): GitOps, CI/CD, observability, and an AIOps chaos demo.

> Skeleton only for now. Design notes live outside this repo until a later publish phase. Full README comes after the platform works end to end.

## Layout

| Path | Purpose |
|---|---|
| `app/` | Five FastAPI services, shared lib, local Compose |
| `eks-frontend/` | Static storefront SPA (S3 + CloudFront later) |
| `gateway/` | Local nginx edge mirroring CloudFront |
| `kubernetes/` | Helm chart + ArgoCD apps |
| `terraform/` | `persistent/` (survives teardown) + `cluster/` + modules |
| `load-tests/` | Locust chaos job |
| `aiops/` | Runbooks + remediation Lambda |
| `.github/workflows/` | CI/CD |
| `docs/` | Published design docs (later) |

## Quick start (local)

Coming in Phase 2 — `app/docker-compose.yml`.
