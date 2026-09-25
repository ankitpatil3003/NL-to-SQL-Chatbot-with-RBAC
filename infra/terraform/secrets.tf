# Two secrets, both injected into ECS tasks as environment variables (never baked into images):
#
#  app  - generated here: database URL, JWT key, reader-login passwords, the CloudFront origin
#         header value, demo password. Lives in Terraform state, which is in an encrypted,
#         versioned, private S3 bucket.
#  llm  - LLM provider keys. Created with placeholders; you set the real values with the AWS CLI
#         (see infra/README.md). Terraform ignores later changes, so the keys never enter state.

resource "random_password" "jwt" {
  length  = 48
  special = false
}

resource "random_password" "scoped_reader" {
  length  = 32
  special = false
}

resource "random_password" "exec_reader" {
  length  = 32
  special = false
}

resource "random_password" "origin_verify" {
  length  = 40
  special = false
}

resource "aws_secretsmanager_secret" "app" {
  name                    = "${var.project}/app"
  recovery_window_in_days = 0 # demo: allow clean destroy/recreate
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    DATABASE_URL              = local.db_url
    JWT_SECRET                = random_password.jwt.result
    DB_SCOPED_READER_PASSWORD = random_password.scoped_reader.result
    DB_EXEC_READER_PASSWORD   = random_password.exec_reader.result
    DEMO_PASSWORD             = var.demo_password
    ORIGIN_VERIFY             = random_password.origin_verify.result
  })
}

resource "aws_secretsmanager_secret" "llm" {
  name                    = "${var.project}/llm"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "llm" {
  secret_id = aws_secretsmanager_secret.llm.id
  secret_string = jsonencode({
    OPENROUTER_API_KEY = "set-me"
    ANTHROPIC_API_KEY  = "set-me"
  })
  lifecycle {
    ignore_changes = [secret_string] # real keys are set out of band and never enter state
  }
}

locals {
  app_secret = aws_secretsmanager_secret.app.arn
  llm_secret = aws_secretsmanager_secret.llm.arn
}
