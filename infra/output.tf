output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.congestion_map_repo.repository_url
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "alb_url" {
  description = "Full URL of the Application Load Balancer"
  value       = "http://${aws_lb.main.dns_name}"
}

output "sqs_queue_url" {
  description = "URL of the SQS queue"
  value       = aws_sqs_queue.ping_queue.url
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table"
  value       = aws_dynamodb_table.congestion_table.name
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = module.ecs.cluster_name
}

output "ecs_cluster_id" {
  description = "ID of the ECS cluster"
  value       = module.ecs.cluster_id
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = module.ecs.services["api"].name
}