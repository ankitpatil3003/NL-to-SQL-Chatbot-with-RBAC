variable "project" {
  type    = string
  default = "novapharma-nl2sql"
}

variable "region" {
  type    = string
  default = "us-east-2" # user decision
}

variable "image_tag" {
  description = "Tag of the api/web/loader images in ECR (the deploy script uses the git sha)."
  type        = string
}

# --- Sizing: user decision "minimal (~$60/mo)" ---------------------------------------------------
# db.t4g.micro (1 GB) failed in production: the 2M-row load drained its CPU credits and ~550 MB of
# sales + indexes couldn't stay cached, so a 50 ms query hit the 15 s statement timeout. small
# (2 GB, twice the credit rate) keeps the hot data cached (user decision, +~$12/mo).
variable "db_instance_class" {
  type    = string
  default = "db.t4g.small"
}

variable "api_cpu" {
  type    = number
  default = 512 # measured idle: 326 MB with the embedding model loaded
}

variable "api_memory" {
  type    = number
  default = 1024
}

variable "web_cpu" {
  type    = number
  default = 256
}

variable "web_memory" {
  type    = number
  default = 512
}

# --- App configuration ----------------------------------------------------------------------------
# Production inference (user decision, paid from AWS credits): Claude in Amazon Bedrock for low
# latency, Haiku 4.5 for the small steps (understanding, answer, title) and Sonnet 5 for SQL, with
# free Nemotron on OpenRouter as the fallback, and the direct Anthropic API as the last resort (the
# first live question hit a Bedrock access error and an Nvidia 503 at the same moment).
variable "llm_chain" {
  type    = string
  default = "bedrock:anthropic.claude-haiku-4-5,openrouter:nvidia/nemotron-3-super-120b-a12b:free,anthropic:claude-haiku-4-5"
}

# Bedrock's model catalogue differs by region: on first deploy anthropic.claude-sonnet-5 returned 404
# in us-east-2 and Haiku 4.5 wasn't in its console catalogue, while us-east-1 lists both. Inference
# runs there; the app stays in var.region.
# Cross-region adds ~10-15 ms per call; the task role's permission isn't region-scoped.
variable "bedrock_region" {
  type    = string
  default = "us-east-1"
}

variable "llm_chain_sql" {
  type    = string
  default = "bedrock:anthropic.claude-sonnet-5,openrouter:nvidia/nemotron-3-super-120b-a12b:free,anthropic:claude-sonnet-5"
}

variable "chat_rate_limit_per_hour" {
  type    = number
  default = 10 # user decision
}

variable "demo_password" {
  description = "Shared demo password for the seeded users (shown on the login page)."
  type        = string
  default     = "novapharma-demo"
}
