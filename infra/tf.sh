#!/usr/bin/env bash
# Run Terraform from the official Docker image (no local install needed).
#   infra/tf.sh main  <terraform args...>     # the application stack (infra/terraform)
#   infra/tf.sh bootstrap <args...>           # the one-time state bucket (infra/terraform/bootstrap)
# AWS credentials come from ~/.aws (mounted read-only) and/or AWS_* environment variables.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
stack="${1:?usage: tf.sh main|bootstrap <terraform args>}"; shift
dir="$here/terraform"; [ "$stack" = "bootstrap" ] && dir="$here/terraform/bootstrap"
host_path() { command -v cygpath >/dev/null && cygpath -m "$1" || echo "$1"; }   # Windows Git Bash
tty=(); [ -t 0 ] && tty=(-t)
MSYS_NO_PATHCONV=1 exec docker run --rm -i "${tty[@]}" \
  -v "$(host_path "$dir")":/work -w /work \
  -v "$(host_path "$HOME/.aws")":/root/.aws:ro \
  -e AWS_PROFILE -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_SESSION_TOKEN -e AWS_REGION \
  hashicorp/terraform:1.12 "$@"
