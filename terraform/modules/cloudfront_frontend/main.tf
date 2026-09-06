variable "api_origin_domain" {
  type = string
}

variable "storefront_bucket" {
  type = string
}

variable "storefront_bucket_regional_domain_name" {
  type = string
}

resource "aws_cloudfront_origin_access_control" "storefront" {
  name                              = "storefront-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_function" "strip_api" {
  name    = "strip-api-prefix"
  runtime = "cloudfront-js-2.0"
  publish = true
  code    = <<-JS
    function handler(event) {
      var req = event.request;
      if (req.uri.startsWith("/api/")) { req.uri = req.uri.replace(/^\/api/, ""); }
      else if (req.uri === "/api")     { req.uri = "/"; }
      return req;
    }
  JS
}

resource "aws_cloudfront_distribution" "storefront" {
  enabled             = true
  default_root_object = "index.html"

  origin {
    origin_id                = "s3-storefront"
    domain_name              = var.storefront_bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.storefront.id
  }

  origin {
    origin_id   = "eks-alb"
    domain_name = var.api_origin_domain
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id       = "s3-storefront"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    cache_policy_id        = "658327ea-f89d-4fab-a63d-7e88639e58f6"
    compress               = true
  }

  ordered_cache_behavior {
    path_pattern             = "/api/*"
    target_origin_id         = "eks-alb"
    viewer_protocol_policy   = "redirect-to-https"
    allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods           = ["GET", "HEAD"]
    cache_policy_id          = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
    origin_request_policy_id = "216adef6-5c7f-47e4-b989-5492eafa07d3"

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.strip_api.arn
    }
  }

  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

data "aws_iam_policy_document" "storefront_oac" {
  statement {
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    actions   = ["s3:GetObject"]
    resources = ["arn:aws:s3:::${var.storefront_bucket}/*"]
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.storefront.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "storefront" {
  bucket = var.storefront_bucket
  policy = data.aws_iam_policy_document.storefront_oac.json
}

output "domain_name" {
  value = aws_cloudfront_distribution.storefront.domain_name
}

output "distribution_id" {
  value = aws_cloudfront_distribution.storefront.id
}
