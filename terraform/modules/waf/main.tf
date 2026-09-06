variable "name" {
  type    = string
  default = "b2b-edge-firewall"
}

resource "aws_wafv2_web_acl" "edge_firewall" {
  name        = var.name
  scope       = "REGIONAL"
  description = "Edge rate limiting; associated to the ALB via Ingress annotation"

  default_action {
    allow {}
  }

  rule {
    name     = "EnforceRateLimit"
    priority = 1

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "WafRateLimitingMetric"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "GlobalWafLimiter"
    sampled_requests_enabled   = true
  }
}

output "web_acl_arn" {
  value = aws_wafv2_web_acl.edge_firewall.arn
}
