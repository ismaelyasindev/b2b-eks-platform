variable "cluster_name" {
  type = string
}

resource "aws_sqs_queue" "dlq" {
  name                      = "${var.cluster_name}-order-completed-dlq"
  message_retention_seconds = 1209600
}

resource "aws_sqs_queue" "order_completed" {
  name = "${var.cluster_name}-order-completed"

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
}

output "queue_arn" {
  value = aws_sqs_queue.order_completed.arn
}

output "queue_url" {
  value = aws_sqs_queue.order_completed.url
}

output "queue_name" {
  value = aws_sqs_queue.order_completed.name
}

output "dlq_arn" {
  value = aws_sqs_queue.dlq.arn
}
