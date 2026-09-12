<p align="center">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=28&pause=1200&color=E0218A&center=true&vCenter=true&width=820&lines=B2B+EKS+Platform;GitOps+%2B+OIDC+on+AWS;Argo+CD+%C2%B7+AIOps+%C2%B7+CloudFront" alt="Typing SVG" />
</p>

<h1 align="center">B2B EKS Platform — Microservices on Amazon EKS</h1>

<p align="center">
  <strong>Five FastAPI services on one EKS cluster</strong> — Terraform (persistent + cluster), Argo CD GitOps,
  GitHub Actions OIDC into ECR, ALB + WAF at the edge, CloudFront storefront, and an AIOps loop
  (Locust → Prometheus → SNS → Lambda / Bedrock → DynamoDB → auth 429).<br/>
  <em>Live in <code>eu-west-2</code>. Destroy the cluster stack when the demo window ends; persistent (ECR, OIDC, AIOps, storefront bucket) stays.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Live%20%7C%20eu--west--2-059669?style=for-the-badge" alt="Status" />
  <a href="https://github.com/ismaelyasindev/b2b-eks-platform/actions"><img src="https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white" alt="Actions" /></a>
  <a href="https://d2dx5pzn9z18zo.cloudfront.net"><img src="https://img.shields.io/badge/Storefront-CloudFront-E0218A?style=for-the-badge" alt="Storefront" /></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/AWS-232F3E?style=flat-square&logo=amazonaws&logoColor=white" alt="AWS" />
  <img src="https://img.shields.io/badge/EKS-FF9900?style=flat-square&logo=amazoneks&logoColor=white" alt="EKS" />
  <img src="https://img.shields.io/badge/Terraform-844FBA?style=flat-square&logo=terraform&logoColor=white" alt="Terraform" />
  <img src="https://img.shields.io/badge/Argo%20CD-EF7B4D?style=flat-square&logo=argo&logoColor=white" alt="Argo CD" />
  <img src="https://img.shields.io/badge/Helm-0F1689?style=flat-square&logo=helm&logoColor=white" alt="Helm" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Prometheus-E6522C?style=flat-square&logo=prometheus&logoColor=white" alt="Prometheus" />
  <img src="https://img.shields.io/badge/Grafana-F46800?style=flat-square&logo=grafana&logoColor=white" alt="Grafana" />
  <img src="https://img.shields.io/badge/Bedrock-232F3E?style=flat-square&logo=amazonaws&logoColor=white" alt="Bedrock" />
  <img src="https://img.shields.io/badge/OIDC-2088FF?style=flat-square&logo=openid&logoColor=white" alt="OIDC" />
  <img src="https://img.shields.io/badge/Trivy-1904DA?style=flat-square&logo=aquasecurity&logoColor=white" alt="Trivy" />
  <img src="https://img.shields.io/badge/Checkov-0A2540?style=flat-square&logo=checkmarx&logoColor=white" alt="Checkov" />
</p>

---

## Why this project

Most “hello world on EKS” repos stop at a Deployment and a LoadBalancer. This one is built like a **real multi-service platform**:

- Infrastructure is **Terraform in two layers** — `persistent/` survives teardown; `cluster/` is EKS, VPC, RDS, Karpenter
- Images ship with **GitHub OIDC → ECR** (no long-lived AWS keys); Argo CD syncs Helm to `dev` / `prod`
- Edge is **ALB (path prefixes) + regional WAF**; storefront is **S3 + CloudFront** (OAC, `/api` strip)
- Observability is **kube-prometheus-stack + postgres-exporter**
- AIOps is a **closed loop**: connection storm → alert → SNS → Lambda / Haiku → DynamoDB TTL → **HTTP 429** on `/auth/signup`

> Modelled on the “Online Boutique” shape (one cluster, many services) — Python/FastAPI, one Postgres per env with schema isolation, GitOps, and a chaos demo you can screenshot.

---

## Demo

Storefront on **CloudFront** (S3 origin + `/api/*` to the prod ALB). Same shop a recruiter opens in the browser.

<p align="center">
  <a href="https://d2dx5pzn9z18zo.cloudfront.net"><img src="https://img.shields.io/badge/Live%20storefront-d2dx5pzn9z18zo.cloudfront.net-E0218A?style=for-the-badge" alt="Live storefront" /></a>
</p>

![Storefront demo](docs/assets/09-storefront-demo.mp4)

<p align="center">
  <em>If the player does not start, open <a href="docs/assets/09-storefront-demo.mp4">docs/assets/09-storefront-demo.mp4</a> on GitHub (browser-native MP4). The original QuickTime file is <a href="docs/assets/09-storefront-demo.mov">09-storefront-demo.mov</a>.</em>
</p>

---

## What runs where

| Layer | What it owns |
|-------|----------------|
| **Persistent** | ECR, Secrets Manager envelopes, GitHub OIDC roles, AIOps (SNS, Lambda, DynamoDB, runbooks bucket), storefront S3 |
| **Cluster** | VPC, NAT, EKS, node group + Karpenter, RDS `dev`/`prod`, SQS, WAF, ALB controller, Argo CD, CloudFront |
| **GitOps** | App-of-Apps + ApplicationSet for five services × two namespaces |
| **Edge** | Prod ALB group `b2b-platform-prod`; CloudFront default domain; WAF on the ALB (not on CloudFront) |

---

## Infrastructure highlights

<table>
<tr>
<td width="50%">

### Cluster & GitOps
- EKS **1.33** in **eu-west-2**, Karpenter for burst (Locust)
- **Argo CD** Helm from git; image tags in `values-dev.yaml` / `values-prod.yaml`
- **Pod Identity** for DB secrets, SQS, Alertmanager SNS, ALB controller

</td>
<td width="50%">

### Edge
- Ingress **ALB**, `target-type: ip`, path prefixes `/auth` `/product` …
- **WAF** WebACL on the ALB (rate-limit / managed rules)
- **CloudFront**: private S3 (OAC) + ALB origin; Function strips `/api`

</td>
</tr>
<tr>
<td width="50%">

### Data
- RDS **Postgres 16**, one instance per env
- Per-service DB users (`auth_user`, …) + `exporter_user`
- Secrets Manager → Kubernetes secrets (not in git)

</td>
<td width="50%">

### Observability & AIOps
- Grafana / Prometheus; `pg_stat_activity_count`
- Alert `RDSConnectionStorm` → SNS `aiops-alerts`
- Lambda + **Bedrock Haiku 4.5** (EU inference profile) → DynamoDB throttle flag

</td>
</tr>
</table>

---

## AIOps loop (proven)

In-cluster Locust hits `auth-svc.prod` with `X-Trigger-Storm` so signup holds DB connections. Prometheus fires when `sum(pg_stat_activity_count{state="active"}) > 50` for 30s. Alertmanager publishes to SNS; Lambda reads the S3 runbook, calls Bedrock, writes `AI_EMERGENCY_SIGNUP_THROTTLE` (TTL). Auth pods poll DynamoDB and return **429** before Postgres.

WAF stays **Normal** on purpose — Locust never goes through the ALB.

<p align="center"><strong>1 — Grafana baseline</strong></p>
<p align="center">
  <img src="docs/assets/01-grafana-baseline.png" alt="Grafana baseline active connections" width="900" />
</p>

<p align="center"><strong>2 — RDS connection storm</strong></p>
<p align="center">
  <img src="docs/assets/02-grafana-rds-storm.png" alt="Grafana RDSConnectionStorm firing" width="900" />
</p>

<p align="center"><strong>3 — Locust spike</strong></p>
<p align="center">
  <img src="docs/assets/03-grafana-locust-spike.png" alt="Grafana active connections spike under Locust" width="900" />
</p>

<p align="center"><strong>4 — DynamoDB emergency throttle</strong></p>
<p align="center">
  <img src="docs/assets/04-dynamodb-throttle.jpg" alt="DynamoDB ai-throttle-config item" width="720" />
</p>

<p align="center"><strong>5 — Auth signup 429</strong></p>
<p align="center">
  <img src="docs/assets/05-auth-429.jpg" alt="HTTP 429 from /auth/signup" width="720" />
</p>

<p align="center"><strong>6 — SNS topic aiops-alerts</strong></p>
<p align="center">
  <img src="docs/assets/06-sns-topic.png" alt="SNS aiops-alerts topic" width="900" />
</p>

<p align="center"><strong>7 — Lambda monitoring</strong></p>
<p align="center">
  <img src="docs/assets/07-lambda-dashboard.png" alt="Lambda b2b-aiops-remediation monitor" width="900" />
</p>

<p align="center"><strong>8 — Lambda logs (Bedrock + PutItem)</strong></p>
<p align="center">
  <img src="docs/assets/08-lambda-logs.png" alt="Lambda CloudWatch logs" width="900" />
</p>

---

## CI/CD — OIDC, no long-lived AWS keys

Secrets store **role ARNs** — never AWS access keys.

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `01 - Test, Build & Push` | `app/**` or manual | Ruff, pytest, Docker, **Trivy** HIGH/CRITICAL, push `dev-<sha>` to ECR, PR to bump `values-dev.yaml` |
| `01b - Promote to Production` | Manual (`sha`) | Retag `dev-<sha>` → `prod-<sha>`, PR for `values-prod.yaml` |
| `02 - Infrastructure Lint & Plan` | `terraform/**` or manual | `fmt`, validate, TFLint, **Checkov** (soft-fail on persistent), `terraform plan` |
| `03 - Infrastructure Apply` | Manual | Apply `persistent` or `cluster` |
| `05 - Deploy Storefront` | `eks-frontend/**` or manual | `s3 sync` + CloudFront invalidation |
| `04 - Terraform Destroy` | Manual | Tear down **cluster** (keep persistent) |

<p align="center">
  <a href="https://github.com/ismaelyasindev/b2b-eks-platform/actions/workflows/build-and-push.yml"><img src="https://github.com/ismaelyasindev/b2b-eks-platform/actions/workflows/build-and-push.yml/badge.svg" alt="01 build-and-push" /></a>
  <a href="https://github.com/ismaelyasindev/b2b-eks-platform/actions/workflows/terraform-plan.yml"><img src="https://github.com/ismaelyasindev/b2b-eks-platform/actions/workflows/terraform-plan.yml/badge.svg" alt="02 terraform-plan" /></a>
  <a href="https://github.com/ismaelyasindev/b2b-eks-platform/actions/workflows/deploy-frontend.yml"><img src="https://github.com/ismaelyasindev/b2b-eks-platform/actions/workflows/deploy-frontend.yml/badge.svg" alt="05 deploy-frontend" /></a>
</p>

---

## Repository layout

```text
├── .github/workflows/     # OIDC: build, promote, plan, apply, destroy, storefront
├── app/                   # Five FastAPI services + Compose + Dockerfile
├── eks-frontend/          # Static storefront (S3 + CloudFront)
├── gateway/               # Local nginx /api strip (Compose --profile ui)
├── kubernetes/            # Helm chart + Argo CD apps
├── terraform/
│   ├── bootstrap/         # State bucket + lock (once)
│   ├── persistent/        # ECR, OIDC, AIOps, storefront bucket
│   ├── cluster/           # VPC, EKS, RDS, WAF, CloudFront
│   └── modules/
├── load-tests/            # Locust Job (manual Argo sync)
├── aiops/                 # Runbook + remediation Lambda
├── scripts/               # RDS role seed (optional)
└── docs/assets/           # README evidence stills
```

---

## Deploy model

### First-time (local Terraform, then GitOps)

```bash
cd terraform/persistent
terraform init && terraform apply

cd ../cluster
terraform init && terraform apply
```

Set `api_origin_domain` in `terraform/cluster/terraform.tfvars` (gitignored) to the **prod ALB hostname** after Ingress is ready, then apply again to create CloudFront.

Images: merge the automated **dev** PR from workflow 01; promote with **01b** using the SHA that **01** actually built.

### Storefront

```bash
aws s3 sync eks-frontend/ s3://b2b-platform-storefront-london/ --delete --region eu-west-2
# or GitHub Actions 05 — Deploy Storefront Frontend
```

### Safety rails

- **Persistent vs cluster** state files — destroy cluster without wiping ECR/OIDC
- Trivy **exit-code 1** on HIGH/CRITICAL (OS patches via `apt-get upgrade` in the Dockerfile)
- Locust Application has **no automated sync**
- `terraform.tfvars` is gitignored

---

## Security model (short version)

| Control | Implementation |
|---------|----------------|
| No public storefront bucket | CloudFront **OAC** only |
| No long-lived AWS keys in CI | **GitHub OIDC** assume-role |
| App secrets | Secrets Manager + Pod Identity `GetSecretValue` |
| Edge abuse | **WAF** on the ALB (Locust bypasses it by design) |
| Storm stop | App-level 429 + DynamoDB **TTL** — no GitOps drift on WAF |
| Image scan | Trivy in Actions before ECR push |

---

## Teardown

When the live window ends, destroy **cluster** only (NAT, EKS, RDS, CloudFront). Keep **persistent**.

| Destroy (cluster) | Retain (persistent) |
|-------------------|---------------------|
| VPC, NAT, EKS, RDS, ALBs, WAF, CloudFront | ECR images, OIDC roles, Secrets Manager |
| Node groups / Karpenter nodes | SNS, Lambda, DynamoDB throttle table, runbooks S3 |
| | Storefront bucket, tfstate bucket |

Park overnight without destroy: stop both RDS instances; delete the Locust Job.

---

## Run locally (no AWS required)

```bash
cd app
cp .env.example .env   # if present
docker compose up --build
```

Optional UI (nginx `/api` strip, same contract as CloudFront):

```bash
docker compose --profile ui up --build
# http://localhost:8080
```

---

## Live verification (while deployed)

```bash
curl -sS -o /dev/null -w '%{http_code}\n' \
  https://d2dx5pzn9z18zo.cloudfront.net/

curl -sS -o /dev/null -w '%{http_code}\n' -X POST \
  http://k8s-b2bplatformprod-b799c3a98a-1823785693.eu-west-2.elb.amazonaws.com/auth/signup \
  -H 'Content-Type: application/json' \
  -d '{"email":"probe@example.com"}'
```

| Check | Expected (when live) |
|-------|----------------------|
| CloudFront `/` | Storefront HTML |
| Catalog | `/api/product/list` via CloudFront → ALB `/product/list` |
| AIOps (after storm + Lambda) | `/auth/signup` **429** while the DynamoDB TTL is valid |
| GitHub Actions | 01 / 02 / 05 green |

---

## Author

**Ismael Yasin** — DevOps & Cloud Engineer  
Portfolio: [ismaelyasin.site](https://www.ismaelyasin.site) · GitHub: [ismaelyasindev](https://github.com/ismaelyasindev)

---

<p align="center">
  <em>Built for production habits — Terraform, OIDC, GitOps, and an AIOps loop you can screenshot.</em>
</p>
