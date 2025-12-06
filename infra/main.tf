module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 6.5"

  name = "${local.name}-vpc"
  cidr = local.vpc_cidr

  azs = local.azs

  public_subnets  = [for k, v in local.azs : cidrsubnet(local.vpc_cidr, 8, k)]
  private_subnets = [for k, v in local.azs : cidrsubnet(local.vpc_cidr, 8, k + 3)]

  enable_nat_gateway = true
  single_nat_gateway = true
}

resource "aws_sqs_queue" "ping_queue" {
  name = "${local.name}-ping-queue"

  visibility_timeout_seconds = 60
  message_retention_seconds  = 86400
}


resource "aws_dynamodb_table" "congestion_table" {
  name         = "${local.name}-congestion-table"
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = "h3_hex"
  range_key = "ts"

  attribute {
    name = "h3_hex"
    type = "S"
  }
  attribute {
    name = "ts"
    type = "S"
  }
}


resource "aws_cloudwatch_log_group" "ecs_logs" {
  name              = "${local.name}-ecs-logs"
  retention_in_days = 7
}

resource "aws_security_group" "alb" {
  name        = "${local.name}-alb-sg"
  description = "Allow HTTP/HTTPS traffic to the application"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name}-alb-sg"
  }
}

resource "aws_security_group" "ecs_tasks" {
  name        = "${local.name}-ecs-tasks-sg"
  description = "Allow traffic from ALB"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name}-ecs-tasks-sg"
  }
}

resource "aws_lb" "main" {
  name               = "${local.name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = module.vpc.public_subnets

  enable_deletion_protection = false
}

resource "aws_lb_target_group" "api" {
  name        = "${local.name}-api-ecs-tg"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"

  health_check {
    path     = "/"
    port     = 80
    protocol = "HTTP"
    matcher  = "200-302"
  }
}

resource "aws_lb_listener" "api" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}
module "ecs" {
  source  = "terraform-aws-modules/ecs/aws"
  version = "~> 6.10"

  cluster_name = local.name

  services = {
    api = {
      cpu           = 256
      memory        = 512
      launch_type   = "FARGATE"
      desired_count = 1

      tasks_iam_role_statements = data.aws_iam_policy_document.ecs_task_policy.statement

      container_definitions = {
        app = {
          image     = "${aws_ecr_repository.congestion_map_repo.repository_url}:latest"
          essential = true
          cpu       = 256
          memory    = 512

          portMappings = [
            {
              containerPort = 80
              protocol      = "tcp"
            }
          ]

          environment = [
            {
              name  = "AWS_REGION"
              value = local.region
            },
            {
              name  = "SQS_QUEUE_NAME"
              value = aws_sqs_queue.ping_queue.name
            },
            {
              name  = "DYNAMODB_TABLE_NAME"
              value = aws_dynamodb_table.congestion_table.name
            }
          ]

          logConfiguration = {
            logDriver = "awslogs"
            options = {
              awslogs-group         = aws_cloudwatch_log_group.ecs_logs.name
              awslogs-region        = local.region
              awslogs-stream-prefix = "api"
            }
          }
        }
      }

      subnet_ids         = module.vpc.private_subnets
      security_group_ids = [aws_security_group.ecs_tasks.id]

      load_balancer = {
        api = {
          target_group_arn = aws_lb_target_group.api.arn
          container_name   = "app"
          container_port   = 80
        }
      }
    }
    worker = {
      cpu           = 256
      memory        = 512
      launch_type   = "FARGATE"
      desired_count = 1

      tasks_iam_role_statements = data.aws_iam_policy_document.ecs_task_policy.statement

      container_definitions = {
        job = {
          image     = "${aws_ecr_repository.congestion_map_repo.repository_url}:latest"
          essential = true
          cpu       = 256
          memory    = 512
          command   = ["python", "run_worker.py"]

          environment = [
            {
              name  = "AWS_REGION"
              value = local.region
            },
            {
              name  = "SQS_QUEUE_NAME"
              value = aws_sqs_queue.ping_queue.name
            },
            {
              name  = "DYNAMODB_TABLE_NAME"
              value = aws_dynamodb_table.congestion_table.name
            }
          ]

          logConfiguration = {
            logDriver = "awslogs"
            options = {
              awslogs-group         = aws_cloudwatch_log_group.ecs_logs.name
              awslogs-region        = local.region
              awslogs-stream-prefix = "worker"
            }
          }
        }
      }

      subnet_ids         = module.vpc.private_subnets
      security_group_ids = [aws_security_group.ecs_tasks.id]
    }
  }
}