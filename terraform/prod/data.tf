data "aws_caller_identity" "current" {}

data "aws_ecs_cluster" "mcp" {
  cluster_name = local.cluster_name
}

data "aws_vpc" "mcp" {
  filter {
    name   = "tag:Name"
    values = ["mcp-vpc"]
  }
}

data "aws_subnet" "private_1" {
  filter {
    name   = "tag:Name"
    values = ["mcp-private-1"]
  }
}

data "aws_subnet" "private_2" {
  filter {
    name   = "tag:Name"
    values = ["mcp-private-2"]
  }
}

data "aws_security_group" "mcp_ecs_tasks" {
  filter {
    name   = "group-name"
    values = ["mcp-ecs-tasks-sg"]
  }

  vpc_id = data.aws_vpc.mcp.id
}

data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}
