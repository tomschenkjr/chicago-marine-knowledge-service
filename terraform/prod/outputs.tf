output "service_internal_url" {
  description = "Service Connect URL for MCP tasks in the mcp namespace to call the knowledge service"
  value       = "http://${local.discovery_name}:${local.container_port}"
}

output "ecr_repository_url" {
  description = "ECR repository URL for the knowledge service image"
  value       = aws_ecr_repository.service.repository_url
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.service.name
}

output "github_oidc_role_arn" {
  description = "GitHub Actions OIDC role ARN for service deployment"
  value       = aws_iam_role.github_actions.arn
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.service.name
}
