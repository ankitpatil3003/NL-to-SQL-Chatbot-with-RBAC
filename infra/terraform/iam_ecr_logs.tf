# --- ECR: one repository per image ----------------------------------------------------------------
locals {
  images = ["api", "web", "loader"]
}

resource "aws_ecr_repository" "repo" {
  for_each             = toset(local.images)
  name                 = "${var.project}/${each.key}"
  image_tag_mutability = "IMMUTABLE" # a deployed tag always means the same image
  force_delete         = true        # demo: allow clean destroy
  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "keep_recent" {
  for_each   = aws_ecr_repository.repo
  repository = each.value.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "keep the 10 most recent images"
      selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 10 }
      action       = { type = "expire" }
    }]
  })
}

# --- Logs ------------------------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "svc" {
  for_each          = toset(local.images)
  name              = "/ecs/${var.project}/${each.key}"
  retention_in_days = 14
}

# --- IAM ---------------------------------------------------------------------------------------------
# Execution role: what ECS itself needs to start a task (pull the image, write logs, read the two
# secrets into environment variables). The containers get a task role with no permissions: the
# app talks to Postgres and LLM APIs, not to AWS.
data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "execution" {
  name               = "${var.project}-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy_attachment" "execution_managed" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "execution_secrets" {
  name = "read-app-secrets"
  role = aws_iam_role.execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [local.app_secret, local.llm_secret]
    }]
  })
}

resource "aws_iam_role" "task" {
  name               = "${var.project}-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

# The API calls Bedrock models as this role: Claude via the Messages endpoint (bedrock-mantle) and
# every other family via the Converse API (bedrock:InvokeModel, incl. cross-region profiles).
resource "aws_iam_role_policy" "task_bedrock" {
  name = "invoke-claude-on-bedrock"
  role = aws_iam_role.task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["bedrock-mantle:CreateInference", "bedrock:InvokeModel"]
      Resource = "*" # ponytail: any model; scope to the two model ARNs once their format is pinned
    }]
  })
}
