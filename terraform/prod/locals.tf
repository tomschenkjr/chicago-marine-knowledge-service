locals {
  aws_region         = "us-east-1"
  service_name       = "chicago-marine-knowledge-service"
  repo_full_name     = "tomschenkjr/chicago-marine-knowledge-service"
  container_port     = 8000
  cluster_name       = "mcp-cluster"
  ecr_repo           = "chicago-marine-knowledge-service"
  log_retention_days = 7
  cpu                = 512
  memory             = 1024
  internal_alb_name  = "cmk-service-internal"
  target_group_name  = "cmk-service"
  service_url_scheme = "http"
}
