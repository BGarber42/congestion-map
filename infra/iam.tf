data "aws_iam_policy_document" "ecs_task_policy" {
  # Allow GetQueueUrl and ListQueues (these need account-level or wildcard resources)
  statement {
    effect = "Allow"
    actions = [
      "sqs:GetQueueUrl",
      "sqs:ListQueues",
    ]
    resources = ["*"] # These actions need account-level access
  }

  # Specific queue operations
  statement {
    effect = "Allow"
    actions = [
      "sqs:SendMessage",
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:CreateQueue",
    ]
    resources = [aws_sqs_queue.ping_queue.arn]
  }

  statement {
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:GetItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:DescribeTable",
      "dynamodb:CreateTable"
    ]
    resources = [aws_dynamodb_table.congestion_table.arn]
  }
}

