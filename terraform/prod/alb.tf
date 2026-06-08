resource "aws_security_group" "service_alb" {
  name        = "${local.service_name}-alb-sg"
  description = "Internal ALB access for ${local.service_name}"
  vpc_id      = data.aws_vpc.mcp.id

  ingress {
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [data.aws_security_group.mcp_ecs_tasks.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.service_name}-alb-sg"
  }
}

resource "aws_security_group" "service_tasks" {
  name        = "${local.service_name}-tasks-sg"
  description = "Task access for ${local.service_name}"
  vpc_id      = data.aws_vpc.mcp.id

  ingress {
    from_port       = local.container_port
    to_port         = local.container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.service_alb.id]
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

resource "aws_lb" "service" {
  name               = local.internal_alb_name
  internal           = true
  load_balancer_type = "application"
  security_groups    = [aws_security_group.service_alb.id]
  subnets            = [data.aws_subnet.private_1.id, data.aws_subnet.private_2.id]

  tags = {
    Name = "${local.service_name}-internal-alb"
  }
}

resource "aws_lb_target_group" "service" {
  name        = local.target_group_name
  port        = local.container_port
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.mcp.id
  target_type = "ip"

  health_check {
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }

  tags = {
    Name = "${local.service_name}-tg"
  }
}

resource "aws_lb_listener" "service" {
  load_balancer_arn = aws_lb.service.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.service.arn
  }
}
