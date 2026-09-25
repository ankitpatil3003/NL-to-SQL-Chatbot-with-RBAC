# AWS deployment

```
Browser ──HTTPS──▶ CloudFront (*.cloudfront.net) ──HTTP + secret header──▶ ALB ─┬─ /*     ▶ ECS web (Next.js)
                                                                                 └─ /api/* ▶ ECS api (FastAPI) ──▶ RDS Postgres 16 (private)
                                                                                                          ├──────▶ Claude in Amazon Bedrock (task role)
                                                                                                          └──────▶ OpenRouter (fallback)
```

| Decision | Choice | Why |
|---|---|---|
| Region | `us-east-2` | full service coverage, same prices as us-east-1 |
| HTTPS | CloudFront default domain | free TLS, no domain needed; caches `/_next/static/*` |
| Origin protection | ALB SG = CloudFront origin-facing prefix list + listener requires `X-Origin-Verify` secret | the CloudFront→ALB leg is HTTP (no certificate without a domain), so nothing else can reach the ALB |
| Sizing | minimal (~$60/mo) | RDS db.t4g.micro single-AZ; api 0.5 vCPU/1 GB (measured 326 MB idle); web 0.25 vCPU/0.5 GB |
| No NAT gateway | tasks in public subnets with public IPs, inbound locked to the ALB SG | saves ~$32/mo; RDS stays in private subnets |
| Secrets | Secrets Manager, injected as env vars | generated passwords/JWT in `…/app`; LLM keys in `…/llm`, set by you, never in Terraform state |
| State | S3 backend (versioned, encrypted, private) with S3-native locking | state holds generated secrets |
| Streaming | CloudFront origin read timeout 60s + SSE heartbeat every 10s; `/api/*` uncompressed and uncached | long SQL steps can be silent for 25-35s |
| Inference | Claude in Amazon Bedrock: Haiku 4.5 for understanding/answer/title, Sonnet 5 for SQL; free Nemotron (OpenRouter), then the direct Anthropic API, as fallbacks | low latency after deploy, billed to the AWS account (credits); no Anthropic key needed. Bedrock has no `output_config`, so JSON comes from a forced tool call |
| Rate limit | 10 questions/hour/user (from turn traces) | caps LLM spend on a public URL |

## Estimated cost (us-east-2, on-demand, per month)

| Item | ~USD |
|---|---|
| Fargate api 0.5 vCPU/1 GB + web 0.25 vCPU/0.5 GB | 16 |
| Application Load Balancer | 17 |
| RDS db.t4g.micro + 20 GB gp3 | 14 |
| Public IPv4 (ALB ×2, tasks ×2) | 11 |
| Secrets Manager (2), CloudWatch logs, ECR, CloudFront (free tier) | ~3 |
| **Total** | **~$61** |

LLM usage (Bedrock, on top): roughly $0.01-0.02 per question (Sonnet 5 SQL step with the cached
semantic contract, Haiku for the rest). The 10/hour/user limit bounds it.

## Prerequisites

- Docker (Terraform runs from the `hashicorp/terraform` image via `infra/tf.sh`, nothing to install)
- AWS CLI v2 with credentials for an account where you can create VPC/ECS/RDS/CloudFront/IAM resources
  (`aws sts get-caller-identity` must succeed)
- Bedrock: submit Anthropic's one-time **use case details** form (Bedrock console → Model catalog →
  any Claude model), once per account. Without it every Claude call returns 403 "not available for
  this account". Inference runs in `us-east-1` (`var.bedrock_region`), which lists both models.

## First deploy

```bash
infra/deploy.sh bootstrap        # once: Terraform state bucket -> infra/terraform/backend.hcl
infra/deploy.sh up               # ~15-20 min the first time (RDS and CloudFront are slow to create)

# Set the fallback key (it never touches Terraform or the repo). Bedrock needs no key (task role).
# Keep both fields: ECS refuses to start a task whose secret lacks a referenced key.
aws secretsmanager put-secret-value --region us-east-2 --secret-id novapharma-nl2sql/llm \
  --secret-string '{"OPENROUTER_API_KEY":"sk-or-...","ANTHROPIC_API_KEY":"unused"}'

infra/deploy.sh load             # generate + load the 2M-row dataset (~3 min), restart the api
infra/deploy.sh smoke            # 200s through CloudFront; 403 straight to the ALB
```

Then open the printed URL, or run the browser tests against it:
`cd apps/web && E2E_BASE_URL=<url> npx playwright test` (add `E2E_LIVE=1` for a real question).

## Later deploys and teardown

```bash
infra/deploy.sh up               # builds images for the current commit, rolls both services
infra/deploy.sh down             # destroys everything except the state bucket
```

A failed deploy rolls back automatically (ECS deployment circuit breaker). Logs:
`aws logs tail /ecs/novapharma-nl2sql/api --follow --region us-east-2`.

## What I'd change for real production

Multi-AZ RDS with deletion protection and longer backups; a custom domain with an ACM certificate on the
ALB (end-to-end TLS); NAT + private task subnets; 2+ tasks per service with autoscaling; WAF on CloudFront;
CI deploys via GitHub OIDC instead of a laptop.
