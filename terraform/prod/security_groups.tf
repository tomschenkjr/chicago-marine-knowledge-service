resource "aws_security_group" "service_tasks" {
  name        = "${local.service_name}-tasks-sg"
  description = "Task access for ${local.service_name}"
  vpc_id      = data.aws_vpc.mcp.id

  ingress {
    from_port       = local.container_port
    to_port         = local.container_port
    protocol        = "tcp"
    security_groups = [data.aws_security_group.mcp_ecs_tasks.id]
    description     = "Service Connect traffic from MCP tasks"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.service_name}-tasks-sg"
  }
}
