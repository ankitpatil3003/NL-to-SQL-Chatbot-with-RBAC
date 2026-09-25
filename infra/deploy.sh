#!/usr/bin/env bash
# Deploy the app to AWS (see infra/README.md for the one-time setup and costs).
#
#   infra/deploy.sh bootstrap   # once: create the Terraform state bucket, write backend.hcl
#   infra/deploy.sh up          # init -> ECR repos -> build+push images -> full apply -> smoke test
#   infra/deploy.sh load        # run the one-off data loader task (first deploy, or to reload)
#   infra/deploy.sh smoke       # check the public URL end to end
#   infra/deploy.sh down        # destroy everything (the state bucket stays)
#
# Images are tagged with the git commit (plus -dirty for uncommitted changes); ECR tags are
# immutable, so an already-pushed tag is reused rather than overwritten.
set -euo pipefail
cd "$(dirname "$0")/.."
TF=infra/tf.sh
REGION="${AWS_REGION:-us-east-2}"

tag() {
  local t; t="$(git rev-parse --short HEAD)"
  [ -n "$(git status --porcelain)" ] && t="$t-dirty-$(date +%s)"
  echo "$t"
}
out() { $TF main output -raw "$1"; }
out_json() { $TF main output -json "$1"; }

cmd_bootstrap() {
  $TF bootstrap init -input=false
  $TF bootstrap apply -input=false -auto-approve
  local bucket; bucket="$($TF bootstrap output -raw state_bucket)"
  printf 'bucket = "%s"\nregion = "%s"\n' "$bucket" "$REGION" > infra/terraform/backend.hcl
  echo "state bucket: $bucket (written to infra/terraform/backend.hcl)"
}

push_images() {
  local tag="$1" registry repos
  registry="$(out ecr_registry)"
  repos="$(out_json ecr_repositories)"
  aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$registry" >/dev/null
  for name in api web loader; do
    local repo; repo="$(echo "$repos" | python -c "import json,sys; print(json.load(sys.stdin)['$name'])")"
    if aws ecr describe-images --region "$REGION" --repository-name "${repo#*/}" --image-ids imageTag="$tag" >/dev/null 2>&1; then
      echo "$name:$tag already in ECR"; continue
    fi
    case "$name" in
      api) docker build -f services/api/Dockerfile -t "$repo:$tag" . ;;
      web) docker build --build-arg API_INTERNAL_URL= -t "$repo:$tag" apps/web ;;  # ALB routes /api/*
      loader) docker build -f scripts/Dockerfile.loader -t "$repo:$tag" . ;;
    esac
    docker push "$repo:$tag"
  done
}

cmd_up() {
  local tag; tag="$(tag)"
  [ -f infra/terraform/backend.hcl ] || { echo "run: infra/deploy.sh bootstrap"; exit 1; }
  $TF main init -input=false -backend-config=backend.hcl
  # ECR repositories must exist before images can be pushed; services need the images.
  $TF main apply -input=false -auto-approve -var "image_tag=$tag" -target=aws_ecr_repository.repo
  push_images "$tag"
  $TF main apply -input=false -auto-approve -var "image_tag=$tag"
  echo "waiting for the services to become stable..."
  aws ecs wait services-stable --region "$REGION" --cluster "$(out cluster)" --services api web
  echo "deployed $tag -> $(out url)"
  cmd_smoke
}

cmd_load() {
  local loader cluster task
  loader="$(out_json loader)"; cluster="$(out cluster)"
  read -r taskdef subnets sg < <(echo "$loader" | python -c "
import json,sys; d=json.load(sys.stdin); print(d['task_definition'], ','.join(d['subnets']), d['security_group'])")
  task="$(aws ecs run-task --region "$REGION" --cluster "$cluster" --launch-type FARGATE \
    --task-definition "$taskdef" \
    --network-configuration "awsvpcConfiguration={subnets=[$subnets],securityGroups=[$sg],assignPublicIp=ENABLED}" \
    --query 'tasks[0].taskArn' --output text)"
  echo "loader task: $task (generating and loading 2M rows, ~2-3 min)"
  aws ecs wait tasks-stopped --region "$REGION" --cluster "$cluster" --tasks "$task"
  local code; code="$(aws ecs describe-tasks --region "$REGION" --cluster "$cluster" --tasks "$task" \
    --query 'tasks[0].containers[0].exitCode' --output text)"
  aws logs tail "/ecs/novapharma-nl2sql/loader" --region "$REGION" --since 15m | tail -25
  [ "$code" = "0" ] || { echo "loader failed (exit $code)"; exit 1; }
  # The API syncs credentials and the knowledge index at startup: restart it onto the new data.
  aws ecs update-service --region "$REGION" --cluster "$cluster" --service api --force-new-deployment >/dev/null
  aws ecs wait services-stable --region "$REGION" --cluster "$cluster" --services api
  echo "data loaded; api restarted"
}

cmd_smoke() {
  local url; url="$(out url)"
  for path in /healthz /login /api/auth/demo-accounts; do
    printf '%-26s %s\n' "$path" "$(curl -s -o /dev/null -w '%{http_code}' "$url$path")"
  done
  echo "ALB without the CloudFront header must be refused: $(curl -s -o /dev/null -w '%{http_code}' "http://$(aws elbv2 describe-load-balancers --region "$REGION" --names novapharma-nl2sql --query 'LoadBalancers[0].DNSName' --output text)/login" || true)"
  echo "open: $url"
}

cmd_down() {
  $TF main destroy -input=false -var "image_tag=unused"
}

"cmd_${1:?usage: deploy.sh bootstrap|up|load|smoke|down}"
