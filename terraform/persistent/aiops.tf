resource "aws_s3_bucket" "runbooks" {
  bucket        = "b2b-platform-aiops-runbooks-london"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "runbooks" {
  bucket                  = aws_s3_bucket.runbooks.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "runbooks" {
  bucket = aws_s3_bucket.runbooks.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_sns_topic" "aiops_alerts" {
  name = "aiops-alerts"
}

resource "aws_dynamodb_table" "throttle_config" {
  name         = "ai-throttle-config"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "RuleName"

  attribute {
    name = "RuleName"
    type = "S"
  }

  ttl {
    attribute_name = "ExpiresAt"
    enabled        = true
  }
}

data "aws_iam_policy_document" "remediation_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "remediation" {
  name               = "b2b-aiops-remediation"
  assume_role_policy = data.aws_iam_policy_document.remediation_assume.json
}

data "aws_iam_policy_document" "remediation" {
  statement {
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["arn:aws:logs:eu-west-2:${data.aws_caller_identity.current.account_id}:*"]
  }

  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.runbooks.arn}/*"]
  }

  statement {
    actions   = ["ses:SendEmail"]
    resources = ["arn:aws:ses:eu-west-2:${data.aws_caller_identity.current.account_id}:identity/${var.aiops_notify_email}"]
  }

  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.approval_hmac.arn]
  }

  statement {
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
    ]
    resources = [
      "arn:aws:bedrock:*::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0",
      "arn:aws:bedrock:eu-west-2:${data.aws_caller_identity.current.account_id}:inference-profile/*",
    ]
  }

  statement {
    actions = [
      "aws-marketplace:ViewSubscriptions",
      "aws-marketplace:Subscribe",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "remediation" {
  name   = "b2b-aiops-remediation"
  role   = aws_iam_role.remediation.id
  policy = data.aws_iam_policy_document.remediation.json
}

data "archive_file" "remediation" {
  type        = "zip"
  source_file = "${path.module}/../../aiops/lambda/remediation_handler.py"
  output_path = "${path.module}/remediation.zip"
}

resource "aws_lambda_function" "remediation" {
  function_name    = "b2b-aiops-remediation"
  filename         = data.archive_file.remediation.output_path
  source_code_hash = data.archive_file.remediation.output_base64sha256
  role             = aws_iam_role.remediation.arn
  handler          = "remediation_handler.lambda_handler"
  runtime          = "python3.12"
  timeout          = 60
  memory_size      = 256

  environment {
    variables = {
      RUNBOOK_BUCKET           = aws_s3_bucket.runbooks.bucket
      BEDROCK_MODEL_ID         = local.bedrock_model_id
      SES_FROM                 = var.aiops_notify_email
      SES_TO                   = var.aiops_notify_email
      APPROVAL_URL             = aws_lambda_function_url.approval.function_url
      APPROVAL_HMAC_SECRET_ARN = aws_secretsmanager_secret.approval_hmac.arn
    }
  }

  depends_on = [aws_iam_role_policy.remediation]
}

resource "aws_lambda_permission" "sns_invoke" {
  statement_id  = "AllowSNSInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.remediation.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.aiops_alerts.arn
}

resource "aws_sns_topic_subscription" "remediation" {
  topic_arn = aws_sns_topic.aiops_alerts.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.remediation.arn

  depends_on = [aws_lambda_permission.sns_invoke]
}

resource "random_password" "approval_hmac" {
  length  = 48
  special = false
}

resource "aws_secretsmanager_secret" "approval_hmac" {
  name                    = "b2b/aiops/approval-hmac"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "approval_hmac" {
  secret_id     = aws_secretsmanager_secret.approval_hmac.id
  secret_string = random_password.approval_hmac.result
}

resource "aws_iam_role" "approval" {
  name               = "b2b-aiops-approval"
  assume_role_policy = data.aws_iam_policy_document.remediation_assume.json
}

data "aws_iam_policy_document" "approval" {
  statement {
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["arn:aws:logs:eu-west-2:${data.aws_caller_identity.current.account_id}:*"]
  }

  statement {
    actions   = ["dynamodb:PutItem"]
    resources = [aws_dynamodb_table.throttle_config.arn]
  }

  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.approval_hmac.arn]
  }
}

resource "aws_iam_role_policy" "approval" {
  name   = "b2b-aiops-approval"
  role   = aws_iam_role.approval.id
  policy = data.aws_iam_policy_document.approval.json
}

data "archive_file" "approval" {
  type        = "zip"
  source_file = "${path.module}/../../aiops/lambda/approval_click_handler.py"
  output_path = "${path.module}/approval.zip"
}

resource "aws_lambda_function" "approval" {
  function_name    = "b2b-aiops-approval"
  filename         = data.archive_file.approval.output_path
  source_code_hash = data.archive_file.approval.output_base64sha256
  role             = aws_iam_role.approval.arn
  handler          = "approval_click_handler.lambda_handler"
  runtime          = "python3.12"
  timeout          = 10
  memory_size      = 128

  environment {
    variables = {
      THROTTLE_TABLE_NAME      = aws_dynamodb_table.throttle_config.name
      APPROVAL_HMAC_SECRET_ARN = aws_secretsmanager_secret.approval_hmac.arn
    }
  }

  depends_on = [aws_iam_role_policy.approval]
}

resource "aws_lambda_function_url" "approval" {
  function_name      = aws_lambda_function.approval.function_name
  authorization_type = "NONE"
}

resource "aws_lambda_permission" "approval_url" {
  statement_id           = "FunctionURLAllowPublic"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.approval.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_lambda_permission" "approval_invoke" {
  statement_id  = "FunctionURLAllowInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.approval.function_name
  principal     = "*"
}
