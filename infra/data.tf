data "aws_availability_zones" "available" {}

data "aws_ecr_authorization_token" "token" {
  registry_id = aws_ecr_repository.congestion_map_repo.registry_id
}