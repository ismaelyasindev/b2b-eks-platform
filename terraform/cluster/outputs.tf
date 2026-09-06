output "cluster_name" {
  value = module.eks.cluster_name
}

output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "web_acl_arn" {
  value = module.waf.web_acl_arn
}

output "rds_endpoints" {
  value = module.rds.endpoints
}

output "sqs_queue_name" {
  value = module.sqs.queue_name
}

output "public_subnet_cidrs" {
  value = module.vpc.public_subnet_cidrs
}

output "cloudfront_domain" {
  value = try(module.cloudfront_frontend[0].domain_name, null)
}

output "cloudfront_distribution_id" {
  value = try(module.cloudfront_frontend[0].distribution_id, null)
}

output "kubeconfig_command" {
  value = "aws eks update-kubeconfig --name ${module.eks.cluster_name} --region ${var.region}"
}
