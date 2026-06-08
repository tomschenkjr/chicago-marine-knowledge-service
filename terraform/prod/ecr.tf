resource "aws_ecr_repository" "service" {
  name                 = local.ecr_repo
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = false
  }

  tags = {
    Name = "${local.service_name}-ecr"
  }
}
