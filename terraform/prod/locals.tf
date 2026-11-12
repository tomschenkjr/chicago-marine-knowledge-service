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
  port_name          = "http"
  discovery_name     = "cmk-service"
}
