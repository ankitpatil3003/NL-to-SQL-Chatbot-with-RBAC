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
variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
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
variable "llm_chain" {
  type    = string
  default = "openrouter:nvidia/nemotron-3-super-120b-a12b:free,anthropic:claude-sonnet-5"
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
