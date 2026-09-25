# ECS Fargate: the API and web services behind the ALB, plus a one-off loader task definition
# (run with `infra/deploy.sh load`). Tasks run in public subnets with public IPs for egress and no
# NAT; inbound is restricted to the ALB by security group.

resource "aws_ecs_cluster" "main" {
  name = var.project
  setting {
    name  = "containerInsights"
    value = "disabled" # cost; CloudWatch logs + app traces cover observability
  }
}

locals {
  registry = split("/", aws_ecr_repository.repo["api"].repository_url)[0]
  image    = { for k, r in aws_ecr_repository.repo : k => "${r.repository_url}:${var.image_tag}" }

  app_secrets = [
    for key in ["DATABASE_URL", "JWT_SECRET", "DB_SCOPED_READER_PASSWORD", "DB_EXEC_READER_PASSWORD", "DEMO_PASSWORD"] :
    { name = key, valueFrom = "${local.app_secret}:${key}::" }
  ]
  llm_secrets = [
    for key in ["OPENROUTER_API_KEY", "ANTHROPIC_API_KEY"] :
    { name = key, valueFrom = "${local.llm_secret}:${key}::" }
  ]

  log = { for k in local.images : k => {
    logDriver = "awslogs"
    options = {
      awslogs-group         = aws_cloudwatch_log_group.svc[k].name
      awslogs-region        = var.region
      awslogs-stream-prefix = k
    }
  } }
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${var.project}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
  container_definitions = jsonencode([{
    name         = "api"
    image        = local.image["api"]
    essential    = true
    portMappings = [{ containerPort = 8000, protocol = "tcp" }]
    environment = [
      { name = "APP_ENV", value = "prod" }, # Secure cookies; refuses a dev JWT secret
      { name = "LOG_LEVEL", value = "INFO" },
      { name = "LLM_CHAIN", value = var.llm_chain },
      { name = "PUBLIC_URL", value = local.public_url },
      { name = "CHAT_RATE_LIMIT_PER_HOUR", value = tostring(var.chat_rate_limit_per_hour) },
      { name = "DEMO_SHOW_CREDENTIALS", value = "true" },
    ]
    secrets          = concat(local.app_secrets, local.llm_secrets)
    logConfiguration = local.log["api"]
  }])
}

resource "aws_ecs_task_definition" "web" {
  family                   = "${var.project}-web"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.web_cpu
  memory                   = var.web_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
  container_definitions = jsonencode([{
    name             = "web"
    image            = local.image["web"]
    essential        = true
    portMappings     = [{ containerPort = 3000, protocol = "tcp" }]
    logConfiguration = local.log["web"]
  }])
}

resource "aws_ecs_task_definition" "loader" {
  family                   = "${var.project}-loader"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
  container_definitions = jsonencode([{
    name             = "loader"
    image            = local.image["loader"]
    essential        = true
    command          = ["--full", "--generate"]
    secrets          = local.app_secrets # DATABASE_URL + the reader-login passwords it sets
    logConfiguration = local.log["loader"]
  }])
}

resource "aws_ecs_service" "api" {
  name                              = "api"
  cluster                           = aws_ecs_cluster.main.id
  task_definition                   = aws_ecs_task_definition.api.arn
  desired_count                     = 1
  launch_type                       = "FARGATE"
  health_check_grace_period_seconds = 180 # first boot embeds the knowledge corpus
  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.api.id]
    assign_public_ip = true
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }
  deployment_circuit_breaker {
    enable   = true
    rollback = true # a bad image rolls back instead of taking the site down
  }
  depends_on = [aws_lb_listener_rule.api]
}

resource "aws_ecs_service" "web" {
  name                              = "web"
  cluster                           = aws_ecs_cluster.main.id
  task_definition                   = aws_ecs_task_definition.web.arn
  desired_count                     = 1
  launch_type                       = "FARGATE"
  health_check_grace_period_seconds = 60
  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.web.id]
    assign_public_ip = true
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.web.arn
    container_name   = "web"
    container_port   = 3000
  }
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  depends_on = [aws_lb_listener_rule.web]
}
