provider "aws" {
  region = local.aws_region

  default_tags {
    tags = {
      Environment = "prod"
      Project     = "chicago-marine-knowledge"
      ManagedBy   = "terraform"
    }
  }
}
