resource "aws_ecr_repository" "congestion_map_repo" {
  name                 = local.name
  image_tag_mutability = "MUTABLE"
}

resource "docker_image" "app" {
  name = "${aws_ecr_repository.congestion_map_repo.repository_url}:latest"

  build {
    context    = "${path.module}/.."
    dockerfile = "Dockerfile"
  }

  triggers = {
    dockerfile_hash   = filemd5("${path.module}/../Dockerfile")
    app_hash          = sha256(join("", [for f in fileset("${path.module}/../app", "**") : filesha256("${path.module}/../app/${f}")]))
    requirements_hash = filemd5("${path.module}/../requirements.txt")
    run_worker_hash   = filemd5("${path.module}/../run_worker.py")
  }
}

resource "docker_registry_image" "app" {
  name = docker_image.app.name
  # Explicit ECR authentication
  auth_config {
    address  = data.aws_ecr_authorization_token.token.proxy_endpoint
    username = "AWS"
    password = data.aws_ecr_authorization_token.token.password
  }

  keep_remotely = true

  depends_on = [
    docker_image.app,
    data.aws_ecr_authorization_token.token
  ]
}