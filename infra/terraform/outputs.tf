output "url" {
  description = "Public HTTPS URL of the app."
  value       = local.public_url
}

output "ecr_registry" {
  value = local.registry
}

output "ecr_repositories" {
  value = { for k, r in aws_ecr_repository.repo : k => r.repository_url }
}

output "cluster" {
  value = aws_ecs_cluster.main.name
}

# Everything `aws ecs run-task` needs to start the one-off loader (used by infra/deploy.sh).
output "loader" {
  value = {
    task_definition = aws_ecs_task_definition.loader.arn
    subnets         = aws_subnet.public[*].id
    security_group  = aws_security_group.loader.id
  }
}

output "llm_secret_name" {
  description = "Set the real LLM keys here (see infra/README.md)."
  value       = aws_secretsmanager_secret.llm.name
}
