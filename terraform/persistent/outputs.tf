output "ecr_repository_urls" {
  value = {
    for name, repo in aws_ecr_repository.service : name => repo.repository_url
  }
}

output "db_secret_arns" {
  value = {
    for k, s in aws_secretsmanager_secret.db : k => s.arn
  }
}

output "postgres_exporter_secret_arns" {
  value = {
    for k, s in aws_secretsmanager_secret.postgres_exporter : k => s.arn
  }
}

output "storefront_bucket" {
  value = aws_s3_bucket.storefront.bucket
}

output "storefront_bucket_regional_domain_name" {
  value = aws_s3_bucket.storefront.bucket_regional_domain_name
}

output "runbooks_bucket" {
  value = aws_s3_bucket.runbooks.bucket
}

output "sns_aiops_topic_arn" {
  value = aws_sns_topic.aiops_alerts.arn
}

output "throttle_table_name" {
  value = aws_dynamodb_table.throttle_config.name
}

output "github_actions_role_arns" {
  value = {
    for name, role in aws_iam_role.github_actions : name => role.arn
  }
}
