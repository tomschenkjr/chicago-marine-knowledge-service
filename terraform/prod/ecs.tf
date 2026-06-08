resource "aws_cloudwatch_log_group" "service" {
  name              = "/ecs/${local.service_name}"
  retention_in_days = local.log_retention_days

  tags = {
    Name = "${local.service_name}-logs"
  }
}

resource "aws_ecs_task_definition" "service" {
  family                   = local.service_name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = local.cpu
  memory                   = local.memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn

  container_definitions = jsonencode([
    {
      name      = local.service_name
      image     = "${aws_ecr_repository.service.repository_url}:latest"
      essential = true
      portMappings = [
        {
          containerPort = local.container_port
          hostPort      = local.container_port
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "PORT"
          value = tostring(local.container_port)
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.service.name
          "awslogs-region"        = local.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = {
    Name = "${local.service_name}-task"
  }
}

resource "aws_ecs_service" "service" {
  name            = local.service_name
  cluster         = data.aws_ecs_cluster.mcp.arn
  task_definition = aws_ecs_task_definition.service.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [data.aws_subnet.private_1.id, data.aws_subnet.private_2.id]
    security_groups  = [aws_security_group.service_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.service.arn
    container_name   = local.service_name
    container_port   = local.container_port
  }

  depends_on = [aws_lb_listener.service]

  lifecycle {
    ignore_changes = [task_definition]
  }

  tags = {
    Name = "${local.service_name}-svc"
  }
}
