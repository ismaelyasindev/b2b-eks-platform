variable "cluster_name" {
  type = string
}

variable "envs" {
  type = list(string)
}

variable "service_env" {
  type = map(object({
    env = string
    svc = string
  }))
}

variable "db_secret_arns" {
  type = map(string)
}

variable "sns_topic_arn" {
  type = string
}

variable "sqs_queue_arn" {
  type = string
}

variable "sqs_dlq_arn" {
  type = string
}

variable "throttle_table_arn" {
  type = string
}

data "aws_iam_policy_document" "pod_assume" {
  statement {
    actions = ["sts:AssumeRole", "sts:TagSession"]

    principals {
      type        = "Service"
      identifiers = ["pods.eks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "order_sqs" {
  name               = "${var.cluster_name}-order-sqs"
  assume_role_policy = data.aws_iam_policy_document.pod_assume.json
}

data "aws_iam_policy_document" "order_sqs" {
  statement {
    actions   = ["sqs:SendMessage"]
    resources = [var.sqs_queue_arn]
  }
}

resource "aws_iam_role_policy" "order_sqs" {
  name   = "order-sqs-send"
  role   = aws_iam_role.order_sqs.id
  policy = data.aws_iam_policy_document.order_sqs.json
}

resource "aws_eks_pod_identity_association" "order_sqs" {
  for_each = toset(var.envs)

  cluster_name    = var.cluster_name
  namespace       = each.value
  service_account = "order-sa"
  role_arn        = aws_iam_role.order_sqs.arn
}

resource "aws_iam_role" "notification_sqs" {
  name               = "${var.cluster_name}-notification-sqs"
  assume_role_policy = data.aws_iam_policy_document.pod_assume.json
}

data "aws_iam_policy_document" "notification_sqs" {
  statement {
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:ChangeMessageVisibility",
    ]
    resources = [var.sqs_queue_arn, var.sqs_dlq_arn]
  }
}

resource "aws_iam_role_policy" "notification_sqs" {
  name   = "notification-sqs-consume"
  role   = aws_iam_role.notification_sqs.id
  policy = data.aws_iam_policy_document.notification_sqs.json
}

resource "aws_eks_pod_identity_association" "notification_sqs" {
  for_each = toset(var.envs)

  cluster_name    = var.cluster_name
  namespace       = each.value
  service_account = "notification-sa"
  role_arn        = aws_iam_role.notification_sqs.arn
}

resource "aws_iam_role" "db_secret" {
  for_each = var.service_env

  name               = "${var.cluster_name}-${each.key}-db"
  assume_role_policy = data.aws_iam_policy_document.pod_assume.json
}

data "aws_iam_policy_document" "db_secret" {
  for_each = var.service_env

  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [var.db_secret_arns[each.key]]
  }

  dynamic "statement" {
    for_each = each.value.svc == "auth" ? [1] : []
    content {
      actions   = ["dynamodb:Scan"]
      resources = [var.throttle_table_arn]
    }
  }
}

resource "aws_iam_role_policy" "db_secret" {
  for_each = var.service_env

  name   = "db-secret"
  role   = aws_iam_role.db_secret[each.key].id
  policy = data.aws_iam_policy_document.db_secret[each.key].json
}

resource "aws_eks_pod_identity_association" "db_secret" {
  for_each = var.service_env

  cluster_name    = var.cluster_name
  namespace       = each.value.env
  service_account = "${each.value.svc}-sa"
  role_arn        = aws_iam_role.db_secret[each.key].arn
}

resource "aws_iam_role" "alertmanager_sns" {
  name               = "${var.cluster_name}-alertmanager-sns"
  assume_role_policy = data.aws_iam_policy_document.pod_assume.json
}

data "aws_iam_policy_document" "alertmanager_sns" {
  statement {
    actions   = ["sns:Publish"]
    resources = [var.sns_topic_arn]
  }
}

resource "aws_iam_role_policy" "alertmanager_sns" {
  name   = "sns-publish"
  role   = aws_iam_role.alertmanager_sns.id
  policy = data.aws_iam_policy_document.alertmanager_sns.json
}

resource "aws_eks_pod_identity_association" "alertmanager_sns" {
  cluster_name    = var.cluster_name
  namespace       = "monitoring"
  service_account = "alertmanager"
  role_arn        = aws_iam_role.alertmanager_sns.arn
}

resource "aws_iam_role" "otel_xray" {
  name               = "${var.cluster_name}-otel-xray"
  assume_role_policy = data.aws_iam_policy_document.pod_assume.json
}

resource "aws_iam_role_policy_attachment" "otel_xray" {
  role       = aws_iam_role.otel_xray.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

resource "aws_eks_pod_identity_association" "otel_xray" {
  cluster_name    = var.cluster_name
  namespace       = "monitoring"
  service_account = "otel-collector"
  role_arn        = aws_iam_role.otel_xray.arn
}
