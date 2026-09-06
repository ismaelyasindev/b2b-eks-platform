resource "aws_s3_bucket" "storefront" {
  bucket        = "b2b-platform-storefront-london"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "storefront" {
  bucket                  = aws_s3_bucket.storefront.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "storefront" {
  bucket = aws_s3_bucket.storefront.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
